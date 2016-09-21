from urllib.parse import urlparse, urljoin
from xml.etree.ElementTree import XML
import functools as fun
import itertools
import json

from flask_oauthlib.provider import OAuth1Provider
import flask
import flask_cors as cors # TODO: Check whether the `@cors.cross_origin()`
                          #       decorators are still necessary once 'iD' is
                          #       served from within this app.
import flask_login as fl
import flask_wtf as wtfl
import wtforms as wtf
from geoalchemy2.functions import ST_AsGeoJSON as geojson
from sqlalchemy.orm import sessionmaker

import oemof.db as db

from .schemas import dev as schema  # test as schema


app = flask.Flask(__name__)
# For production deployment: generate a different one via Python's `os.urandom`
# and store it in a safe place.
# See: http://flask.pocoo.org/docs/0.11/quickstart/#sessions
app.secret_key = b"DON'T USE THIS IN PRODUCTION! " + b'\xdb\xcd\xb4\x8cp'

Plant = schema.Plant
Timeseries = schema.Timeseries
Grid = schema.Grid

engine = db.engine("openMod.sh")

Session = sessionmaker(bind=engine)
session = Session()

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
            print("Redirecting to: {}".format(self.next.data))
            return flask.redirect(self.next.data)
        target = get_redirect_target(self.redirect_arg)
        print("Redirecting to: {}".format(target))
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

class User:
    """ Required by flask-login.

    See: https://flask-login.readthedocs.io/en/latest/#your-user-class

    This implementation just stores users in memory in a class variable and
    creates new users as they try to log in.
    """
    known = {}
    def __init__(self, name, pw):
        if name in self.known:
            raise ValueError(
                    "Trying to create user '{}' which already exists.".format(
                        name))
        self.known[name] = self
        self.name = name
        self.pw = pw
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self): return self.name

login_manager = fl.LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.known.get(user_id)

class Login(RedirectForm):
    username = wtf.StringField('Username', [wtf.validators.Length(min=3,
                                                                  max=79)])
    password = wtf.PasswordField(
            'Password', [wtf.validators.Length(min=3, max=79)])

@csrf.exempt
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = Login()
    print('Checking form validation/submission check.')
    if form.validate_on_submit():
        print("--> Login POSTed.")
        user = load_user(form.username.data)
        if user is not None:
            print("--> User exists.")
            if user.pw == form.password.data:
                print("--> Authenticated.")
                fl.login_user(user)
                #print("Current user: {}".format(fl.current_user))
            else:
                print("--> Login unsuccessfull.")
                flask.flash('Invalid username/password combination.')
                return flask.redirect(flask.url_for('login'))
        else:
            print("--> New user.")
            user = User(form.username.data, form.password.data)
            flask.flash('User "{}" created.'.format(user.name))
            fl.login_user(user)
        # From now on: user logged in.
        # TODO: Doesn't seem to work, as `flask.request.args.get('next')` is
        #       always none. Have a look at http://flask.pocoo.org/snippets/63/
        #       for pointers on how to make this work.
        print("Logged in. Redirecting.")
        return form.redirect('login')
    print('`validate_on_submit failed. Rendering template.')
    print('errors: {}'.format(form.errors))
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
    return flask.redirect('http://127.0.0.1:8000')

# TODO: Factor adding the 'Content-Type' header out into a separate function.

@app.route('/osm/api/capabilities')
@app.route('/osm/api/0.6/capabilities')
@cors.cross_origin()
def capabilities():
    template = flask.render_template('capabilities.xml', area={"max": 1},
                                     timeout=250)
    response = flask.make_response(template)
    response.headers['Content-Type'] = 'text/xml'
    return response

# Store test OSM data as attributes on an object. In a real app that data would
# be stored in/retrieved from the database.
class OSMT: pass
OSM = OSMT()
OSM.nodes = [{"lat": 0.0075, "lon": -0.0025,
              "tags": {"ele": 0, # stands for 'elevation' (usually)
                       "name": "A Test Node"}}]
OSM.changesets = []

@app.route('/osm/api/0.6/map')
@cors.cross_origin()
def osm_map():
    left, bottom, right, top = map(float, flask.request.args['bbox'].split(","))
    minx, maxx = sorted([top, bottom])
    miny, maxy = sorted([left, right])
    nodes = [dict(**n)
            for n in OSM.nodes
            for x, y in ((n["lat"], n["lon"]),)
            if minx <= x and  miny <= y and maxx >= x and maxy >= y]
    for node in nodes:
        node['id'] = node.get('id', id(node))
        node['tags'] = node.get('tags', {})
    template = flask.render_template('map.xml', nodes=nodes,
                                          minlon=miny, maxlon=maxy,
                                          minlat=minx, maxlat=maxx)

    response = flask.make_response(template)
    response.headers['Content-Type'] = 'text/xml'
    return response

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
        self.client_key = "5A043yRSEugj4DJ5TljuapfnrflWDte8jTOcWLlT"
        self.client_secret = "aB3jKq1TRsCOUrfOIZ6oQMEDmv2ptV76PA54NGLL"
        self.redirect_uris = ["http://localhost:5000/oauth-redirected",
                              # The [OAuthLib example][0] needs this redirect.
                              #
                              # [0]: https://oauthlib.readthedocs.io/en/latest/oauth1/server.html#try-your-provider-with-a-quick-cli-client
                              "http://127.0.0.1/cb",
                              # This one is needed by the iD editor. This is
                              # where the user is redirected to after
                              # authorizing iD, so that iD gets to know that it
                              # can go on.
                              "http://127.0.0.1:8000/land.html"]
        self.default_redirect_uri = self.redirect_uris[0]
        self.default_realms = []
CLIENT = Client()

class RequestToken:
    known = []
    def __init__(self, token, request):
        print("Creating request token.")
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
    print("KNWN: {}".format(AccessToken.known))
    print("ARGS: k -> {}, t -> {}, args -> {}, kwgs: {}".format(
        client_key, token, args, kwargs))
    print("ACTS: {}".format(ats))
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
    print("wtf.Form")
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
    print("Regular ATH.")
    print("Request: {}".format(str(flask.request.headers) + "\n" +
                               flask.request.data.decode('utf-8')))
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

@app.route('/iD/connection/api/0.6/changeset/create', methods=['PUT'])
@cors.cross_origin()
def create_changeset():
    cs = {}
    OSM.changesets.append(cs)
    return str(id(cs))

@app.route('/iD/connection/api/0.6/user/details', methods=['GET'])
@cors.cross_origin()
def userdetails():
    cu = fl.current_user
    fl.id = id(fl)
    return flask.render_template('userdetails.xml', user=fl.current_user)

@app.route('/iD/connection/api/0.6/changeset/<cid>/upload', methods=['POST'])
@cors.cross_origin()
def upload_changeset(cid):
    xml = XML(flask.request.data)
    creations = xml.findall('create')
    created_nodes = itertools.chain(*[c.findall('node') for c in creations])
    created_nodes = [
            {"lat": float(n["lat"]), "lon": float(n["lon"]),
             "old_id": n["id"], "version": n["version"],
             "tags": fun.reduce(
                 lambda old, new: old.update(new) or old,
                 [{k: float(v) if k in ["lat", "lon"] else v}
                     for tag in node.findall('tag')
                     for k, v in ((tag.attrib['k'], tag.attrib['v']),)],
                 {})}
            for node in created_nodes
            for n in (node.attrib,)]
    for n in created_nodes:
        n["new_id"] = id(n)
        n["id"] = id(n)
    OSM.nodes.extend(created_nodes)
    return flask.render_template('diffresult.xml', nodes=created_nodes)

@app.route('/iD/connection/api/0.6/changeset/<id>/close', methods=['PUT'])
@cors.cross_origin()
def close_changeset(id):
    return ""

##### Persistence code ends here ##############################################

@app.route('/series/<path:ids>')
def series(ids):
    ids = ids.split("/")
    series = session.query(Timeseries).order_by(Timeseries.plant,
                                                Timeseries.step)
    if ids:
        series = series.filter(Timeseries.plant.in_(ids))
    # Better but still improvable. Now generates one query per plant, which
    # incurs the time overhead of a database request for each plant. But at
    # least we no longer have quadratic complexity.
    # If you want to know why the data is structured the way it is, consult the
    # [Flot data format][0] documentation.
    #
    # [0]: https://github.com/flot/flot/blob/master/API.md#data-format
    series_data = [{"lines": {"show": False}, "lines": {"fill": True},
                    "label": plant,
                    "data": [[t.step, t.value]
                             for t in ts]}
                   for plant, ts in itertools.groupby(series,
                                                      lambda s: s.plant)]
    series_json = json.dumps(series_data)
    return series_json


@app.route('/plants-json')
@app.route('/plants-json/<t>')
def plant_coordinate_json(t=None):
    # TODO: Maybe SQLAlchemy's "relationship"s can be used to do this in a
    #       simpler or more efficient way. The only problem is, that here,
    #       there is a one-to-many relationship from points/locations to
    #       powerplants, but points do not have a separate/dedicated table and
    #       therefore no uid (create a view maybe?).
    #       BUT: Using groupby on an ordered collection is already very
    #            efficient because:
    #
    #              * there is only one query (yeah, it's ordered, but thats
    #                what the DBMS is for),
    #              * the queryset is only traversed once,
    #              * 'groupby' is written in C (i.e. lightning fast) and MEANT
    #                for exactly this scenario.
    #
    #            So even if we figure out a way to do this via SQLAlchemy
    #            relationships, it's questionable whether those are faster.
    plants = session.query(geojson(Plant.geometry).label("gjson"),
                           Plant.capacity, Plant.id
                           ).order_by(Plant.geometry)
    if t:
        plants = plants.filter(Plant.type == t)
    return json.dumps({"features": [{"type": "Feature",
                                     "geometry": json.loads(k),
                                     "properties": {
                                         "plants": [{"id": p.id,
                                                     "capacity": p.capacity}
                                                    for p in ps]
                                     }}
                                    for k, ps in itertools.groupby(
                                        plants, lambda p: p.gjson)],
                       "type": "FeatureCollection"})


@app.route('/grids-json')
def grid():
    grids = session.query(geojson(Grid.geometry).label("gjson"),
                          Grid.voltage, Grid.id).all()
    return json.dumps({"features": [{"type": "Feature",
                                     "geometry": json.loads(g.gjson),
                                     "properties": {"id": g.id,
                                                    "voltage": g.voltage
                                                    }}
                                    for g in grids],
                       "type": "FeatureCollection"})


@app.route('/types')
def types():
    return json.dumps([p.type for p in
                       session.query(Plant.type).distinct().all()])


@app.route('/csv/<path:ids>')
def csv(ids):
    ids = ids.split("/")
    plants = session.query(Plant.id, Plant.capacity).order_by(Plant.id)
    if ids:
        plants = plants.filter(Plant.id.in_(ids))
    header = [d["name"] for d in plants.column_descriptions]
    app.logger.debug(header)
    plants = plants.all()
    body = "\n".join([",".join([str(getattr(p, k)) for k in header])
                      for p in plants])
    response = flask.make_response(",".join(header) + "\n" + body)
    response.headers["Content-Disposition"] = ("attachment;" +
                                               "filename=eeg_extract.csv")
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
