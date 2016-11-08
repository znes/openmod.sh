# -*- coding: utf-8 -*-
"""
"""
import oemof.db as db
from sqlalchemy.orm import sessionmaker
from openmod.sh.schemas import osm
import geojson as gj

engine = db.engine('openMod.sh R/W')

Session = sessionmaker(bind=engine)
session = Session()

scenario = session.query(osm.Relation).filter_by(
                         #id = int(kwargs['scenario'][1:])).first()
                         id = 1).first()

elements = scenario.elements
nodes = [n for n in elements if isinstance(n, osm.Node)]
ways = [w for w in elements if isinstance(w, osm.Way)]
# only hub relations
relations = [r for r in elements if isinstance(r, osm.Relation)]

#print([n.tags.get('name') for n in nodes])

features = []
# create all nodes (in nodes there should be node 'help' nodes!!!)
for n in nodes:
    feature = gj.Feature(id=n.tags.get('name'),
                         geometry=gj.Point([n.lon, n.lat]))

    for k,v in n.tags.items():
        if k != 'name':
            feature['properties'][k] = v
        if v == 'timeseries':
            feature['properties'][k] = n.timeseries[k]
    features.append(feature)

# create all hub relations
for r in relations:
    feature = gj.Feature(id=r.tags.get('name'))
    for k,v in n.tags.items():
        if k != 'name':
            feature['properties'][k] = v
    features.append(feature)

for w in ways:
    feature = gj.Feature(id=w.tags.get('name'),
                         geometry=gj.LineString([[n.lon, n.lat]
                                                 for n in w.nodes]))
    for k,v in n.tags.items():
        if k != 'name':
            feature['properties'][k] = v
    features.append(feature)


feature_collection = gj.FeatureCollection(features)
feature_collection['scenario'] = dict(scenario.tags)
