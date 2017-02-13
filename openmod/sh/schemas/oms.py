# this is the open-mod-schema
from datetime import datetime, timezone as tz
from itertools import chain, groupby
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import types as geotypes
from sqlalchemy import MetaData
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm.collections import attribute_mapped_collection as amc
import werkzeug.security as ws
from oemof.db import config as cfg

configsection = 'openMod.sh R/W'
metadata = MetaData(schema=cfg.get(configsection, 'schema'))
DB = SQLAlchemy(metadata=metadata)

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
        self.is_active = True

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
Element_Tag_Associations = DB.Table(
        'element_tag_associations',
        DB.Column('element_id', DB.Integer, DB.ForeignKey('element.id')),
        DB.Column('tag_id', DB.Integer, DB.ForeignKey('tag.id')))

Element_Sequence_Associations = DB.Table(
        'element_sequence_associations',
        DB.Column('sequence_id', DB.Integer, DB.ForeignKey('sequence.id')),
        DB.Column('element_id', DB.Integer, DB.ForeignKey('element.id')))

Parent_Children_Associations = DB.Table(
        'parent_children_associations',
        DB.Column('element_parent_id', DB.Integer, DB.ForeignKey('element.id')),
        DB.Column('element_child_id', DB.Integer, DB.ForeignKey('element.id')))

Predecessor_Successor_Associations = DB.Table(
        'predecessor_successor_associations',
        DB.Column('element_predecessor_id', DB.Integer, DB.ForeignKey('element.id')),
        DB.Column('element_successor_id', DB.Integer, DB.ForeignKey('element.id')))

# No association tables anymore. These are regular models.
class Tag(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    value = DB.Column(DB.String(255), nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class Sequence(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    # TODO: Could be as well an array of strings for a more generic approach
    #       Additionally then perhaps sequence and tag could be merged...
    value = DB.Column(ARRAY(DB.Float, dimensions=1), nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class Geom(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    type = DB.Column(DB.String(255), nullable=False)
    geom = DB.Column(geotypes.Geometry(), nullable=False)

    def __init__(self, type, geom):
        self.type = type
        self.geom = geom

class Element(DB.Model):
    """ Common base class
    """
    id = DB.Column(DB.Integer, primary_key=True)
    uid = DB.Column(DB.Integer, DB.ForeignKey(User.id))
    user = DB.relationship(User, uselist=False)
    # TODO: is it possible to remove geom_id?
    geom_id = DB.Column(DB.Integer, DB.ForeignKey(Geom.id))
    geom = DB.relationship(Geom, uselist=False)
    tags = DB.relationship('Tag', secondary=Element_Tag_Associations,
                           backref='elements')
    sequences = DB.relationship('Sequence',
                                secondary=Element_Sequence_Associations)
    children = DB.relationship(
            'Element',
            secondary=Parent_Children_Associations,
            primaryjoin=id==Parent_Children_Associations.c.element_parent_id,
            secondaryjoin=id==Parent_Children_Associations.c.element_child_id,
            backref='parents')
    successors = DB.relationship(
            'Element',
            secondary=Predecessor_Successor_Associations,
            primaryjoin=id==Predecessor_Successor_Associations.c.element_predecessor_id,
            secondaryjoin=id==Predecessor_Successor_Associations.c.element_successor_id,
            backref='predecessors')

    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

