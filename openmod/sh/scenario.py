# Contains the simulation code

import time

from sqlalchemy.orm import sessionmaker
import matplotlib.pyplot as plt, mpld3
import pandas as pd
import numpy as np
# solph imports
from oemof.solph import (Sink, Source, LinearTransformer, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS)
import oemof.db as db
import oemof.outputlib as output
# Here you would now import the `oemof` modules and proceed to customize the
# `simulate` function to generate objects and start the simulation.

from .schemas import osm


def simulate(**kwargs):
    # This is how you get a scenario object from the database.
    # Since the iD editor prefixes element ids with their type ('r' for
    # relation, 'w' for way and 'n' for node), we have to strip a leading
    # character from the scenario id string before converting it to int.
    # This is what the [1:] is for.

    engine = db.engine('openMod.sh R/W')

    Session = sessionmaker(bind=engine)
    session = Session()

    scenario = session.query(osm.Relation).get(int(kwargs['scenario'][1:]))

    scenario_tags = {}
    for t in scenario.tags:
        scenario_tags.update({t.key: t.value})

    # Delete the scenario id from `kwargs` so that is doesn't show up in the
    # response later.
    del kwargs['scenario']

    # Now you can access the nodes, ways and relations this scenario contains
    # and build oemof objects from them. I'll only show you how to access the
    # contents here.
    # These are lists with Node, Way and Relation objects.
    # See the .schemas.osm module for the API.
    nodes = scenario.referenced_nodes
    ways = scenario.referenced_ways
    relations = scenario.referenced # Make sure to traverse these recursively.


    #########################################################################
    # OEMOF SOLPH
    #########################################################################
    # We need a datetimeindex for the optimization problem / energysystem
    # TODO: Replace date and period with arguments from scenario
    datetimeindex = pd.date_range(scenario_tags.get('year', 2016),
                                  periods=24, freq='H')

    energy_system = EnergySystem(groupings=GROUPINGS, time_idx=datetimeindex)

    ## Create Nodes (added automatically to energysystem)
    bel = Bus(label='bel')
    bgas = Bus(label='bgas', balanced=False)

    # sources from ID input """(i,n) in enumerate(nodes)"""
    for n in nodes:
        tags = {}
        for t in n.node.tags:
            tags.update({t.key: t.value})
        if tags.get('type') == 'source':
            Source(label=tags['name'],
                   outputs={bel:Flow(actual_value=np.random.rand(24),
                            nominal_value=float(tags['power']),
                            fixed=True)})
        if tags.get('type') == 'powerplant':
            LinearTransformer(label=tags['name'],
                              inputs={bgas: Flow()},
                              outputs={bel: Flow(nominal_value=float(tags['power']),
                              variable_costs=40)},
                              conversion_factors={bel: 0.50})
        if tags.get('type') == 'demand':
            Sink(label=tags['name'],
                 inputs={bel: Flow(nominal_value=float(tags['amount']),
                         actual_value=np.random.rand(24),
                         fixed=True)})

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
    esplot = output.DataFramePlot(energy_system=energy_system)
    unstack = esplot.slice_unstacked(bus_label="bel", type="to_bus",
                                    date_from='2012-01-01 00:00:00',
                                    date_to='2012-01-01 23:00:00')
    string = unstack.to_html()

#    fig = plt.figure()
#    esplot.plot(title="January 2012", stacked=True, width=1, lw=0.1,
#                kind='bar')
#    string = mpld3.fig_to_html(fig)

    #########################################################################
    # END OF OEMOF SOLPH
    #########################################################################
    # Generate a response so that we see something is actually happening.
    lengths = [len(l) for l in [nodes, ways, relations]]
    response = string + (
            "Done running scenario: '{scenario}'.<br />" +
            "Contents:<br />" +
            "  {0[0]:>5} nodes<br />" +
            "  {0[1]:>5} ways<br />" +
            "  {0[2]:>5} relations<br />" +
            "Parameters:<br />  " +
            "<br />  ".join(["{}: {}".format(*x) for x in kwargs.items()])
            ).format(lengths,
                     scenario={t.key: t.value for t in scenario.tags}['name'])
    # Now sleep for 5 minutes to pretend we are doing something.
    time.sleep(0.5)
    return response

