# -*- coding: utf-8 -*-
"""

"""
from sqlalchemy import create_engine, text
import pandas as pd
import geojson

uri = "postgresql+psycopg2://openmodsh_admin:3nergykollekt!v@localhost:5434/openmodsh"
engine = create_engine(uri)

#
sql = text("SELECT gen, ags id, ST_AsGeoJson(ST_Simplify(ST_Transform(geom, 4326), 0.01)) area," +
	" ST_AsGeoJson(ST_Centroid(ST_Transform(geom, 4326))) point" +
	" FROM orig_vg250.vg250_4_krs WHERE rs LIKE '01%' and gf != 2;")
geoms = pd.read_sql(sql, con=engine)
geoms.index = geoms['id']
geoms.index = [str(l.lstrip("0"))+'_heat' for l in geoms.index.values]


# read geojson file
path='../data/scenarios/sh/sh_heat_template.geojson'
with open(path) as data_file:
    data = geojson.load(data_file)

# add
for f in data['features']:
    if f['properties']['type'] == 'hub_relation':
        f['geometry'] = eval(geoms['area'].loc[f['id']])
    if f['properties']['type'] == 'demand':
        f['geometry'] = eval(geoms['point'].loc[f['properties']['hubs'][0]])

with open('../data/scenarios/sh/sh_heat_final.geojson', 'w') as data_file:
    geojson.dump(data, data_file)

