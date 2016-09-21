# -*- coding: utf-8 -*-
"""

"""
from datetime import datetime, timezone as tz
from openmod.sh.schemas import osm as osm
from openmod.sh import web
from random import uniform

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

myscenario = osm.Relation(myid='myscenario',
                          uid=uid,
                          changeset_id=csid,
                          timestamp=ts,
                          tags={'type': 'scenario',
                                'name': 'myscenario'})
DB.add(myscenario)
DB.flush()

# Nodes
nodes = [{'lon': 10.1,
          'lat': 54.1,
          'hubs': ['myhub1'],
          'tags': {'name': 'mysink',
                   'type': 'demand',
                   'oemof_class': 'sink',
                   'energy_amount': 100,
                   'energy_sector': 'electricity'},
          'timeseries': [uniform(0,1) for x in range(8760)]},
         {'lon': 10.2,
          'lat': 54.1,
          'hubs': ['myhub1'],
          'tags': {'name': 'mysource',
                   'type': 'volatile_generator',
                   'oemof_class': 'source',
                   'installed_power': 10,
                   'energy_sector': 'electricity'},
          'timeseries': [uniform(0,1) for x in range(8760)]},
         {'lon': 10.3,
          'lat': 54.1,
          'hubs': ['myhub1'],
          'tags': {'name': 'myheatsink',
                   'type': 'demand',
                   'oemof_class': 'sink',
                   'energy_amount': 40,
                   'energy_sector': 'heat'},
          'timeseries': [uniform(0,1) for x in range(8760)]},
         {'lon': 10.5,
          'lat': 54.1,
          'hubs': ['myhub2'],
          'tags': {'name': 'mytransformer',
                   'type': 'flexible_generator',
                   'oemof_class': 'linear_transformer',
                   'installed_power': 100,
                   'efficiency': 0.6,
                   'fuel_type': 'coal',
                   'variable_costs': 2,
                   'energy_sector': 'electricity'}},
         {'lon': 10.54,
          'lat': 54.15,
          'hubs': ['myhub2','myheathub1'],
          'tags': {'name': 'mychp',
                   'type': 'combined_flexible_generator',
                   'oemof_class': 'linear_transformer',
                   'installed_power': 70,
                   'electrical_efficiency': 0.4,
                   'thermal_efficiency': 0.4,
                   'fuel_type': 'coal',
                   'variable_costs': 3.5,
                   'energy_sector': 'powerheat'}},
         {'lon': 10.5,
          'lat': 54.2,
          'hubs': ['myhub2'],
          'tags': {'name': 'mystorage',
                   'type': 'storage',
                   'oemof_class': 'storage',
                   'installed_power': 80,
                   'installed_energy': 500,
                   'variable_costs': 0.1,
                   'energy_sector': 'electricity'}}]

hub_nodes = {}
for n in nodes:
    x = osm.Node(myid=n['tags']['name'],
                 uid=uid,
                 changeset_id=csid,
                 timestamp=ts,
                 lon=n['lon'],
                 lat=n['lat'],
                 tags=n['tags'],
                 referencing_relations = [myscenario])
    if 'timeseries' in n:
        x.timeseries['timeseries'] = n['timeseries']
    for h in n['hubs']:
        hub_nodes[h] = hub_nodes.get(h, []) + [x]
    DB.add(x)

DB.flush()

# Hubs
hubs =[{'area_nodes': [(10,54),(10.3,54),(10.3,54.2),(10,54.2),(10,54)],
        'tags': {'name': 'myhub1',
                 'type': 'hub_relation',
                 'energy_sector': 'electricity'}},
       {'area_nodes': [(10.4,54),(10.6,54),(10.6,54.2),(10.4,54.2),(10.4,54)],
        'tags': {'name': 'myhub2',
                 'type': 'hub_relation',
                 'energy_sector': 'electricity'}},
       {'area_nodes': [(10.2,54),(10.4,54),(10.4,54.2),(10.3,54.2),(10.2,54)],
        'tags': {'name': 'myheathub1',
                 'type': 'hub_relation',
                 'energy_sector': 'heat'}}]

hub_relations = {}
for h in hubs:
    hub_name = h['tags']['name']
    area_nodes = []
    for a in h['area_nodes']:
        x = osm.Node(myid = hub_name,
                     uid = uid,
                     timestamp = ts,
                     changeset_id = csid,
                     lon = a[0],
                     lat = a[1],
                     referencing_relations = [myscenario])
        DB.add(x)
        area_nodes.append(x)
    DB.flush()
    w = osm.Way(myid = hub_name,
                changeset_id = csid,
                uid = uid,
                timestamp = ts,
                nodes = area_nodes,
                tags = {'area': 'yes',
                        'name': hub_name+'_area',
                        'type':'hub_area',
                        'energy_sector': h['tags']['energy_sector']},
                referencing_relations = [myscenario])
    DB.add(w)
    r = osm.Relation(myid = hub_name,
                    timestamp = ts,
                    uid = uid,
                    changeset_id = csid,
                    elements = hub_nodes[hub_name] + [w],
                    tags = h['tags'],
                    referencing_relations = [myscenario])
    hub_relations[hub_name] = r
    DB.add(r)

# Transmissions
trans =[{'area_nodes': [(10.3,54.1),(10.4,54.1)],
         'hubs': ['myhub1', 'myhub2'],
        'tags': {'name': 'mytrans',
                 'type': 'transmission',
                 'line': 'yes',
                 'oemof_class': 'linear_transformer',
                 'installed_power': 10,
                 'efficiency': 0.95,
                 'energy_sector': 'electricity'}}]

for t in trans:
    trans_name = t['tags']['name']
    hub_ids = t['hubs']
    area_nodes = []
    for a in t['area_nodes']:
        x = osm.Node(myid = trans_name,
                     uid = uid,
                     timestamp = ts,
                     changeset_id = csid,
                     lon = a[0],
                     lat = a[1],
                     referencing_relations = [myscenario])
        DB.add(x)
        area_nodes.append(x)
    DB.flush()
    w = osm.Way(myid = trans_name,
                changeset_id = csid,
                uid = uid,
                timestamp = ts,
                nodes = area_nodes,
                tags = t['tags'],
                referencing_relations = [myscenario] + [hub_relations[i] for i in hub_ids])
    DB.add(w)

DB.commit()

