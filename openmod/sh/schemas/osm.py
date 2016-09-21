from flask_sqlalchemy import SQLAlchemy
import werkzeug.security as ws

DB = SQLAlchemy()

class User():
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
        self.password_hash = ws.generate_password_hash(pw)
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self): return self.name

    def check_pw(self, pw):
        return ws.check_password_hash(self.password_hash, pw)

