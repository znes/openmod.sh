# -*- coding: utf-8 -*-
"""

"""
import pandas as pd
import openmod.sh.schemas.osm as osm
from openmod.sh import web

web.app.app_context().push()
db = osm.DB.session
cs = osm.Changeset()
db.add(cs)
db.commit()


x = pd.read_csv('data/pp-sh.csv')
x['type'] = x['type'].fillna('Condesing')

for i, r in x.iterrows():
    node = osm.Node(r['lat'], r['lon'], 1, cs.id, myid="hereami",
                    tags=[("type", r["type"]),
                          ("capacity", r["capacity"]),
                          ("fuel", r["fuel"]),
                          ("commissioned", r["commissioned"])])
    db.add(node)
    db.commit()

