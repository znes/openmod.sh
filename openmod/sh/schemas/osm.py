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
class Node_Way_Associations(DB.Model):
        __tablename__ = 'node_way_associations'
        id = DB.Column(DB.Integer, primary_key=True)
        node_id = DB.Column(DB.Integer, DB.ForeignKey('node.id'))
        way_id = DB.Column(DB.Integer, DB.ForeignKey('way.id'))
        position = DB.Column(DB.Integer)
        node = DB.relationship('Node', backref='nodes_way')
        way = DB.relationship('Way')

class Element_Relation_Associations(DB.Model):
        __tablename__ = 'element_relation_associations'
        id = DB.Column(DB.Integer, primary_key=True)
        role = DB.Column(DB.String(255))
        relation_id = DB.Column(DB.Integer, DB.ForeignKey('relation.id'))
        element_id = DB.Column(DB.Integer, DB.ForeignKey('element.element_id'))
        element = DB.relationship('Element', backref='relation_associations',
                foreign_keys=[element_id])
        relation = DB.relationship('Relation', backref='element_associations',
                foreign_keys=[relation_id])

Tag_Associations = DB.Table('tag_associations',
        DB.Column('tag_id', DB.Integer, DB.ForeignKey('tag.id')),
        DB.Column('tagged_id', DB.Integer, DB.ForeignKey('tagged.tagged_id')))

# Define timeseries association tables

Element_Timeseries_Associations = DB.Table(
        'element_timeseries_associations',
        DB.Column('timeseries_id', DB.Integer, DB.ForeignKey('timeseries.id')),
        DB.Column('element_id', DB.Integer,
            DB.ForeignKey('element.element_id')))

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
    tagged_id = DB.Column(DB.Integer, primary_key=True)
    typename = DB.Column(DB.String(79))
    tag_objects = DB.relationship(Tag, secondary=Tag_Associations,
                                       collection_class=amc('key'))
    tags = association_proxy('tag_objects', 'value')
    __mapper_args__ = {'polymorphic_identity': 'tagged',
                       'polymorphic_on': typename}


class Element(Tagged):
    """ Common base class of OSM elements.

    This class collects attributes shared by all OSM elements, i.e. nodes, ways
    and/or relations. It also acts as a target for polymorphic relationships to
    more than one type of OSM element.
    """

    __mapper_args__ = {'polymorphic_identity': 'element'}

    element_id = DB.Column(DB.Integer, primary_key=True)
    tagged_id = DB.Column(DB.Integer, DB.ForeignKey(Tagged.tagged_id))
    myid = DB.Column(DB.String(255))
    version = DB.Column(DB.Integer, nullable=False)
    timestamp = DB.Column(DB.DateTime, nullable=False)
    visible = DB.Column(DB.Boolean, nullable=False)
    uid = DB.Column(DB.Integer, DB.ForeignKey(User.id))
    user = DB.relationship(User, uselist=False)
    changeset_id = DB.Column(DB.Integer, DB.ForeignKey('changeset.id'))
    changeset = DB.relationship('Changeset', uselist=False,
            foreign_keys=[changeset_id])
    referencing_relations = association_proxy('relation_associations',
            'relation',
            creator=lambda r: Element_Relation_Associations(relation=r))
    timeseries_objects = DB.relationship('Timeseries',
            secondary=Element_Timeseries_Associations,
            collection_class=amc('key'),
            cascade="all")
    timeseries = association_proxy('timeseries_objects', 'values')

    def __init__(self, **kwargs):
        self.version = 1
        self.timestamp = datetime.now(tz.utc)
        self.visible = True
        # Can't do this:
        #
        #   super().__init__(**kwargs)
        #
        # since we put non-mapped attributes on created elements during
        # `upload_changeset`.
        # This shoule be cleaned up when `upload_changeset` gets refactored.
        for k in kwargs:
            setattr(self, k, kwargs[k])

    @DB.validates('timeseries_objects', include_removes=True)
    def timeseries_tag_hook(self, key, tso, is_remove):
        """ Hackily abuse a validator to manage timeseries tags.

        This validator doesn't really do validation, but is used as a hook to
        intercept addition and removal of `timeseries_objects` on `Element`s
        and modify the `Element`'s timeseries tag accordingly.
        """

        # tso: timeseries object
        ttags = (self.tags['timeseries'].split(", ")
                 if 'timeseries' in self.tags else [])
        if is_remove:
            self.tags['timeseries'] = ", ".join(t for t in ttags
                                                  if t != tso.key)
        else:
            ttags.append(tso.key)
            self.tags['timeseries'] = ", ".join(t for t in ttags)
        if self.tags['timeseries'] == '':
            del self.tags['timeseries']
        return tso

class Node(Element):
    __mapper_args__ = {'polymorphic_identity': 'node'}
    id = DB.Column(DB.Integer, primary_key=True)
    element_id = DB.Column(DB.Integer, DB.ForeignKey(Element.element_id))

    lat = DB.Column(DB.Float, nullable=False)
    lon = DB.Column(DB.Float, nullable=False)

    ways = association_proxy('nodes_way', 'way')

    def __init__(self, lat, lon, changeset_id, **kwargs):
        super().__init__(changeset_id=changeset_id, **kwargs)
        self.lat = lat
        self.lon = lon

class Way(Element):
    __mapper_args__ = {'polymorphic_identity': 'way'}
    id = DB.Column(DB.Integer, primary_key=True)
    element_id = DB.Column(DB.Integer, DB.ForeignKey(Element.element_id))
    way_nodes = DB.relationship(Node_Way_Associations,
                                order_by=Node_Way_Associations.position,
                                collection_class=ordering_list('position'))
    nodes = association_proxy('way_nodes', 'node',
                              creator=lambda n: Node_Way_Associations(node=n))

class Relation(Element):
    __mapper_args__ = {'polymorphic_identity': 'relation'}
    id = DB.Column(DB.Integer, primary_key=True)
    element_id = DB.Column(DB.Integer, DB.ForeignKey(Element.element_id))
    elements = association_proxy('element_associations', 'element',
            creator=lambda e: Element_Relation_Associations(element=e))

    @property
    def referenced_nodes(self):
        return (x for x in self.element_associations
                  if x.element.typename == 'node')
    @property
    def referenced_ways(self):
        return (x for x in self.element_associations
                  if x.element.typename == 'way')
    @property
    def referenced(self):
        return (x for x in self.element_associations
                  if x.element.typename == 'relation')

class Changeset(Tagged):
    __mapper_args__ = {'polymorphic_identity': 'changeset'}
    id = DB.Column(DB.Integer, primary_key=True)
    tagged_id = DB.Column(DB.Integer, DB.ForeignKey(Tagged.tagged_id))

class Timeseries(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    key = DB.Column(DB.String(255), nullable=False)
    values = DB.Column(ARRAY(DB.Float, dimensions=1), nullable=False)

    def __init__(self, key, values):
        self.key = key
        self.values = values

