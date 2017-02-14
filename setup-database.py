import openmod.sh.schemas.oms as oms
from openmod.sh import web

web.app.app_context().push()
oms.DB.create_all()
oms.DB.session.flush()

username = 'admin'
user = oms.User(username, username)
oms.DB.session.add(user)
oms.DB.session.flush()


################################################################################
# Add pypsa test data ##########################################################
################################################################################

json_input = [{"name": "bus1", "type": "bus", "tags": {"v_nom": 20},
                 "geom": "POLYGON((9.2 54.1, 9.6 54.1, 9.6 54.3, 9.2 54.3, 9.2 54.1))"},
              {"name": "bus2", "type": "bus", "tags": {"v_nom": 20},
                 "geom": "POLYGON((9.8 54.1, 10.1 54.1, 10.1 54.3, 9.8 54.3, 9.8 54.1))"},
              {"name": "gen1", "type": "generator",
                 "tags": {"control": "PQ", "p_set": 100}, "successors": ["bus1"],
                 "geom": "POINT(9.5 54.2)"},
              {"name": "line1", "type": "line", "tags": {"r": 0.01, "x": 0.1},
                 "predecessors": ["bus1"], "successors": ["bus2"],
                 "geom": "LINESTRING(9.6 54.2, 9.8 54.2)"},
              {"name": "load1", "type": "load", "tags": {"p_set": 100},
                 "predecessors": ["bus2"],
                 "geom": "POINT(9.9 54.2)"}]


# so far: components are always children of buses

elements = {}

scenario = {'type': 'scenario', 'name': 'pypsa-test', 'tags': {'model': 'pypsa'}}
tags = [oms.Tag(k,v) for k,v in scenario['tags'].items()]
scenario_element = oms.Element(user=user, tags=tags, name=scenario['name'],
                               type=scenario['type'])
elements[scenario['name']] = scenario_element

for e in json_input:
    tags = [oms.Tag(k,v) for k,v in e['tags'].items()]
    element = oms.Element(user=user, tags=tags, name=e['name'], type=e['type'])
    if e.get('geom', None):
        geom = oms.Geom(e['geom'].split('(')[0], 'SRID=4326;' + e['geom'])
        element.geom = geom
        print(geom.elements)
    if e.get('predecessors', None):
        element.predecessors = [elements[i] for i in e['predecessors']]
    if e.get('successors', None):
        element.successors = [elements[i] for i in e['successors']]
    element.parents = [scenario_element]
    elements[e['name']] = element

for _, element in elements.items():
    oms.DB.session.add(element)

oms.DB.session.commit()
