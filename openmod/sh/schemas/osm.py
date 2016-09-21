from datetime import datetime, timezone as tz
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
class nodes_and_ways(DB.Model):
        __tablename__ = 'nodes_and_ways'
        id = DB.Column(DB.Integer, primary_key=True)
        node_id = DB.Column(DB.Integer, DB.ForeignKey('node.id'))
        way_id = DB.Column(DB.Integer, DB.ForeignKey('way.id'))
        position = DB.Column(DB.Integer)
        node = DB.relationship('Node', backref='nodes_way')
        way = DB.relationship('Way')

class rs_and_nodes(DB.Model):
        __tablename__ = 'relations_and_nodes'
        id = DB.Column(DB.Integer, primary_key=True)
        role = DB.Column(DB.String(255))
        relation_id = DB.Column(DB.Integer, DB.ForeignKey('relation.id'))
        node_id = DB.Column(DB.Integer, DB.ForeignKey('node.id'))
        node = DB.relationship('Node', backref='referencing_relations')
        relation = DB.relationship('Relation', backref='referenced_nodes')

class rs_and_ways(DB.Model):
        __tablename__ = 'relations_and_ways'
        id = DB.Column(DB.Integer, primary_key=True)
        role = DB.Column(DB.String(255))
        relation_id = DB.Column(DB.Integer, DB.ForeignKey('relation.id'))
        way_id = DB.Column(DB.Integer, DB.ForeignKey('way.id'))
        way = DB.relationship('Way', backref='referencing_relations')
        relation = DB.relationship('Relation', backref='referenced_ways')

class rs_and_rs(DB.Model):
        __tablename__ = 'relations_and_relations'
        id = DB.Column(DB.Integer, primary_key=True)
        role = DB.Column(DB.String(255))
        referencing_id = DB.Column(DB.Integer, DB.ForeignKey('relation.id'),
            primary_key=True)
        referenced_id = DB.Column(DB.Integer, DB.ForeignKey('relation.id'),
            primary_key=True)
        referenced = DB.relationship('Relation',
                primaryjoin=("rs_and_rs.referenced_id == Relation.id"),
                backref='referencing')
        referencing = DB.relationship('Relation',
                primaryjoin=("rs_and_rs.referencing_id == Relation.id"),
                backref='referenced')

tag_associations = DB.Table('tag_associations',
        DB.Column('tag_id', DB.Integer, DB.ForeignKey('tag.id')),
        DB.Column('tagged_id', DB.Integer, DB.ForeignKey('tagged.object_id')))

# Define timeseries association tables

ts_and_nodes = DB.Table('timeseries_and_nodes',
        DB.Column('timeseries_id', DB.Integer, DB.ForeignKey('timeseries.id')),
        DB.Column('node_id', DB.Integer, DB.ForeignKey('node.id')))

ts_and_ways = DB.Table('timeseries_and_ways',
        DB.Column('timeseries_id', DB.Integer, DB.ForeignKey('timeseries.id')),
        DB.Column('way_id', DB.Integer, DB.ForeignKey('way.id')))

ts_and_rs = DB.Table('timeseries_and_relations',
        DB.Column('timeseries_id', DB.Integer, DB.ForeignKey('timeseries.id')),
        DB.Column('relation_id', DB.Integer, DB.ForeignKey('relation.id')))

# No association tables anymore. These are regular models.

class Tag(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    value = DB.Column(DB.String(255), nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class Tagged(DB.Model):
    """ Base model/table for all objects which can have tags.

    Nearly everything in OSM can have associated tags[0]. Most importantly,
    elements, i.e. nodes, ways and/or relations, have nothing in common with
    changesets, except having tags. Therefore being tagged is the only
    commonality which can be factored out into a class that is a base for
    elements as well as changesets.

    [0]: Except tags itself. Duh.
    """
    object_id = DB.Column(DB.Integer, primary_key=True)
    typename = DB.Column(DB.String(79))
    tag_objects = DB.relationship(Tag, secondary=tag_associations,
                                       collection_class=amc('key'))
    tags = association_proxy('tag_objects', 'value')
    __mapper_args__ = {'polymorphic_on': typename}


class Node(Tagged):
    __mapper_args__ = {'polymorphic_identity': 'node'}
    id = DB.Column(DB.Integer, primary_key=True)
    tagged_id = DB.Column(DB.Integer, DB.ForeignKey(Tagged.object_id))
    myid = DB.Column(DB.String(255))
    lat = DB.Column(DB.Float, nullable=False)
    lon = DB.Column(DB.Float, nullable=False)
    version = DB.Column(DB.Integer, nullable=False)
    timestamp = DB.Column(DB.DateTime, nullable=False)
    visible = DB.Column(DB.Boolean, nullable=False)
    uid = DB.Column(DB.Integer, DB.ForeignKey(User.id))
    user = DB.relationship(User, uselist=False)
    ways = association_proxy('nodes_way', 'way')
    relations = association_proxy('referencing_relations', 'relation')
    changeset = DB.relationship('Changeset', uselist=False)
    changeset_id = DB.Column(DB.Integer, DB.ForeignKey('changeset.id'))

    def __init__(self, lat, lon, user_id, changeset_id, **kwargs):
        self.lat = lat
        self.lon = lon
        self.version = 1
        self.timestamp = datetime.now(tz.utc)
        self.visible = True
        self.uid = user_id
        self.changeset_id = changeset_id
        for k in kwargs:
            setattr(self, k, kwargs[k])

class Way(Tagged):
    __mapper_args__ = {'polymorphic_identity': 'way'}
    id = DB.Column(DB.Integer, primary_key=True)
    tagged_id = DB.Column(DB.Integer, DB.ForeignKey(Tagged.object_id))
    myid = DB.Column(DB.String(255))
    version = DB.Column(DB.String)
    way_nodes = DB.relationship('nodes_and_ways',
                                order_by='nodes_and_ways.position',
                                collection_class=ordering_list('position'))
    nodes = association_proxy('way_nodes', 'node',
                              creator=lambda n: nodes_and_ways(node=n))
    relations = association_proxy('referencing_relations', 'relation')
    uid = DB.Column(DB.Integer, DB.ForeignKey(User.id))
    user = DB.relationship(User, uselist=False)
    changeset = DB.relationship('Changeset', uselist=False)
    changeset_id = DB.Column(DB.Integer, DB.ForeignKey('changeset.id'))

class Relation(Tagged):
    __mapper_args__ = {'polymorphic_identity': 'relation'}
    id = DB.Column(DB.Integer, primary_key=True)
    tagged_id = DB.Column(DB.Integer, DB.ForeignKey(Tagged.object_id))
    myid = DB.Column(DB.String(255))
    version = DB.Column(DB.String)
    timestamp = DB.Column(DB.DateTime, nullable=False)
    visible = DB.Column(DB.Boolean, nullable=False)
    uid = DB.Column(DB.Integer, DB.ForeignKey(User.id))
    user = DB.relationship(User, uselist=False)
    superiors = association_proxy('referencing', 'relation')
    changeset = DB.relationship('Changeset', uselist=False)
    changeset_id = DB.Column(DB.Integer, DB.ForeignKey('changeset.id'))

class Changeset(Tagged):
    __mapper_args__ = {'polymorphic_identity': 'changeset'}
    id = DB.Column(DB.Integer, primary_key=True)
    tagged_id = DB.Column(DB.Integer, DB.ForeignKey(Tagged.object_id))

class Timeseries(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    value = DB.Column(ARRAY(DB.Float, dimensions=1), nullable=False)

