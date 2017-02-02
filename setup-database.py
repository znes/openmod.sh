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

json_input = {"buses": {"bus1": {"name": "bus1", "v_nom": 20},
                        "bus2": {"name": "bus2", "v_nom": 20},
                        "bus3": {"name": "bus3", "v_nom": 20}},
              "generators": {"gen1": {"bus": "bus1",
                                      "control": "PQ",
                                      "name": "gen1",
                                      "p_set": 100}},
              "lines": {"line1": {"buses": ["bus1", "bus2"],
                                  "name": "line1",
                                  "r": 0.01,
                                  "x": 0.1},
                        "line2": {"buses": ["bus2", "bus3"],
                                  "name": "line2",
                                  "r": 0.01,
                                  "x": 0.1},
                        "line3": {"buses": ["bus3", "bus1"],
                                  "name": "line3",
                                  "r": 0.01,
                                  "x": 0.1}},
              "loads": {"load1": {"bus": "bus2", "name": "load1", "p_set": 100}}}

# so far: components are always children of buses

elements = {}

scenario = {'type': 'scenario', 'name': 'pypsa-test', 'model': 'pypsa'}
tags = [oms.Tag(k,v) for k,v in scenario.items()]
scenario_element = oms.Element(user=user, tags=tags)
elements[scenario['name']] = scenario_element

for _, bus in json_input['buses'].items():
    tags = [oms.Tag(k,v) for k,v in bus.items()]
    tags.append(oms.Tag('type', 'bus'))
    element = oms.Element(user=user, tags=tags)
    element.parents = [scenario_element]
    elements[bus['name']] = element

for _, gen in json_input['generators'].items():
    tags = [oms.Tag(k,v) for k,v in gen.items()]
    tags.append(oms.Tag('type', 'generator'))
    element = oms.Element(user=user, tags=tags)
    element.parents = [scenario_element]
    element.successors = [elements[gen['bus']]]
    elements[gen['name']] = element

for _, load in json_input['loads'].items():
    tags = [oms.Tag(k,v) for k,v in load.items()]
    tags.append(oms.Tag('type', 'load'))
    element = oms.Element(user=user, tags=tags)
    element.parents = [scenario_element]
    element.predecessors = [elements[load['bus']]]
    elements[load['name']] = element

for _, line in json_input['lines'].items():
    tags = [oms.Tag(k,v) for k,v in line.items()]
    tags.append(oms.Tag('type', 'line'))
    element = oms.Element(user=user, tags=tags)
    element.parents = [scenario_element]
    element.predecessors = [elements[line['buses'][0]]] + [elements[line['buses'][1]]]
    element.successors = [elements[line['buses'][0]]] + [elements[line['buses'][1]]]
    elements[line['name']] = element

for _, element in elements.items():
    oms.DB.session.add(element)

oms.DB.session.commit()
