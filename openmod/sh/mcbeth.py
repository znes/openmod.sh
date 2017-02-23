# -*- coding: utf-8 -*-
import pandas as pd
import json
import time

from oemof.network import Node
from oemof.solph import (Sink, Source, LinearTransformer, Storage, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS)
import oemof.outputlib as output

first = time.time()
# just for testing purposes
scenario = json.load(open('../../data/scenarios/kiel/kiel-statusquo-explicit-geoms-sequences.json'))

##### Utility Functions #######################################################
def _float(obj, attr):
    """ Help function to convert string input from database string of tag[key]
    to float with explicit value error message and default setting of
    attributes.
    """
    defaults = {'variable_costs': 0,
                'efficiency' : 1}

    default = defaults.get(attr)
    try:
        return float(obj['tags'].get(attr, default))
    except:
        raise ValueError('Your attribute {0} of object {1} is supposed to be\
         a number. Did you specifiy it and use `.` as decimal sign?'.format(attr,
                                                            obj.get('name')))

# mcbeth specific grouping function for energy system grouping argument
def sector_grouping(node):
    if isinstance(node, Bus) and hasattr(node, 'sector'):
      if isinstance(node, Bus) and node.sector == 'electricity':
          return 'electricity'
      if isinstance(node, Bus) and node.sector == 'heat':
          return 'heat'

#####fucntion for oemof workflow ##############################################

def create_energy_system(scenario):
    """Creates oemof energy system from JSON scenario definition

    Parameters
    ----------
    scenario: dict
        Dictionary representing the scenario element containing the scenario
        information and the children

    Returns
    -------
    es : oemof.solph.EnergySystem
        EnergySystem object with timeindex and additional scenario information
    """

    first = pd.to_datetime(scenario['tags'].get('scenario_year' + '0101',
                                                '2016'))
    start = first + pd.DateOffset(
                hours=int(scenario['tags'].get('start_timestep', 1))-1)
    end = first + pd.DateOffset(
                hours=int(scenario['tags'].get('nd_timestep', 4))-1)
    timeindex = pd.date_range(start=start, end=end, freq='H')

    # create energy sytem and disable automatic registry of node objects
    es = EnergySystem(groupings=GROUPINGS, timeindex=timeindex)
    #Node.registry = None

    es.scenario_description = scenario['tags'].get('scenario_description',
                                                   'No description provided.')
    return es

es = create_energy_system(scenario)

nodes = scenario['children']

#def populate_energy_system(es, nodes=scenario['children']):
#    """Populates energy systems with oemof.solph - nodes created from the
#       elements.
#    Parameters
#    ----------
#    es : oemof.solph.EnergySystem
#    nodes : dict
#       Elements from
#    """


# create solph buses
for n in nodes:
    if n['type'] == 'hub':
        b = Bus(label=n['name'], geo=n.get('geom'))
        # add all tags as attributes to hub/bus
        for k,v in n['tags'].items():
            setattr(b, k, v)
        #es.add(b)

# create solph components
for n in nodes:
    # create source objects for volatile generators
    if n['type'] == "commodity" and n['successors']:
        ss = es.groups.get(n['successors'][0])
        if ss:
            obj = Source(label=n['name'],
                         outputs={ss:
                             Flow(variable_costs=_float(n, 'variable_cost'))})
            obj.type = n['type']
        #es.add(obj)

    if n['type'] == 'volatile_generator':
        ss = es.groups[n['successors'][0]]

        obj = Source(label=n['name'],
                     outputs={ss:
                         Flow(nominal_value=float(n['tags']['installed_power']),
                              actual_value=n['sequences']['generator_profile'],
                              fixed=True)})
        obj.fuel_type = n['tags'].get('fuel_type')
        obj.type = n['type']
        #es.add(obj)

    # create sink objects
    if n['type'] == 'demand':
        ps = es.groups[n['predecessors'][0]]
        # depending on the values inside the scenario def. -> calc
        # oemof.solph input values
        abs_profile = [i*float(n['tags']['amount'])
                       for i in  n['sequences']['load_profile']]
        av = [i/max(abs_profile) for i in abs_profile]
        nv = max(abs_profile)
        obj = Sink(label=n['name'],
                   inputs={ps:
                         Flow(nominal_value=nv,
                              actual_value=av,
                              fixed=True)})
        #es.add(obj)

    # create linear transformers for flexible generators
    if n['type'] == 'flexible_generator':
        ss = es.groups[n['successors'][0]]
        ps = es.groups[n['predecessors'][0]]

        outflow = Flow(nominal_value=float(n['tags']['installed_power']),
                    variable_costs=_float(n, 'variable_costs'))
        # set additional outflow attributes

        for k,v in n['tags'].items():
            if k in vars(Flow()).keys():
                setattr(outflow, k, float(v))

        obj = LinearTransformer(
            label=n['name'],
            outputs={ss: outflow
                },
            inputs={ps:
                Flow()},
            conversion_factors={ss: float(n['tags']['efficiency'])})
        #es.add(obj)

    # create linear transformers for combined flexible generators
    if n['type'] == 'combined_flexible_generator':
        ss = {es.groups[i].sector: es.groups[i]
              for i in n['successors'] if i}
        ps = es.groups[n['predecessors'][0]]

        obj = LinearTransformer(
            label=n['name'],
            outputs={ss['heat']:
                Flow(),
                     ss['electricity']:
                Flow(nominval_value=float(n['tags']['installed_power']))},
            inputs={ps:
                Flow()},
            conversion_factors = {
                ss['heat']: float(n['tags']['thermal_efficiency']),
                ss['electricity']: float(n['tags']['electrical_efficiency'])})
        #es.add(obj)

    # create solph storage objects for storage elements
    if n['type'] == 'storage':
        # Oemof solph does not provide direct way to set power in/out of
        # storage hence, we need to caculate the needed ratios upfront
        nicr = (_float(n,'installed_power') / _float(n,'installed_energy'))
        nocr = (_float(n,'installed_power') / _float(n,'installed_energy'))

        ps = es.groups[n['predecessors'][0]]
        ss = es.groups[n['successors'][0]]

        obj = Storage(label=n['name'],
                    inputs={ps:
                        Flow(variable_costs=0)},
                    outputs={ss:
                        Flow(variable_costs=0)},
                    nominal_capacity=_float(n,'installed_energy'),
                    nominal_input_capacity_ratio=nicr,
                    nominal_output_capacity_ration=nocr)
        #es.add(obj)

    # create linear transformer(s) for transmission elements
    if n['type'] == 'transmission':
        # create 2 LinearTransformers for a transmission element
        ss = es.groups[n['successors'][0]]
        ps = es.groups[n['predecessors'][0]]

        obj1 = LinearTransformer(
            label=n['name']+'_1',
            outputs={ss:
                Flow(nominal_value=float(n['tags']['installed_power']))},
            inputs={ps:
                Flow()},
            conversion_factors={ss: float(n['tags']['efficiency'])})
        #es.add(obj1)

        obj2 = LinearTransformer(
            label=n['name']+'_2',
            outputs={ps:
                Flow(nominal_value=float(n['tags']['installed_power']))},
            inputs={ss:
                Flow()},
            conversion_factors={ps: float(n['tags']['efficiency'])})
        #es.add(obj2)

def create_model(es):
    """
    """

    es.model = OperationalModel(es=es)

    return es



def update_model(es, elements):
    """ Updates 'installed_power' of elements of type 'volatile_generator',
        'flexible_generator' and 'combined_flexible_generator'

    Parameters
    ----------
    es : oemof.solph.EnergySystem
        Energysystem object with instantiated OperationalModel (es.om)
    elements : list
        List with openmod API elements

    #TODO : Code should be runtime optimized...
    """

    for t in es.timeindex:
        for e in elements:
            if e['type'] == 'volatile_generator':
                # update flow in oemof model
                es.model.flows[
                     es.groups[e['name']],
                     es.groups[e['successors'][0]]].nominal_value = \
                         float(e['tags']['installed_power'])
                # update flow in pyomo model
                es.model.flow[
                    es.groups[e['name']],
                    es.groups[e['successors'][0]],t].value = \
                        (float(e['tags']['installed_power']) *
                            e['sequences']['generator_profile'][t])

            if e['type'] in ['flexible_generator',
                             'combined_flexible_generator']:
                ss = {es.groups[s].sector: es.groups[s]
                      for s in e['successors'] if s}
                es.model.flow[
                    es.groups[e['name']],
                    ss['electricity'], t].setub(
                        float(e['tags']['installed_power']))

    return es

def compute_results(es):
    """
    """

    if not hasattr(es, "model"):
        raise ValueError("Energysystem has no model to compute results.")

    solver = 'glpk'

    es.model.solve(solver=solver,
                   solve_kwargs={'tee': True, 'keepfiles': False})

    es.model.results()

    es.rdf = output.DataFramePlot(energy_system=es)

    return es


es = create_model(es)

es = compute_results(es)





if __name__ == "__main__":
    import graphviz as gv
    import oemof.network as ntwk
    G = gv.Digraph(format='svg', engine='dot')
    for n in es.nodes:
        if isinstance(n, ntwk.Component):
            color='black'
            shape = 'box'
        else:
            color = 'blue'
            shape = None
        if 'heat' in n.label:
            color = 'red'
        if 'GL' in n.label:
            color='brown'
        if '_el' in n.label:
            color='blue'
        G.node(n.label, color=color, shape=shape)
    # add edges
    for s,t in es.model.flows:
        G.edge(s.label, t.label)
    G.render('G')