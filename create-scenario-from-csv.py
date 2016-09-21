# -*- coding: utf-8 -*-
"""
The scenario has to be specified in semicolon separated values files like:

test-scenario.scsv
test-demand.scsv
test-flexible-generator.scsv

With test being the scenario name.

Usage:
python create-scenario-from-csv.py data/scenarios/test

"""

import pandas as pd
import os
import sys
from datetime import datetime, timezone as tz
from openmod.sh.schemas import osm as osm
from openmod.sh import web

try:
    scenario = sys.argv[1]
except IndexError:
    raise IOError("Please specify scenario: " + \
                  "python create-scenario-from-csv.py .../myscenario")

scenario_pd = pd.read_csv(scenario + '-scenario.scsv', sep=';')

if len(scenario_pd) != 1:
    raise Exception("There schould be exactly one row. " + \
                    "Please specify only one scenario = one row")

demand_pd = pd.read_csv(scenario + '-demand.scsv', sep=';')

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

for i,r in scenario_pd.iterrows():
    x = osm.Relation(uid = uid,
                     changeset_id = csid,
                     timestamp = ts,
                     myid = r['name'],
                     tags = {'type': 'scenario',
                             'name': r['name'],
                             'scenario_year': r['scenario_year'],
                             'scenario_description': r['scenario_description']})
    scenario_db = x
    DB.add(x)

DB.flush()

hub_nodes = {}
for i,r in demand_pd.iterrows():
    x = osm.Node(uid = uid,
                 changeset_id = csid,
                 timestamp = ts,
                 myid = r['name'],
                 lon = r['lon'],
                 lat = r['lat'],
                 tags = {'type': 'demand',
                         'oemof_class': 'sink',
                         'name': r['name'],
                         'energy_amount': r['energy_amount'],
                         'energy_sector': r['energy_sector']},
                 referencing_relations = [scenario_db])
    for h in r['hubs'].split(','):
        hub_nodes[h] = hub_nodes.get(h, []) + [x]
    # add timeseries
    DB.add(x)

DB.commit()

