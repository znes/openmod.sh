# -*- coding: utf-8 -*-
import multiprocessing as mp
import os
import signal
import sys
import traceback

import pandas as pd
import json
import logging

from oemof.tools import logger
from oemof.network import Node
from oemof.solph import (Sink, Source, LinearTransformer, Storage, Bus, Flow,
                         VariableFractionTransformer, OperationalModel,
                         EnergySystem, GROUPINGS)

from openmod.sh.api import results_to_db

import oemof.outputlib as output

logger.define_logging(log_version=False)

##### Utility Functions #######################################################
def _float(obj, attr):
    """ Help function to convert string input from database string of tag[key]
    to float with explicit value error message and default setting of
    attributes.
    """

    if obj['tags'].get(attr)  == 'null':
        if attr == 'max_fullloadhours':
            obj['tags'][attr] = None
        else:
            obj['tags'][attr] = 0

    if obj['tags'].get(attr) == '+inf':
        obj['tags'][attr] = None

    defaults = {'installed_energy': 0,
                'installed_power': None,
                'amount': None,
                'variable_cost': 0,
                'efficiency' : 1,
                'min_amount':0,
                'max_amount': None,
                'max_fullloadhours': None,
                'min_fullloadhours': 0}


    try:
        if obj['tags'].get(attr) is None:
            logging.info("Setting default value of {0} for attribute {1} of" \
                " element {2}".format(defaults.get(attr), attr, obj['name']))
            return defaults.get(attr)
        else:
            return float(obj['tags'][attr])
    except:
        raise ValueError("Your attribute {0} of object {1} is supposed to be" \
         " a number. Did you specifiy it and use `.` as decimal sign?".format(attr,
                                                            obj.get('name')))

# mcbeth specific grouping function for energy system grouping argument
def sector_grouping(node):
    if isinstance(node, Bus) and hasattr(node, 'sector'):
      if isinstance(node, Bus) and node.sector == 'electricity':
          return 'electricity'
      if isinstance(node, Bus) and node.sector == 'heat':
          return 'heat'

# warnings, infos etc
def missing_hub_warning(n, hub):
    logging.warning("{0} (hub) missing of element {1}. Skipping element..." \
                    "Simulation will most likely fail.".format(hub, n['name']))

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
                hours=int(scenario['tags'].get('end_timestep', 3))-1)
    timeindex = pd.date_range(start=start, end=end, freq='H')

    # create energy sytem and disable automatic registry of node objects
    es = EnergySystem(groupings=GROUPINGS,
                      timeindex=timeindex)
    Node.registry = None

    es.scenario_description = scenario['tags'].get('scenario_description',
                                                   'No description provided.')
    es.scenario_name = scenario['name']

    return es


def populate_energy_system(es, node_data):
    """Populates energy systems with oemof.solph - nodes created from the
       elements.
    Parameters
    ----------
    es : oemof.solph.EnergySystem
    node_data : dict
       Elements from
    """

    # create solph buses
    logging.info("Creating hubs...")
    # create solph components
    hubs = {}
    for n in node_data:
        if n['type'] == 'hub':
            b = Bus(label=n['name'], geo=n.get('geom'))
            b.type = n['type']
            # add all tags as attributes to hub/bus
            for k,v in n['tags'].items():
                setattr(b, k, v)
            es.add(b)
            hubs[n['name']] = b

    # create solph components
    commodities = {}
    for n in node_data:
        # create source objects for volatile generators
        if n['type'] == "commodity":
            ss = es.groups.get(n['successors'][0])
            if not ss:
                missing_hub_warning(n, 'Successor')
            else:
                max_amount = _float(n, 'max_amount')
                min_amount = _float(n, 'min_amount')

                # assign the lager value of min/max amount to nominal value
                nv = max_amount

                if nv is None:
                    summed_max = None
                    summed_min = None
                else:
                    summed_max = max_amount / nv
                    summed_min = min_amount / nv
                # if summe_min i.e min_amount is 0, we do not want to build the
                # constraint, therefore summed_min is set to None
                if summed_min == 0:
                    summed_min = None

                # summe_max is set to 1, to make summed max working!!!!!!!!
                # contraints is: flow <= nominal_value * summed_max
                obj = Source(label=n['name'],
                             outputs={ss:
                                 Flow(nominal_value=nv,
                                      variable_costs=_float(n, 'variable_cost'),
                                      summed_max=summed_max,
                                      summed_min=summed_min)})
                obj.type = n['type']
                obj.emission_factor = _float(n, 'emission_factor')

                es.add(obj)
                commodities[n['name']] = obj

    for n in node_data:
        logging.info("Creating component {0}...".format(n['name']))

        if n['type'] in ['area_factor', 'unit']:
            pass

        # create oemof solph sinks for sink elements  (e.g. co2-sink, import-slack)
        if n['type'] == 'sink':
            ps = es.groups.get(n['predecessors'][0])
            if not ps:
                missing_hub_warning(n, 'Predecessor')
            else:
                obj = Sink(label=n['name'],
                           inputs={ps:
                              Flow(nominal_value=_float(n, 'installed_power'),
                                   variable_costs=_float(n, 'variable_cost'))})
                es.add(obj)
                obj.type = n['type']

        # create oemof solph source for sink elements  (e.g. export-slack)
        if n['type'] == 'source':
            ss = es.groups.get(n['successors'][0])
            if not ss:
                missing_hub_warning(n, 'Successor')
            else:
                obj = Source(label=n['name'],
                             outputs={ss:
                              Flow(nominal_value=_float(n, 'installed_power'),
                                   variable_costs=_float(n, 'variable_cost'))})
                es.add(obj)
                obj.type = n['type']

        # create oemof solph source object for volatile generator elements
        if n['type'] == 'volatile_generator':
            ss = es.groups[n['successors'][0]]
            if not ss:
                missing_hub_warning(n, 'Successor')
            else:
                obj = Source(label=n['name'],
                             outputs={ss:
                                 Flow(nominal_value=_float(n, 'installed_power'),
                                      actual_value=n['sequences']['generator_profile'],
                                      variable_cost=_float(n, 'variable_cost'),
                                      fixed=True)})
                es.add(obj)
                obj.type = n['type']

        # cretae oemof solph sink object for demand elements
        if n['type'] == 'demand':
            ps = es.groups[n['predecessors'][0]]
            if not ps:
                missing_hub_warning(n, 'Predecessor')
            else:
                # depending on the values inside the scenario def. -> calc
                # oemof.solph input values
                amount =_float(n, 'amount')
                abs_profile = [i* amount for i in  n['sequences']['load_profile']]
                nv = max(abs_profile)
                if nv != 0:
                    av = [i/nv for i in abs_profile]
                else:
                    av = [i*0 for i in abs_profile]
                    logging.warning('Nominal value of {} is 0.'.format(n['name']))

                fixed = True

                obj = Sink(label=n['name'],
                           inputs={ps:
                                 Flow(nominal_value=nv,
                                      actual_value=av,
                                      variable_costs=_float(n, 'variable_cost'),
                                      fixed=fixed)})
                es.add(obj)
                obj.type = n['type']

        # create variable fraction transformers for extraction turbines
        if n['type'] == 'extraction_turbine':
            ss = {es.groups[i].sector: es.groups[i] for i in n['successors']
                  if i in [n.label for n in es.nodes]}
            ps = es.groups[n['predecessors'][0]]

            conversion_factors = {
                ss['heat']: _float(n, 'thermal_efficiency'),
                ss['electricity']: _float(n, 'electrical_efficiency')}

            if _float(n, 'min_fullloadhours') == 0:
                summed_min = None
            else:
                summed_min = _float(n, 'min_fullloadhours')

            outputs={
                ss['heat']: Flow(),
                ss['electricity']: Flow(
                    nominal_value=_float(n, 'installed_power'),
                    variable_costs=_float(n, 'variable_cost'),
                    summed_max= _float(n, 'max_fullloadhours'),
                    summed_min=summed_min)}

            if ss.get('co2'):
                # select input of predecessor for transformer (commodity source)
                conversion_factors[ss['co2']] = list(
                    es.groups[n['predecessors'][0]].inputs.keys())[0].emission_factor
                outputs[ss['co2']] = Flow()

            obj = VariableFractionTransformer(
                            label=n['name'],
                            outputs=outputs,
                            inputs={ps:
                                Flow()},
                            conversion_factors=conversion_factors,
                            conversion_factor_single_flow={
                                ss['electricity']: _float(n, 'condensing_efficiency')})
            es.add(obj)
            obj.type = n['type']

        # create linear transformers for flexible generators
        if n['type'] == 'flexible_generator':
            ss = {es.groups[i].sector: es.groups[i] for i in n['successors']
                  if i in [n.label for n in es.nodes]}
            ps = es.groups[n['predecessors'][0]]

            # if min fullload hours is 0, we do not want to build the
            # constraint, therefore summed_min is set to None
            if _float(n, 'min_fullloadhours') == 0:
                summed_min = None
            else:
                summed_min = _float(n, 'min_fullloadhours')
            # select bus
            sector = [v for (k,v) in ss.items() if k !='co2'][0]
            conversion_factors = {
                sector: _float(n, 'efficiency')}
            outputs={
                sector: Flow(nominal_value=_float(n, 'installed_power'),
                             summed_max= _float(n, 'max_fullloadhours'),
                             variable_costs=_float(n, 'variable_cost'),
                             summed_min=summed_min)}

            # if co2-successor exist, add conversion factors and Flow
            if ss.get('co2'):
                # select input of predecessor for transformer (commodity source)
                conversion_factors[ss['co2']] = list(
                    es.groups[n['predecessors'][0]].inputs.keys())[0].emission_factor
                outputs[ss['co2']] = Flow()

            obj = LinearTransformer(
                label=n['name'],
                outputs=outputs,
                inputs={ps:
                    Flow()},
                conversion_factors=conversion_factors)
            es.add(obj)
            obj.type = n['type']

        # create linear transformers for combined flexible generators
        if n['type'] == 'combined_flexible_generator':
            ss = {es.groups[i].sector: es.groups[i] for i in n['successors']
                  if i in [n.label for n in es.nodes]}
            ps = es.groups[n['predecessors'][0]]

            conversion_factors = {
                ss['heat']: _float(n, 'thermal_efficiency'),
                ss['electricity']: _float(n, 'electrical_efficiency')}

            if _float(n, 'min_fullloadhours') == 0:
                summed_min = None
            else:
                summed_min = _float(n, 'min_fullloadhours')

            outputs={
                ss['heat']: Flow(),
                ss['electricity']: Flow(
                    nominal_value=_float(n, 'installed_power'),
                    variable_costs=_float(n, 'variable_cost'),
                    summed_max= _float(n, 'max_fullloadhours'),
                    summed_min=summed_min)}

            if ss.get('co2'):
                # select input of predecessor for transformer (commodity source)
                conversion_factors[ss['co2']] = list(
                    es.groups[n['predecessors'][0]].inputs.keys())[0].emission_factor
                outputs[ss['co2']] = Flow()

            obj = LinearTransformer(
                label=n['name'],
                outputs=outputs,
                inputs={ps:
                    Flow()},
                conversion_factors = conversion_factors)
            es.add(obj)
            obj.type = n['type']

        # create solph storage objects for storage elements
        if n['type'] == 'storage':
            # Oemof solph does not provide direct way to set power in/out of
            # storage hence, we need to caculate the needed ratios upfront
            try:
                nicr = (_float(n,'installed_power') / _float(n,'installed_energy'))
                nocr = (_float(n,'installed_power') / _float(n,'installed_energy'))
            except:
                ZeroDivisionError
                logging.warning('Installed energy of strorage {} is zero.' \
                      'Setting default values for nicr/norc'.format(n['name']))
                nicr = 1/6
                nocr = 1/6

            ps = es.groups[n['predecessors'][0]]
            ss = es.groups[n['successors'][0]]

            obj = Storage(label=n['name'],
                        inputs={ps:
                            Flow(variable_costs=_float(n, 'variable_cost'))},
                        outputs={ss:
                            Flow(variable_costs=_float(n, 'variable_cost'))},
                        nominal_capacity=_float(n,'installed_energy'),
                        nominal_input_capacity_ratio=nicr,
                        nominal_output_capacity_ration=nocr)
            es.add(obj)
            obj.type = n['type']

        # create linear transformer(s) for transmission elements
        if n['type'] == 'transmission':
            # create 2 LinearTransformers for a transmission element
            ss = [es.groups[s] for s in n['successors']][0]
            ps = [es.groups[s] for s in n['predecessors']][0]
            obj = LinearTransformer(
                label=n['name'],
                outputs={ss:
                    Flow(nominal_value=_float(n, 'installed_power'))},
                inputs={ps:
                    Flow()},
                conversion_factors={ss: _float(n, 'efficiency')})
            es.add(obj)
            obj.type = n['type']

        for k,v in n['tags'].items():
            if k == 'slack':
                setattr(obj, k, v)




    return es

def create_model(es):
    """
    """
    logging.info("Creating oemof.solph.OperationalModel instance for" \
        "scenario {}...".format(es.scenario_name))
    es.model = OperationalModel(es=es)
    # TODO: Add lp file writing in openmod debug mode only?
    if True:
        es.model.write(es.scenario_name+'.lp',
                       io_options={'symbolic_solver_labels':True})

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
    logging.info('Update values in OperationalModel()...')
    for t in range(len(es.timeindex)):
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

    es.model.preprocess()

    return es

def compute_results(es):
    """
    """

    if not hasattr(es, "model"):
        raise ValueError("Energysystem has no model to compute results.")

    logging.info("Computing results...")

    solver = 'cbc'

    es.model.solve(solver=solver,
                   solve_kwargs={'tee': True, 'keepfiles': False})

    es.model.results()

    es.rdf = output.DataFramePlot(energy_system=es)

    return es

class JobStoppedException(Exception):
    pass

def stop_worker(signal_number, stack_frame, message="Stopped by user."):
    raise(JobStoppedException(message))

def wrapped_simulation(scenario, connection):
    """

    Parameters
    ----------

    scenario : dict
        Complete scenario definition including all elements.
    connection : `multiprocessing.Connection`
        A connection object with which the child process can communicate with
        the parent.

    """
    signal.signal(signal.SIGINT, stop_worker)
    connection.send(mp.current_process().pid)
    # If theres anything available on our end of the pipe, that means our
    # parent wants us to stop immediately.
    if connection.poll():
      return "Cancelled.\n<br/>Terminated without any action."
    try:
        # create an energy system object
        es = create_energy_system(scenario)

        # add the nodes to the energy system object
        es = populate_energy_system(es=es, node_data=scenario['children'])

        # create the optimization model
        es = create_model(es)

        # run the model
        es = compute_results(es)

        results_to_db(scenario['name'], es.results)

        result = "Success."

    except JobStoppedException as e:
        result = "Stopped.\n<br/>"
        if sys.version_info >= (3, 5):
            result += '<br/>'.join(traceback
                .TracebackException
                .from_exception(e)
                .format())
        else:
            result += '<br/>'.join(traceback.format_exc())
    except Exception as e:
        result = "Failure.\n<br/>"
        if sys.version_info >= (3, 5):
            result += '<br/>'.join(traceback
                .TracebackException
                .from_exception(e)
                .format())
        else:
            result += '<br/>'.join(traceback.format_exc())
    finally:
        connection.close()

    return result


if __name__ == "__main__":

    scenario = json.load(open('../../data/scenarios/kiel-2014-explicit-geoms-sequences.json'))

    es = create_energy_system(scenario)
    es = populate_energy_system(es=es, node_data=scenario['children'])
    es = create_model(es)
    es = compute_results(es)

#    import graphviz as gv
#    import oemof.network as ntwk
#    G = gv.Digraph(format='svg', engine='dot')
#    for n in es.nodes:
#        if isinstance(n, ntwk.Component):
#            color='black'
#            shape = 'box'
#        else:
#            color = 'blue'
#            shape = None
#        if 'heat' in n.label:
#            color = 'red'
#        if 'GL' in n.label:
#            color='brown'
#        if '_el' in n.label:
#            color='blue'
#        G.node(n.label, color=color, shape=shape)
#    # add edges
#    for s,t in es.model.flows:
#        G.edge(s.label, t.label)
#    G.render('G')
