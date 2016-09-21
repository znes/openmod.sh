# Contains the simulation code

import time

from sqlalchemy.orm import sessionmaker
#import matplotlib.pyplot as plt, mpld3
import pandas as pd

# solph imports
from oemof.solph import (Sink, Source, LinearTransformer, Storage, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS)
import oemof.db as db
import oemof.outputlib as output
# Here you would now import the `oemof` modules and proceed to customize the
# `simulate` function to generate objects and start the simulation.

from openmod.sh.schemas import osm


def simulate(**kwargs):
    # This is how you get a scenario object from the database.
    # Since the iD editor prefixes element ids with their type ('r' for
    # relation, 'w' for way and 'n' for node), we have to strip a leading
    # character from the scenario id string before converting it to int.
    # This is what the [1:] is for.

    engine = db.engine('openMod.sh R/W')

    Session = sessionmaker(bind=engine)
    session = Session()

    scenario = session.query(osm.Relation).filter_by(
            id = int(kwargs['scenario'][1:])).first()
            #id = 1).first()

    # Delete the scenario id from `kwargs` so that is doesn't show up in the
    # response later.
    del kwargs['scenario']

    # Now you can access the nodes, ways and relations this scenario contains
    # and build oemof objects from them. I'll only show you how to access the
    # contents here.
    # These are lists with Node, Way and Relation objects.
    # See the .schemas.osm module for the API.
    elements = scenario.elements
    nodes = [n for n in elements if isinstance(n, osm.Node)]
    ways = [w for w in elements if isinstance(w, osm.Way)]
    relations = [r for r in elements if isinstance(r, osm.Relation)]

    #########################################################################
    # OEMOF SOLPH
    #########################################################################
    # We need a datetimeindex for the optimization problem / energysystem
    datetimeindex = pd.date_range(scenario.tags.get('year', 2016),
                                  periods=4, freq='H')

    energy_system = EnergySystem(groupings=GROUPINGS, time_idx=datetimeindex)

    ## CREATE NODES FROM RELATIONS OF TYPE "HUB ASSIGNMENT"
    buses = {}
    for r in relations:
        if r.tags.get('type') is not None:
            if r.tags['type'] == 'hub_relation':
                 name = r.tags.get('name')
                 buses[name] = Bus(label=str(name))
                 buses[name].energy_sector = r.tags['energy_sector']
        else:
            raise ValueError('Missing tag type of component with name {0}.'.format(r.tags['name']))

    ## GLOBAL FUEL BUSES FOR TRANSFORMER INPUTS (THAT ARE NOT IN RELATIONS)
    global_buses = {n.tags['fuel_type']:Bus(label=n.tags['fuel_type'],
                                            balanced=False)
                    for n in nodes
                    if n.tags.get('oemof_class') == 'linear_transformer'}

    ## Create Nodes (added automatically to energysystem)
    for n in nodes:
        # GET RELATIONS 'HUB ASSIGNMENT' FOR NODE
        node_bus = [r.tags['name'] for r in n.referencing_relations
                    if r.tags['name'] in list(buses.keys())]
        # CREATE SINK OBJECTS

        if n.tags.get('oemof_class') == 'sink':
            Sink(label=n.tags['name'],
                 inputs={buses[node_bus[0]]:
                     Flow(nominal_value=float(n.tags['energy_amount']),
                          actual_value=n.timeseries['timeseries'],
                          fixed=True)})
        # CREATE SOURCE OBJECTS
        if n.tags.get('oemof_class') == 'source':
            Source(label=n.tags['name'],
                   outputs={buses[node_bus[0]]:
                       Flow(nominal_value=float(n.tags['installed_power']),
                            actual_value=n.timeseries['timeseries'],
                            fixed=True)})
        # CREATE TRANSFORMER OBJECTS
        if n.tags.get('oemof_class') == 'linear_transformer':
            if n.tags.get('type') == 'flexible_generator':
                # CREATE LINEAR TRANSFORMER
                ins =  global_buses[n.tags['fuel_type']]
                outs = buses[node_bus[0]]
                LinearTransformer(label=n.tags['name'],
                                  inputs={ins: Flow(variable_costs=float(n.tags.get('variable_costs', 0)))},
                                  outputs={outs: Flow(nominal_value=float(n.tags['installed_power']))},
                conversion_factors={outs:float(n.tags['efficiency'])})
            if n.tags.get('type') == 'combined_flexible_generator':
                # CREATE COMBINED HEAT AND POWER AS LINEAR TRANSFORMER
                ins =  global_buses[n.tags['fuel_type']]
                heat_out = [buses[k] for k in node_bus
                            if buses[k].energy_sector == 'heat'][0]
                power_out = [buses[k] for k in node_bus
                             if buses[k].energy_sector == 'electricity'][0]
                LinearTransformer(label=n.tags['name'],
                                  inputs={ins: Flow(variable_costs=float(n.tags.get('variable_costs', 0)))},
                                  outputs={power_out: Flow(nominal_value=float(n.tags['installed_power'])),
                                           heat_out: Flow()},
                conversion_factors={heat_out:float(n.tags['thermal_efficiency']),
                                    power_out:float(n.tags['electrical_efficiency'])})

        if n.tags.get('oemof_class') == 'storage':
            # CRAETE STORAGE OBJECTS
            # Oemof solph does not provide direct way to set power in/out of
            # storage hence, we need to caculate the needed ratios upfront
            nicr = float(n.tags['installed_power']) / float(n.tags['installed_energy'])
            nocr = float(n.tags['installed_power']) / float(n.tags['installed_energy'])
            Storage(label=n.tags['name'],
                    inputs={buses[node_bus[0]]:Flow()},
                    outputs={buses[node_bus[0]]:Flow()},
                    nominal_capacity=float(n.tags['installed_energy']),
                    nominal_input_capacity_ratio=nicr,
                    nominal_output_capacity_ration=nocr)
    for w in ways:
        way_bus = [r.tags['name'] for r in w.referencing_relations
                    if r.tags['name'] in list(buses.keys())]
        if w.tags.get('oemof_class') == 'linear_transformer':
            # CREATE TWO TRANSFORMER OBJECTS WITH DIFFERENT DIRECTIONS IN/OUTS
            if w.tags.get('type') == 'transmission':
                # transmission lines are modelled as two transformers with
                # the same technical parameters
                ins = buses[way_bus[0]]
                outs = buses[way_bus[1]]
                LinearTransformer(label=w.tags['name']+'_1',
                                  inputs={outs: Flow()},
                                  outputs={ins: Flow(nominal_value=float(w.tags['installed_power']))},
                conversion_factors={ins:float(w.tags['efficiency'])})
                LinearTransformer(label=w.tags['name']+'_2',
                                  inputs={ins: Flow()},
                                  outputs={outs: Flow(nominal_value=float(w.tags['installed_power']))},
                conversion_factors={outs:float(w.tags['efficiency'])})


    ## Create optimization model, solve it, wrtie back results
    om = OperationalModel(es=energy_system)
    if 'solver' in kwargs.keys():
        solver = kwargs['solver']
    else:
        solver = 'glpk'
    om.solve(solver=solver,
             solve_kwargs={'tee': True, 'keepfiles': False})
    om.results()

    # figure to html with mpld3 package ???
    #esplot = output.DataFramePlot(energy_system=energy_system)
    #unstack = esplot.slice_unstacked(bus_label=power_out.label,
    #                                 type="to_bus",
    #                                 date_from='2012-01-01 00:00:00',
    #                                 date_to='2012-01-01 23:00:00')
    #string = unstack.to_html()

    #########################################################################
    # END OF OEMOF SOLPH
    #########################################################################
    # Generate a response so that we see something is actually happening.
    lengths = [len(l) for l in [nodes, ways, relations]]
    response = (
            "Done running scenario: '{scenario}'.<br />" +
            "Contents:<br />" +
            "  {0[0]:>5} nodes<br />" +
            "  {0[1]:>5} ways<br />" +
            "  {0[2]:>5} relations<br />" +
            "Parameters:<br />  " +
            "<br />  ".join(["{}: {}".format(*x) for x in kwargs.items()])
            ).format(lengths,
                     scenario=scenario.tags['name'])

    # Now sleep for 5 minutes to pretend we are doing something.
    time.sleep(0.5)
    return response

