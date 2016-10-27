# -*- coding: utf-8 -*-
"""
The scenario has to be specified in semicolon separated values files like:

scenario.csv
hubs.csv
components.csv
timeseries.csv

All columns are separated by semicolon. Do not use additional white spaces.

On usage you have to specify the directory with the files as specified above.

Usage:
python create-geojson-from-csv.py csv-directory outputfile

"""
import pandas as pd
import os
import sys
import geojson as gj

def extract_coordinates(coords):
    coords = coords.split(',')
    coords = [tuple([float(c) for c in co.split(' ')]) for co in coords]
    return coords

def create_features(df):
    features = []
    properties = [c for c in list(df) if c not in ['name','geom','timeseries']]
    for _, row in df.iterrows():
        coords = extract_coordinates(row['geom'])
        name = row['name']
        if len(coords) == 1:
            feature = gj.Feature(id=name,
                                 geometry=gj.Point(coords[0]))
        elif row['type'] == 'hub_relation':
            feature = gj.Feature(id=name,
                                 geometry=gj.Polygon([coords]))
        else:
            feature = gj.Feature(id=name,
                                 geometry=gj.LineString(coords))
        for prop in properties:
            prop_value = row[prop]
            if pd.notnull(prop_value):
                if prop == 'hubs':
                    prop_value = prop_value.split(',')
                feature['properties'][prop] = prop_value
        if 'timeseries' in df:
            ts_value = row['timeseries']
            if pd.notnull(ts_value):
                feature['properties']['timeseries'] = list(timeseries_df[ts_value])
        features.append(feature)
    return features

scenario_path = sys.argv[1]
output_filename = sys.argv[2]

scenario_df = pd.read_csv(os.path.join(scenario_path, 'scenario.csv'), sep=';')
components_df = pd.read_csv(os.path.join(scenario_path, 'components.csv'), sep=';')
timeseries_df = pd.read_csv(os.path.join(scenario_path, 'timeseries.csv'), sep=';')
hubs_df = pd.read_csv(os.path.join(scenario_path, 'hubs.csv'), sep=';')

features = create_features(components_df)
features.extend(create_features(hubs_df))
feature_collection = gj.FeatureCollection(features)

scenario_dict = dict(scenario_df.iloc[0])
# json package does not serialize numpy.int64 therefore
scenario_dict['scenario_year'] = int(scenario_dict['scenario_year'])
# probably better to use https://pypi.python.org/pypi/geojson/#custom-classes
feature_collection['scenario'] = scenario_dict

validation = gj.is_valid(feature_collection)
print("Feature collection is valid: " + validation['valid'])
if validation['valid'] != 'yes':
    print(validation['message'])
    raise Exception()

with open(output_filename, 'w') as output_file:
    gj.dump(feature_collection, output_file, sort_keys=True)

print("File saved in " + os.path.join(os.getcwd(), output_filename))

