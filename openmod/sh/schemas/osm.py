from datetime import datetime, timezone as tz
from flask_sqlalchemy import SQLAlchemy
import werkzeug.security as ws

DB = SQLAlchemy()

class User(DB.Model):
    """ Required by flask-login.

    See: https://flask-login.readthedocs.io/en/latest/#your-user-class

    This implementation just stores users in memory in a class variable and
    creates new users as they try to log in.
    """

    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(79), unique=True)
    password_hash = DB.Column(DB.String)
    is_active = DB.Column(DB.Boolean)

    @classmethod
    def name2id(cls, name):
        user = cls.query.filter_by(name=name).first()
        return user and user.id

    def __init__(self, name, pw):
        self.name = name
        self.password_hash = ws.generate_password_hash(pw)
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def check_pw(self, pw):
        return ws.check_password_hash(self.password_hash, pw)

# Association tables for many-to-many relationships.
# Tags can appear just about anywhere...

nodes_and_ways = DB.Table('nodes_and_ways',
        DB.Column('node_id', DB.Integer, DB.ForeignKey('node.id')),
        DB.Column('way_id', DB.Integer, DB.ForeignKey('way.id')))

tags_and_nodes = DB.Table('tags_and_nodes',
        DB.Column('tag_id', DB.Integer, DB.ForeignKey('tag.id')),
        DB.Column('node_id', DB.Integer, DB.ForeignKey('node.id')))

tags_and_ways = DB.Table('tags_and_ways',
        DB.Column('tag_id', DB.Integer, DB.ForeignKey('tag.id')),
        DB.Column('way_id', DB.Integer, DB.ForeignKey('way.id')))

tags_and_changesets = DB.Table('tags_and_changesets',
        DB.Column('tag_id', DB.Integer, DB.ForeignKey('tag.id')),
        DB.Column('changeset_id', DB.Integer, DB.ForeignKey('changeset.id')))

# No association tables anymore. These are regular models.

class Tag(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    value = DB.Column(DB.String(255), nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class Node(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    lat = DB.Column(DB.Float, nullable=False)
    lon = DB.Column(DB.Float, nullable=False)
    version = DB.Column(DB.Integer, nullable=False)
    timestamp = DB.Column(DB.DateTime, nullable=False)
    visible = DB.Column(DB.Boolean, nullable=False)
    tags = DB.relationship(Tag, secondary=tags_and_nodes)
    uid = DB.Column(DB.Integer, DB.ForeignKey(User.id))
    user = DB.relationship(User, uselist=False)
    changeset = DB.relationship('Changeset', uselist=False)
    changeset_id = DB.Column(DB.Integer, DB.ForeignKey('changeset.id'))

    def __init__(self, lat, lon, user_id, changeset_id, tags=(), **kwargs):
        self.lat = lat
        self.lon = lon
        self.version = 1
        self.timestamp = datetime.now(tz.utc)
        self.visible = True
        self.uid = user_id
        self.changeset_id = changeset_id
        self.tags = [Tag(key=k, value=v) for k, v in tags]
        for k in kwargs:
            setattr(self, k, kwargs[k])

class Way(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    tags = DB.relationship(Tag, secondary=tags_and_ways)
    nodes = DB.relationship(Node, secondary=nodes_and_ways)

class Changeset(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    tags = DB.relationship(Tag, secondary=tags_and_changesets)
    def __init__(self, tags=()):
        self.tags = [Tag(key=k, value=v) for k, v in tags]

