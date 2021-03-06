"""
Creates a scenario in the databse from a geojson file.

Have a look at data/test1/test1.geojson for an example file.

Usage:
python geojson2db.py inputfile
"""

import sys
import os
file_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(file_path, '..'))

#import matplotlib.pyplot as plt
import pandas as pd
import geojson
from datetime import datetime, timezone as tz
from openmod.sh.schemas import osm as osm
from openmod.sh import web

def create_supporting_points(points, name='support'):
    nodes = []
    for p in points:
        n = osm.Node(myid = name,
                     uid = uid,
                     timestamp = ts,
                     changeset_id = csid,
                     lon = p[0],
                     lat = p[1])
        DB.add(n)
        nodes.append(n)
    DB.flush()
    return nodes

oemof_classes = {'demand': 'sink',
                 'volatile_generator': 'source',
                 'flexible_generator': 'linear_transformer',
                 'combined_flexible_generator': 'linear_transformer',
                 'storage': 'storage',
                 'transmission': 'linear_transformer'}

def make_tags(feature):
    tags = feature['properties'].copy()
    tags.pop('hubs', None)
    for key, value in tags.copy().items():
        if isinstance(value, list):
            tags[key] = 'timeseries'
    tags['name'] = feature['id']
    if feature['properties']['type'] in oemof_classes:
        tags['oemof_class'] = oemof_classes[feature['properties']['type']]
    return tags

input_filename = sys.argv[1]

with open(input_filename, 'r') as input_file:
    scenario_dict = geojson.load(input_file)

scenario_meta = scenario_dict['scenario']

# plot if wanted
#scenario_gdf.plot()
#plt.show()

# This line is necessary so that flask-sqlalchemy creates a database session
# for us.
web.app.app_context().push()

# Let's store a shortcut to the session to save some typing.
DB = osm.DB.session

cs = osm.Changeset()
DB.add(cs)
DB.flush()

uid = '1'
csid = cs.id
ts= datetime.now(tz.utc)

scenario_meta['type'] = 'scenario'
scenario = osm.Relation(myid=scenario_meta['name'],
                        uid=uid,
                        changeset_id=csid,
                        timestamp=ts,
                        tags=scenario_meta)
DB.add(scenario)
DB.flush()


features = scenario_dict['features']
points = [f for f in features if f['geometry']['type'] == 'Point']
linestrings = [f for f in features if f ['geometry']['type'] == 'LineString']
polygons = [f for f in features if f['geometry']['type'] == 'Polygon']

hub_elements = {}

print("Adding points")
number_of_points = len(points)
i = 0
for f in points:
    i += 1
    print(i, 'of', number_of_points)
    n = osm.Node(myid=f['id'],
                 uid=uid,
                 changeset_id=csid,
                 timestamp=ts,
                 lon=f['geometry']['coordinates'][0],
                 lat=f['geometry']['coordinates'][1],
                 tags=make_tags(f),
                 referencing_relations = [scenario])
    for key,value in n.tags.copy().items():
        if value == 'timeseries':
            n.timeseries[key] = f['properties'][key]
    DB.add(n)
    for h in f['properties']['hubs']:
        hub_elements[h] = hub_elements.get(h, []) + [n]

DB.flush()

print("Adding linestrings")
for f in linestrings:
    nodes = create_supporting_points(f['geometry']['coordinates'], f['id'])
    w = osm.Way(myid = f['id'],
                changeset_id = csid,
                uid = uid,
                timestamp = ts,
                nodes = nodes,
                tags = make_tags(f),
                referencing_relations = [scenario])
    DB.add(w)
    for h in f['properties']['hubs']:
        hub_elements[h] = hub_elements.get(h, []) + [w]

DB.flush()

print("Adding polygons")
for f in polygons:
    nodes = create_supporting_points(f['geometry']['coordinates'][0], f['id'])
    w = osm.Way(myid = f['id'],
                changeset_id = csid,
                uid = uid,
                timestamp = ts,
                nodes = nodes,
                tags = {'area': 'yes',
                        'name': f['id'] +'_area',
                        'type':'hub_area',
                        'energy_sector': f['properties']['energy_sector'],
                    # remove this line below, if not needed anymore for testing
                        'value' : f['properties'].get('value', 0)},
                referencing_relations = [scenario])
    DB.add(w)
    hub_elements[f['id']] = hub_elements.get(f['id'], []) + [w]
    r = osm.Relation(myid = f['id'],
                    timestamp = ts,
                    uid = uid,
                    changeset_id = csid,
                    elements = hub_elements[f['id']],
                    tags = make_tags(f),
                    referencing_relations = [scenario])
    DB.add(r)

DB.flush()

print("Commiting to database. Be patient.")
DB.commit()
print("Imported successfully.")

