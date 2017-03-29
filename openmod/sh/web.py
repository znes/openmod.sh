from collections import namedtuple
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
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy.orm import aliased
from shapely.geometry import box
import wtforms as wtf
from werkzeug.utils import secure_filename

import oemof.db

from .bookkeeping import PointIds, InMemorySessionInterface as IMSI
from .schemas import oms as schema



app = flask.Flask(__name__)
# For production deployment: generate a different one via Python's `os.urandom`
# and store it in a safe place.
# See: http://flask.pocoo.org/docs/0.11/quickstart/#sessions
app.secret_key = b"DON'T USE THIS IN PRODUCTION! " + b'\xdb\xcd\xb4\x8cp'
app.session_interface = IMSI()

# Set up a pool of workers to which jobs can be submitted and a dictionary
# which stores the asynchronous result objects.
app.workers = mpp.Pool(4)
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

csrf = wtfl.csrf.CSRFProtect(app)

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

# TODO: LOGIN SHOULD BE ENABLE FOR PRODUCTION AGAIN
app.config['LOGIN_DISABLED'] = True

login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    user = schema.User.query.get(user_id) if user_id else None
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
        user = load_user(schema.User.name2id(form.username.data))
        #if user is not None:
        if ((user is not None) and (user.check_pw(form.password.data))):
                fl.login_user(user)
                flask.session['id-tracker'] = PointIds()
                #print("Current user: {}".format(fl.current_user))
        else:
                flask.flash('Invalid username/password combination.')
                return form.redirect('login')
        #else:
        #    user = schema.User(form.username.data, form.password.data)
        #    schema.DB.session.add(user)
        #    schema.DB.session.commit()
        #    flask.flash('User "{}" created.'.format(user.name))
        #    fl.login_user(user)
        # From now on: user logged in.
        # TODO: Doesn't seem to work, as `flask.request.args.get('next')` is
        #       always none. Have a look at http://flask.pocoo.org/snippets/63/
        #       for pointers on how to make this work.
        return form.redirect('login')
    return flask.render_template('login.html', form=form)

@app.route('/logout')
def logout():
    fl.logout_user()
    del app.session_interface[flask.session.sid]
    flask.flash('Logged out')
    return flask.redirect(flask.url_for('login'))

##### User Management stuff ends here (except for the `@fl.login_required`).

app.config['SQLALCHEMY_DATABASE_URI'] = oemof.db.url(schema.configsection)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
schema.DB.init_app(app)

@app.route('/')
@fl.login_required
def root():
    return flask.redirect('/scenario_overview')
