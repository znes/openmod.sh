# this is the open-mod-schema
from datetime import datetime, timezone as tz
from itertools import chain, groupby
from flask_sqlalchemy import SQLAlchemy
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
# Tags can appear just about anywhere...

# This one is necessary to keep track of the additional ordering information.
# See:
#
#   * http://stackoverflow.com/questions/21292726/how-to-properly-use-association-proxy-and-ordering-list-together-with-sqlalchemy
#   * http://docs.sqlalchemy.org/en/latest/orm/extensions/associationproxy.html#simplifying-association-objects
#   * http://docs.sqlalchemy.org/en/latest/orm/extensions/orderinglist.html#module-sqlalchemy.ext.orderinglist
#
# for pointers on how this works.

#Element_Tag_Associations = DB.Table('element_tag_associations',
#        DB.Column('element_id', DB.Integer, DB.ForeignKey('element.element_id')),
#        DB.Column('tag_id', DB.Integer, DB.ForeignKey('tag.tag_id')))

# Define sequence association tables

#Element_Sequence_Associations = DB.Table(
#        'element_sequence_associations',
#        DB.Column('sequence_id', DB.Integer, DB.ForeignKey('sequence.sequence_id')),
#        DB.Column('element_id', DB.Integer,
#            DB.ForeignKey('element.element_id')))

# No association tables anymore. These are regular models.

class Tag(DB.Model):
    tag_id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    value = DB.Column(DB.String(255), nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class Sequence(DB.Model):
    sequence_id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    value = DB.Column(ARRAY(DB.Float, dimensions=1), nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class Geom(DB.Model):
    geom_id = DB.Column(DB.Integer, primary_key=True)
    type = DB.Column(DB.String(255), nullable=False)
    geom = DB.Column(DB.String(255), nullable=False)

    def __init__(self, type, geom):
        self.type = type
        self.geom = geom

class Element(DB.Model):
    """ Common base class
    """
    element_id = DB.Column(DB.Integer, primary_key=True)
    uid = DB.Column(DB.Integer, DB.ForeignKey(User.id))
    user = DB.relationship(User, uselist=False)
    geom_id = DB.Column(DB.Integer, DB.ForeignKey(Geom.geom_id))
    geom = DB.relationship(Geom, uselist=False)
    # many to many asscociation still missing, therfore no attributes tags and
    #  sequences yet...
    tag_id = DB.Column(DB.Integer, DB.ForeignKey(Tag.tag_id))
    sequence_id = DB.Column(DB.Integer, DB.ForeignKey(Sequence.sequence_id))
    

    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

