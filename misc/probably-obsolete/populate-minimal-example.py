# -*- coding: utf-8 -*-
"""

"""
from datetime import datetime, timezone as tz
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from openmod.sh.schemas import osm as osm
from openmod.sh import web

# This line is necessary so that flask-sqlalchemy creates a database session
# for us.
web.app.app_context().push()

# Let's store a shortcut to the session to save some typing.
DB = osm.DB.session

# Components
components = [{'name':'wind1', 'installed_capacity': 10, 'fixed': True,
               'class':'source', 'lon':10, 'lat':53.5, 'hub': 'hub1'},
              {'name':'wind2', 'installed_capacity': 11, 'fixed': True,
               'class':'source', 'lon':10, 'lat':53.6, 'hub': 'hub2'},
              {'name': 'powerplant', 'installed_capacity':100, 'lon':10.3,
               'lat':53.1, 'class':'LinearTransformer', 'fuel':'gas',
               'hub':'hub1'}]
cs = osm.Changeset()
DB.flush()

cs = cs.id

# create nodes from data dictionary
nodes = {}
for c in components:
    n = osm.Node(myid=c['name'],
                 user_id='1',
                 changeset_id=cs,
                 timestamp=datetime.now(tz.utc),
                 version=1,
                 lon=c['lon'],
                 lat=c['lat'],
                 tags={'adad':'asd'})
    nodes[c['hub']] = nodes.get(c['hub'], []) + [n]
    DB.add(n)

# Hubs
hub_tags ={'hub1': {'type': 'hub', 'balanced': True, 'name':'hub112'},
           'hub2': {'type': 'hub1', 'balanced': True, 'name': 'hub211'}}

# create relations from
relations = []
for k,v in hub_tags.items():
    r = osm.Relation(myid=k,
                    timestamp=datetime.now(tz.utc),
                    visible=True,
                    elements=nodes[k],
                    tags=v)
    relations.append(r)
    DB.add(r)



DB.commit()




