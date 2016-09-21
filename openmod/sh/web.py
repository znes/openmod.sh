from datetime import datetime, timezone as tz
from urllib.parse import urlparse, urljoin
from xml.etree.ElementTree import XML
import functools as fun
import itertools
import json
import multiprocessing as mp
import multiprocessing.pool as mpp

from flask_oauthlib.provider import OAuth1Provider
import flask
import flask_cors as cors # TODO: Check whether the `@cors.cross_origin()`
                          #       decorators are still necessary once 'iD' is
                          #       served from within this app.
import flask_login as fl
import flask_wtf as wtfl
import wtforms as wtf

import oemof.db

from .schemas import osm
from .schemas.osm import Element_Relation_Associations as ERAs
import openmod.sh.scenario


app = flask.Flask(__name__)
# For production deployment: generate a different one via Python's `os.urandom`
# and store it in a safe place.
# See: http://flask.pocoo.org/docs/0.11/quickstart/#sessions
app.secret_key = b"DON'T USE THIS IN PRODUCTION! " + b'\xdb\xcd\xb4\x8cp'

# Set up a pool of workers to which jobs can be submitted and a dictionary
# which stores the asynchronous result objects.
app.workers = mpp.Pool(1)
app.results = {}

##### Utility Functions #######################################################
#
# Some functions used throughout this module (and maybe even elsewhere.)
#
# This should probably go into it's own module but I'm putting it all here for
# now, as some parts need to stay in this module while some parts can be
# factored out later. The 'factoring out' part can be considered an open TODO.
#
###############################################################################

def xml_response(template):
    response = flask.make_response(template)
    response.headers['Content-Type'] = 'text/xml'
    return response

##### Utility Functions end here ##############################################

##### Safe Redirects ##########################################################
#
# If we allow redirects after form submission, we want it to be safe. The code
# in here is taken from a [flask snippet][0], with minor modifications.
#
# This should probably go into it's own module but I'm putting it all here for
# now, as some parts need to stay in this module while some parts can be
# factored out later. The 'factoring out' part can be considered an open TODO.
#
# [0]: http://flask.pocoo.org/snippets/63/
#
##############################################################################

app.config['WTF_CSRF_CHECK_DEFAULT'] = False

csrf = wtfl.csrf.CsrfProtect(app)

def is_safe_url(target):
    ref_url = urlparse(flask.request.host_url)
    test_url = urlparse(urljoin(flask.request.host_url, target))
    return ((test_url.scheme in ('http', 'https')) and
            (ref_url.netloc == test_url.netloc))

    # TODO: Remove the `redirect_arg` parameter. That was only needed to
    #       redirect to the 'oauth_callback' URL parameter, which isn't needed
    #       anymore as redirection seems to be handled by flask-oauthlib there.
def get_redirect_target(redirect_arg):
    for target in flask.request.args.get(redirect_arg), flask.request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target

class RedirectForm(wtfl.Form):
    next = wtf.HiddenField()

    def __init__(self, *args, redirect_arg='next', **kwargs):
        super().__init__(*args, **kwargs)
        self.redirect_arg = redirect_arg
        if not self.next.data:
            self.next.data = get_redirect_target(redirect_arg) or ''

    def redirect(self, endpoint='root', **values):
        if is_safe_url(self.next.data):
            return flask.redirect(self.next.data)
        target = get_redirect_target(self.redirect_arg)
        return flask.redirect(target or flask.url_for(endpoint, **values))

##### Safe Redirects end here #################################################

##### User Management #########################################################
#
# User management code. This should probably go into it's own module but I'm
# putting it all here for now, as some parts need to stay in this module while
# some parts can be factored out later.
# The 'factoring out' part can be considered an open TODO.
#
##############################################################################

login_manager = fl.LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    user = osm.User.query.get(user_id) if user_id else None
    return user

class Login(RedirectForm):
    username = wtf.StringField('Username', [wtf.validators.Length(min=3,
                                                                  max=79)])
    password = wtf.PasswordField(
            'Password', [wtf.validators.Length(min=3, max=79)])

@csrf.exempt
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        user = load_user(osm.User.name2id(form.username.data))
        if user is not None:
            if user.check_pw(form.password.data):
                fl.login_user(user)
                #print("Current user: {}".format(fl.current_user))
            else:
                flask.flash('Invalid username/password combination.')
                return flask.redirect(flask.url_for('login'))
        else:
            user = osm.User(form.username.data, form.password.data)
            osm.DB.session.add(user)
            osm.DB.session.commit()
            flask.flash('User "{}" created.'.format(user.name))
            fl.login_user(user)
        # From now on: user logged in.
        # TODO: Doesn't seem to work, as `flask.request.args.get('next')` is
        #       always none. Have a look at http://flask.pocoo.org/snippets/63/
        #       for pointers on how to make this work.
        return form.redirect('login')
    return flask.render_template('login.html', form=form)

@app.route('/logout')
def logout():
    fl.logout_user()
    flask.flash('Logged out')
    return flask.redirect(flask.url_for('login'))

##### User Management stuff ends here (except for the `@fl.login_required`).

@app.route('/')
@fl.login_required
def root():
    return flask.redirect('/static/iD/index.html')

@app.route('/iD/api/capabilities')
@app.route('/osm/api/capabilities')
@app.route('/osm/api/0.6/capabilities')
@cors.cross_origin()
def capabilities():
    template = flask.render_template('capabilities.xml', area={"max": 0.2},
                                     timeout=250)
    return xml_response(template)

# See:
#   * http://wiki.openstreetmap.org/wiki/API_v0.6#Retrieving_map_data_by_bounding_box:_GET_.2Fapi.2F0.6.2Fmap
# for notes on how exctly to do this.

@app.route('/iD/api/0.6/map')
@app.route('/osm/api/0.6/map')
@cors.cross_origin()
@fl.login_required
def osm_map():
    left, bottom, right, top = map(float, flask.request.args['bbox'].split(","))
    minx, maxx = sorted([top, bottom])
    miny, maxy = sorted([left, right])
    # Get all nodes in the given bounding box.
    nodes = osm.Node.query.filter(minx <= osm.Node.lat, miny <= osm.Node.lon,
                                  maxx >= osm.Node.lat, maxy >= osm.Node.lon)
    # Limit nodes to the one's contained in the selected scenario.
    scenario = flask.session.get("scenario")
    if (scenario):
        scenario = osm.Relation.query.filter_by(id=scenario).first()
        nodes = [ n for n in nodes
                    for scenario in n.referencing_relations]
    # Get all ways referencing the above nodes.
    ways = set(way for node in nodes for way in node.ways)
    # Get all relations referencing the above ways.
    relations = set(relation for way in ways
                             for relation in way.referencing_relations)
    # Add possibly missing nodes (from outside the bounding box) referenced by
    # the ways retrieved above.
    nodes = set(itertools.chain([n for way in ways for n in way.nodes], nodes))
    relations = set(itertools.chain((r for n in nodes
                                       for r in n.referencing_relations),
                                    (s for r in relations
                                       for s in r.referencing_relations),
                                    relations))
    template = flask.render_template('map.xml', nodes=nodes, ways=ways,
                                          relations=relations,
                                          minlon=miny, maxlon=maxy,
                                          minlat=minx, maxlat=maxx)
    return xml_response(template)

@app.route('/simulate', methods=['PUT'])
def simulate():
    fras = flask.request.args
    result = app.workers.apply_async(openmod.sh.scenario.simulate,
                                     #kwds=fras)
                                     kwds={k: fras[k] for k in fras})
    key = str(id(result))
    app.results[key] = result
    return key

@app.route('/simulation/<job>')
def simulation(job):
    if not job in app.results:
        return "Unknown job."
    elif not app.results[job].ready():
        return ("Job running, but not finished yet. <br />" +
                "Please come back later.")
    else:
        result = app.results[job].get()
        del app.results[job]
        return result

@app.route('/scenarios')
@fl.login_required
def scenarios():
    scenarios = list(sorted(
        [ {"value": r.tags['name'], "title": r.id}
          for r in osm.Relation.query.all()
          if r.tags.get("type") == "scenario"
          if r.tags.get('name')],
        key=lambda d: d['value']))
    if (flask.session.get("scenario")):
        scenarios = ([{"title": None, "value": "Deselect selected scenario"}] +
                [s for s in scenarios
                   if s['title'] != flask.session.get("scenario")])
    return json.dumps(scenarios)

@app.route('/scenario', defaults={"s": None}, methods=['GET'])
@app.route('/scenario/<s>', methods=['PUT'])
@fl.login_required
def scenario(s):
    if flask.request.method == 'GET':
        return str(flask.session.get("scenario", ""))
    elif s and not json.loads(s) and "scenario" in flask.session:
        del flask.session["scenario"]
    else:
        flask.session["scenario"] = json.loads(s)
    return ""

##### OAuth1 provider code ####################################################
#
# In order to talk to the iD editor, we need to implement and OAuth1 provider.
#
# The code in this section does so by following the flask-oauthlib
# [tutorial][0] pretty closely. The only exception is that we don't involve a
# database since we store everything in memor. One can also always check that
# it works by going through the [oauthlib CLI trial][1].
#
# This should probably go into it's own module but I'm putting it all here for
# now, as some parts need to stay in this module while some parts can be
# factored out later. The 'factoring out' part can be considered an open TODO.
#
# [0]: http://flask-oauthlib.readthedocs.io/en/latest/oauth1.html#oauth1-server
# [1]: https://oauthlib.readthedocs.io/en/latest/oauth1/server.html#try-your-provider-with-a-quick-cli-client
#
###############################################################################

"""
import logging
import sys
log = logging.getLogger('flask_oauthlib')
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.DEBUG)
"""

app.config['OAUTH1_PROVIDER_ENFORCE_SSL'] = False
app.config['OAUTH1_PROVIDER_KEY_LENGTH'] = (3, 127)

oauth = OAuth1Provider(app)

class Client:
    def __init__(self):
        # At this point we don't really care about OAuth. That's why the
        # key/secret is set to something silly to make sure it's set to
        # something more secret and unguessable once we start caring about
        # OAuth again.
        self.client_key = 'NotReallyAKey'
        self.client_secret = 'NotReallyASecret'
        self.redirect_uris = ["http://localhost:5000/oauth-redirected",
                              # The [OAuthLib example][0] needs this redirect.
                              #
                              # [0]: https://oauthlib.readthedocs.io/en/latest/oauth1/server.html#try-your-provider-with-a-quick-cli-client
                              "http://127.0.0.1/cb",
                              # This one is needed by the iD editor. This is
                              # where the user is redirected to after
                              # authorizing iD, so that iD gets to know that it
                              # can go on.
                              "/static/iD/land.html"]
        self.default_redirect_uri = self.redirect_uris[0]
        self.default_realms = []
CLIENT = Client()

class RequestToken:
    known = []
    def __init__(self, token, request):
        #print("Creating request token.")
        self.known.append(self)
        self.client = CLIENT
        self.token = token['oauth_token']
        self.secret = token['oauth_token_secret']
        self.redirect_uri = request.redirect_uri
        self.realms = request.realms if getattr(oauth, "realms", None) else []

    @property
    def client_key(self):
        return self.client.client_key

class Nonce:
    known = []
    def __init__(self, timestamp, nonce, request_token, access_token):
        self.known.append(self)
        self.client_key = CLIENT.client_key
        self.timestamp = timestamp
        self.nonce = nonce
        self.request_token = request_token
        self.access_token = access_token

class AccessToken:
    known = []
    def __init__(self, token, request):
        self.known.append(self)
        self.client = request.client
        self.user = request.user
        self.token = token['oauth_token']
        self.secret = token['oauth_token_secret']
        self.realms = token['oauth_authorized_realms'].split()

    @property
    def client_key(self):
        return self.client.client_key

@oauth.clientgetter
def load_client(client_key):
    return CLIENT

@oauth.grantgetter
def load_request_token(token):
    rts = [rt for rt in RequestToken.known if rt.token == token]
    return (rts[0] if rts else None)

@oauth.grantsetter
def save_request_token(token, request):
    return RequestToken(token, request)

@oauth.verifiergetter
def load_verifier(verifier, token):
    #print("Verifiers on known rts: {}".format(
    #    [rt.verifier for rt in RequestToken.known]))
    #print("Verifier: {}".format(verifier))
    #print("Tokens on known rts: {}".format(
    #    [rt.token for rt in RequestToken.known]))
    #print("Token: {}".format(token))
    rt = [rt for rt in RequestToken.known
             if rt.token == token
             if rt.verifier == verifier]
    #print("rt: {}".format(rt))
    return (rt[0] if rt else None)

@oauth.verifiersetter
def save_verifier(token, verifier, *args, **kwargs):
    rt = [rt for rt in RequestToken.known if rt.token == token][0]
    rt.verifier = verifier['oauth_verifier']
    rt.user = fl.current_user
    return rt

@oauth.tokengetter
def load_access_token(client_key, token, *args, **kwargs):
    ats =  [at for at in AccessToken.known
               if at.client_key == client_key and at.token == token]
    return (ats[0] if ats else None)

@oauth.tokensetter
def save_access_token(token, request):
    return AccessToken(token, request)

@oauth.noncegetter
def load_nonce(client_key, timestamp, nonce, request_token, access_token):
    """
    print('\n  '.join([
        "In `load_nonce`. Arguments:",
        "client_key: {}", "timestamp: {}", "nonce: {}", "request_token: {}",
        "access_token: {}"]).format(
            client_key, timestamp, nonce, request_token, access_token))
    print(Nonce.known)
    """
    filtered = [n for n in Nonce.known if (n.client_key == client_key and
                                           n.timestamp == timestamp and
                                           n.nonce == nonce and
                                           n.request_token == request_token and
                                           n.access_token == access_token)]
    return (filtered[0] if filtered else None)

@oauth.noncesetter
def save_nonce(client_key, timestamp, nonce, request_token, access_token):
    #print("Setting nonce.")
    return Nonce(timestamp, nonce, request_token, access_token)

@app.route('/iD/connection/oauth/request_token', methods=['GET', 'POST'])
@cors.cross_origin()
@oauth.request_token_handler
def oauth_request_token():
    #print("request_token_handler: {}".format(flask.request.method))
    return {}

"""
@app.before_request
def pre_request_debug_hook():
    print("\n  ".join([
        "Got request: ",
        "Method: {0.method}",
        "Path  : {0.path}",
        "Rule  : {0.url_rule}",
        "Data  : {0.data}",
        "T(D)  : {1}",
        "Endpt.: {0.endpoint}"]).format(flask.request, type(flask.request.data)))
"""

class Authorize(wtfl.Form):
     confirm = wtf.BooleanField('Authorize')

@app.route('/iD/connection/oauth/authorize', methods=['GET', 'POST'])
@fl.login_required
@oauth.authorize_handler
def authorize(*args, **kwargs):
    if flask.request.method == 'GET':
        form = Authorize()
        return """
            <p> "{}" : "{}" </p>
            <form action="" method="post">
                <input type=submit value="Confirm authorization">
                {}
            </form>
            """.format(CLIENT.client_key, kwargs.get('resource_owner_key'),
                       form.confirm)
    return (flask.request.form.get('confirm', 'no') == 'y')

@app.route('/iD/connection/oauth/access_token', methods=['GET', 'POST'])
@cors.cross_origin()
@oauth.access_token_handler
def access_token():
    return {}

@app.route('/oauth-protected')
@oauth.require_oauth()
def oauth_protected_test_endpoint():
    return "Successfully accessed an oauth protected resource as {}.".format(
            flask.request.oauth.user)

##### OAuth1 provider code ends here ##########################################

##### Persisting changes from iD ##############################################
#
# Persistence code to store changes done in iD on the server.
#
# TODO: Protect these via `@oauth.require_oauth()`. It doesn't work currently,
#       so we are just ignoring the whole OAuth thing to get a working version.
# This should probably go into it's own module but I'm putting it all here for
# now, as some parts need to stay in this module while some parts can be
# factored out later. The 'factoring out' part can be considered an open TODO.
#
###############################################################################

app.config['SQLALCHEMY_DATABASE_URI'] = oemof.db.url(osm.configsection)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
osm.DB.init_app(app)

@app.route('/iD/api/0.6/changeset/create', methods=['PUT'])
@app.route('/iD/connection/api/0.6/changeset/create', methods=['PUT'])
@cors.cross_origin()
def create_changeset():
    cs = osm.Changeset()
    osm.DB.session.add(cs)
    osm.DB.session.commit()
    return str(cs.id)

@app.route('/iD/api/0.6/user/details', methods=['GET'])
@app.route('/iD/connection/api/0.6/user/details', methods=['GET'])
@cors.cross_origin()
def userdetails():
    cu = fl.current_user
    fl.id = id(fl)
    template = flask.render_template('userdetails.xml', user=fl.current_user)
    return xml_response(template)

@app.route('/iD/api/0.6/changeset/<cid>/upload', methods=['POST'])
@app.route('/iD/connection/api/0.6/changeset/<cid>/upload', methods=['POST'])
@cors.cross_origin()
def upload_changeset(cid):
    xml = XML(flask.request.data)
    creations = xml.findall('create')
    created_nodes = itertools.chain(*[c.findall('node') for c in creations])
    created_nodes = [
            osm.Node(
              float(n["lat"]), float(n["lon"]), int(cid),
              uid=fl.current_user.id,
              tags={tag.attrib['k']: tag.attrib['v']
                    for tag in node.findall('tag')},
              old_id=int(n["id"]),
              tag="node")
            for node in created_nodes
            for n in (node.attrib,)]
    for node in created_nodes:
        osm.DB.session.add(node)
    modifications = xml.findall('modify')
    modified_nodes = list(
            itertools.chain(*[c.findall('node') for c in modifications]))
    for xml_node in modified_nodes:
        atts = xml_node.attrib
        tags = xml_node.findall('tag')
        db_node = osm.Node.query.filter_by(id = int(atts["id"])).first()
        db_node.old_id = db_node.id
        db_node.version = atts["version"]
        db_node.changeset = osm.Changeset.query.filter_by(
                id = int(atts["changeset"])).first()
        db_node.tags.update({tag.attrib['k']: tag.attrib['v']
                             for tag in xml_node.findall('tag')})
    for element in modified_nodes:
        element.tag = "node"
        created_nodes.append(element)
    osm.DB.session.flush()
    temporary_id2node = {n.old_id: n for n in created_nodes
                                     if  n not in modified_nodes}
    created_ways = itertools.chain(*[c.findall('way') for c in creations])
    created_ways = {int(att["id"]): osm.Way(
        nodes=[temporary_id2node.get(node_id) or
               osm.Node.query.filter_by(id = node_id).first()
               for node_id in map(lambda nd: int(nd.attrib['ref']),
                                  way.findall('nd'))],
        changeset=osm.Changeset.query.filter_by(id = int(cid)).first(),
        user=fl.current_user,
        version=att['version'],
        tags={tag.attrib['k']: tag.attrib['v']
              for tag in way.findall('tag')})
            for way in created_ways
            for att in (way.attrib,)}
    for old_id, way in created_ways.items():
        way.old_id = old_id
        way.tag = "way"
        osm.DB.session.add(way)
        created_nodes.append(way)
    osm.DB.session.flush()

    modified_ways = list(
            itertools.chain(*[c.findall('way') for c in modifications]))
    for xml_way in modified_ways:
        atts = xml_way.attrib
        tags = xml_way.findall('tag')
        db_way = osm.Way.query.filter_by(id = int(atts["id"])).first()
        db_way.old_id = db_way.id
        db_way.version = atts["version"]
        db_way.changeset = osm.Changeset.query.filter_by(
                id = int(atts["changeset"])).first()
        db_way.tags.update({tag.attrib['k']: tag.attrib['v']
                            for tag in xml_way.findall('tag')})
    for element in modified_ways:
        element.tag = "way"
        created_nodes.append(element)
    osm.DB.session.flush()

    created_relations = itertools.chain(*[ c.findall('relation')
                                           for c in creations])
    created_relations = {
            int(atts["id"]):
                ( osm.Relation(
                    timestamp=datetime.now(tz.utc),
                    uid=fl.current_user.id,
                    changeset_id=cid,
                    tags={tag.attrib['k']: tag.attrib['v']
                          for tag in node.findall('tag')},
                    version=1,
                    visible=True)
                , node.findall('member'))
            for node in created_relations
            for atts in (node.attrib,)}

    for old_id, (relation, members) in created_relations.items():
        osm.DB.session.add(relation)
        osm.DB.session.flush()
        relation.old_id = old_id
        relation.tag = "relation"
        for member in members:
            typename = member.attrib['type']
            member_type = (osm.Node
                           if typename == 'node'
                           else (osm.Way if typename == 'way'
                           else osm.Relation))
            reference = ERAs(
                    element_id=member_type.query.filter_by(
                        id = int(member.attrib['ref'])).first().element_id,
                    relation_id=relation.id)
            if member.attrib['role']:
                reference.role = member.attrib['role']

            osm.DB.session.add(reference)

        created_nodes.append(relation)

    osm.DB.session.flush()

    modifications = xml.findall('modify')
    modified_relations = list(
            itertools.chain(*[c.findall('relation') for c in modifications]))
    for xml_node in modified_relations:
        atts = xml_node.attrib
        relation = osm.Relation.query.filter_by(id = int(atts["id"])).first()
        relation.old_id = relation.id
        relation.version = atts["version"]
        relation.changeset = osm.Changeset.query.filter_by(
                id = int(atts["changeset"])).first()
        relation.tags.update({tag.attrib['k']: tag.attrib['v']
                              for tag in xml_node.findall('tag')})
        members = xml_node.findall('member')
        nodes = {str(element.id): element for element in relation.elements
                                          if element.typename == 'node'}
        ways = {str(element.id): element for element in relation.elements
                                         if element.typename == 'way'}
        relations = {str(element.id): element
                for element in relation.elements
                if element.typename == 'relation'}
        for member in members:
            if member.attrib['type'] == 'node':
                reference = nodes.get(member.attrib['ref'],
                                      ERAs(element_id=osm.Node.query.filter_by(
                                              id = int(member.attrib['ref'])
                                              ).first().element_id,
                                          relation_id=relation.id))
            elif member.attrib['type'] == 'way':
                reference = ways.get(member.attrib['ref'],
                                     ERAs(element_id=osm.Way.query.filter_by(
                                             id = int(member.attrib['ref'])
                                             ).first().element_id,
                                         relation_id=relation.id))
            elif member.attrib['type'] == 'relation':
                reference = relations.get(
                        member.attrib['ref'],
                        ERAs(element_id=osm.Relation.query.filter_by(
                                id = int(member.attrib['ref'])
                                ).first().element_id,
                            relation_id=relation.id))

            if member.attrib['role']:
                reference.role = member.attrib['role']

            osm.DB.session.add(reference)

    for element in modified_relations:
        element.tag = "relation"
        created_nodes.append(element)

    osm.DB.session.commit()

    return flask.render_template('diffresult.xml', modifications=created_nodes)

@app.route('/iD/api/0.6/changeset/<id>/close', methods=['PUT'])
@app.route('/iD/connection/api/0.6/changeset/<id>/close', methods=['PUT'])
@cors.cross_origin()
def close_changeset(id):
    return ""

def attach_node_attribute_hash(node):
    node.attributes = {
            ("changeset" if k == "changeset_id" else k):
            (v.name if k == "user" else (
             v.replace(microsecond=0).isoformat() if k == "timestamp" else (
             str(v).lower() if k == "visible" else
             v)))
            for k in ["lat", "lon", "version", "timestamp", "visible", "uid",
                      "user", "changeset_id", "id"]
            for v in (getattr(node, k),)}
    return node

@app.route('/osm/api/0.6/nodes')
@cors.cross_origin()
def get_nodes():
    # TODO: See whether you can make this better by querying only once.
    #       Maybe 'in' works?
    nodes = [attach_node_attribute_hash(
                osm.Node.query.filter_by(id = int(node_id)).first())
            for node_id in flask.request.args['nodes'].split(",")]
    template = flask.render_template('node.xml', nodes=nodes)
    return xml_response(template)

def attach_non_node_attribute_hash(non_node):
    non_node.attributes = {
            ("changeset" if k == "changeset_id" else k):
            (v.name if k == "user" else (
             v.replace(microsecond=0).isoformat() if k == "timestamp" else (
             str(v).lower() if k == "visible" else
             v)))
            for k in ["version", "timestamp", "visible", "uid",
                      "user", "changeset_id", "id"]
            for v in (getattr(non_node, k),)}
    return non_node

@app.route('/osm/api/0.6/ways')
@cors.cross_origin()
def get_ways():
    # TODO: See whether you can make this better by querying only once.
    #       Maybe 'in' works?
    ways = [attach_non_node_attribute_hash(
                osm.Way.query.filter_by(id = int(way_id)).first())
           for way_id in flask.request.args['ways'].split(",")]
    template = flask.render_template('ways.xml', ways=ways)
    return xml_response(template)

@app.route('/osm/api/0.6/relations')
def get_relations():
    relations = [
            attach_non_node_attribute_hash(
                osm.Relation.query.filter_by(id = int(relation_id)).first())
            for relation_id in flask.request.args['relations'].split(",")]
    template = flask.render_template('relations.xml', relations=relations)
    return xml_response(template)

##### Persistence code ends here ##############################################


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
