"""
Now designed for geojson from overpass API
Only works if properties of features are key value tags
"""

import json
import geojson
from shapely.geometry import shape

input_file = "sh-grid.geojson"
output_file = "sh-grid.json"

with open(input_file, "r") as f:
    feature_collection_geojson = f.read()

feature_collection = geojson.loads(feature_collection_geojson)

children_lst = []

i = 1
for feature in feature_collection.features:
    child_dct = {}
    if feature.get('id', False):
        id = feature.get('id')
    else:
        id = i
        i += 1
    child_dct['name'] = id
    child_dct['type'] = feature['type'] # should always be Feature
    child_dct['tags'] = feature['properties']
    child_dct['geom'] = shape(feature['geometry']).wkt
    children_lst.append(child_dct)

element_dct = {}
element_dct['children'] = children_lst
del(feature_collection.features)
if feature_collection.get('id'):
    id = feature_collection.get('id')
    del(feature_collection.id)
else:
    id = 0
element_dct['name'] = id
element_dct['type'] = feature_collection.type
del(feature_collection.type)
element_dct['tags'] = {}
for k,v in feature_collection.items():
    element_dct['tags'][k] = v

features_json = json.dumps(element_dct, indent=2)

with open(output_file, 'w') as f:
    f.write(features_json)
