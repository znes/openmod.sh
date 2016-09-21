# -*- coding: utf-8 -*-
"""

"""
from datetime import datetime, timezone as tz
from openmod.sh.schemas import osm as osm
from openmod.sh import web

# This line is necessary so that flask-sqlalchemy creates a database session
# for us.
web.app.app_context().push()

# Let's store a shortcut to the session to save some typing.
DB = osm.DB.session

cs = osm.Changeset()
DB.flush()
cs = cs.id

myscenario = osm.Relation(myid='myscenario',
                          changeset_id=cs,
                          timestamp=datetime.now(tz.utc),
                          tags={'type': 'Scenario',
                                'name': 'myscenario'})
DB.add(myscenario)
DB.flush()

# Nodes
nodes = [{'lon': 10,
          'lat': 53.5,
          'hub': 'hub1',
          'tags': {'name': 'mysink',
                   'type': 'Sink',
                   'energy_amount': 100,
                   'energy_sector': 'electricity'}},
         {'lon': 10.25,
          'lat': 53.75,
          'hub': 'hub1',
          'tags': {'name': 'mysource',
                   'type': 'source',
                   'installed_power': 10,
                   'energy_sector': 'electricity'}},
         {'lon': 10.5,
          'lat': 54,
          'hub': 'hub2',
          'tags': {'name': 'mytransformer',
                   'type': 'LinearTransformer',
                   'installed_power': 100,
                   'energy_sector': 'electricity',
                   'efficiency': 0.6,
                   'fuel_type': 'coal'}}          
                   ]

# create nodes from data dictionary
hub_nodes = {}
for n in nodes:
    x = osm.Node(myid=n['tags']['name'],
                 user_id='1',
                 changeset_id=cs,
                 timestamp=datetime.now(tz.utc),
                 version=1,
                 lon=n['lon'],
                 lat=n['lat'],
                 tags=n['tags'],
                 referencing_relations = [myscenario])
    hub_nodes[n['hub']] = hub_nodes.get(n['hub'], []) + [x]
    DB.add(x)

## Hubs
#hub_tags ={'hub1': {'type': 'hub', 'balanced': True, 'name':'hub112'},
#           'hub2': {'type': 'hub1', 'balanced': True, 'name': 'hub211'}}

## create relations from
#relations = []
#for k,v in hub_tags.items():
#    r = osm.Relation(myid=k,
#                    timestamp=datetime.now(tz.utc),
#                    visible=True,
#                    elements=nodes[k],
#                    tags=v)
#    relations.append(r)
#    DB.add(r)



DB.commit()




