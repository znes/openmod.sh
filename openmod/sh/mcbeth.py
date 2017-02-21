# -*- coding: utf-8 -*-
import pandas as pd
import json

from oemof.network import Node
from oemof.solph import (Sink, Source, LinearTransformer, Storage, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS)
import oemof.outputlib as output

# just for testing purposes
scenario = json.load(open('../../data/scenarios/test-kiel/kiel-statusquo-explicit.json'))

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
                hours=int(scenario['tags'].get('end_timestep', 8760))-1)
    timeindex = pd.date_range(start=start, end=end, freq='H')

    # create energy sytem and disable automatic registry of node objects
    es = EnergySystem(groupings=GROUPINGS, timeindex=timeindex)
    Node.registry = None

    es.scenario_description = scenario['tags'].get('scenario_description',
                                                   'No description provided.')
    return es

es = create_energy_system(scenario)

nodes = scenario['children']

#def populate_energy_system(nodes=scenario['children']):

# create solph buses
for n in nodes:
    if n['type'] == 'hub':
        b = Bus(label=n['name'], geo=n.get('geom'))
        # add all tags as attributes to hub/bus
        for k,v in n['tags'].items():
            setattr(b, k, v)
        es.add(b)

# create solph components
for n in nodes:
    # create source objects for volatile generators
#    if n['type'] == 'volatile_generator':
#        ss = es.groups[n['successors'][0]]
#        obj = Source(label=n['name'],
#                     outputs={ss:
#                         Flow(nominal_value=float(n['tags']['installed_power']),
#                              actual_value=n['sequences']['profile'])})
#        es.add(obj)
#
#    # create sink objects
#    if n['type'] == 'demand':
#        ps = es.groups[n['predecessors'][0]]
#        # depending on the values inside the scenario def. -> calc
#        # oemof.solph input values
#        abs_profile = [i*float(n['tags']['amount'])
#                       for i in  n['sequences']['load_profile']]
#        av = [max(abs_profile) / i for i in abs_profile]
#        nv = max(abs_profile)
#        obj = Sink(label=n['name'],
#                   inputs={ps:
#                         Flow(nominal_value=nv,
#                              actual_value=av)})

    # create linear transformers for flexible generators
    if n['type'] == 'flexible_generator':
        ss = es.groups[n['successors'][0]]
        ps = es.groups[n['predecessors'][0]]

        obj = LinearTransformer(
            label=n['name'],
            outputs={ss:
                Flow(nominal_value=float(n['tags']['installed_power']))},
            inputs={ps:
                Flow()},
            conversion_factors={ss: float(n['tags']['efficiency'])})
        es.add(obj)

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
        es.add(obj)

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
        es.add(obj)

    # create linear transformer(s) for transmission elements
    if n['type'] == 'transmission':
        pass


def compute_results(energysystem):
    """
    """
    # create solph model
    om = OperationalModel(es=energysystem)

    solver =  None
    if solver is None:
        solver = 'glpk'

    om.solve(solver=solver,
             solve_kwargs={'tee': True, 'keepfiles': False})

    om.results()

    return om


def simulate(scenario):
    """
    """
    es = create_energy_system(scenario)

    es = populate_energy_system(es)

    om = compute_results(es)

    return es, om

