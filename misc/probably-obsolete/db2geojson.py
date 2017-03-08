# -*- coding: utf-8 -*-
"""
Creates a geojson file from a selected scenario in the database.

Usage:
python db2geojson.py scenarioname outputfile
"""
import sys
import os
file_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(file_path, '..'))

import oemof.db as db
from sqlalchemy.orm import sessionmaker
from openmod.sh.schemas import osm
import geojson as gj

scenario_name = sys.argv[1]
output_filename = sys.argv[2]

engine = db.engine('openMod.sh R/W')

Session = sessionmaker(bind=engine)
session = Session()

scenarios = session.query(osm.Relation).all()
scenarios = [s for s in scenarios if s.tags['type'] == 'scenario' and
                                     s.tags['name'] == scenario_name]

if len(scenarios) == 0:
    raise Exception("No scenario found with name: " + scenario_name)
if len(scenarios) > 1:
    raise Exception("There are more than one scenarios with name: " +
                    scenario_name)

scenario = scenarios[0]
elements = scenario.elements
nodes = [n for n in elements if isinstance(n, osm.Node)]
# only transmissions
ways = [w for w in elements if isinstance(w, osm.Way) and
                               w.tags['type'] == 'transmission']
# only hub relations
relations = [r for r in elements if isinstance(r, osm.Relation)  and
                                    r.tags['type'] == 'hub_relation']

#print([n.tags.get('name') for n in nodes])

print("Creating features...")
features = []
# create all nodes (in nodes there should be node 'help' nodes!!!)
for n in nodes:
    feature = gj.Feature(id=n.tags.get('name'),
                         geometry=gj.Point([n.lon, n.lat]))

    for k,v in n.tags.items():
        if k != 'name' and k != 'oemof_class':
            feature['properties'][k] = v
        if v == 'timeseries':
            feature['properties'][k] = n.timeseries.get(k, None)
    hubs = [r for r in n.referencing_relations 
            if r.tags['type'] == 'hub_relation']
    feature['properties']['hubs'] = [h.tags['name'] for h in hubs]
    features.append(feature)

# create all hub relations
for r in relations:
    w = [way for way in r.elements if way.tags['type'] == 'hub_area'][0]
    feature = gj.Feature(id=r.tags.get('name'),
                         geometry=gj.Polygon([[[n.lon, n.lat]
                                               for n in w.nodes]]))
    for k,v in r.tags.items():
        if k != 'name' and k != 'oemof_class':
            feature['properties'][k] = v
    features.append(feature)

# create all transmissions
for w in ways:
    feature = gj.Feature(id=w.tags.get('name'),
                         geometry=gj.LineString([[n.lon, n.lat]
                                                 for n in w.nodes]))
    for k,v in w.tags.items():
        if k != 'name' and k != 'oemof_class':
            feature['properties'][k] = v
    hubs = [r for r in n.referencing_relations 
            if r.tags['type'] == 'hub_relation']
    feature['properties']['hubs'] = [h.tags['name'] for h in hubs]
    features.append(feature)


feature_collection = gj.FeatureCollection(features)
feature_collection['scenario'] = dict(scenario.tags)

validation = gj.is_valid(feature_collection)
print("Feature collection is valid: " + validation['valid'])
if validation['valid'] != 'yes':
    print(validation['message'])
    raise Exception()

with open(output_filename, 'w') as output_file:
    gj.dump(feature_collection, output_file, sort_keys=True)

print("File saved in " + os.path.join(os.getcwd(), output_filename))
