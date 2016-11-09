# Contains the simulation code

import pdb
import os
from tempfile import mkstemp
from sqlalchemy.orm import sessionmaker
#import matplotlib.pyplot as plt, mpld3
import pandas as pd

# solph imports
from oemof.solph import (Sink, Source, LinearTransformer, Storage, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS)
import oemof.db as db
import oemof.outputlib as output
from bokeh.charts import Bar, output_file, show
from bokeh.embed import components as bokeh_components
# Here you would now import the `oemof` modules and proceed to customize the
# `simulate` function to generate objects and start the simulation.

from .schemas import osm

defaults = {'variable_costs': 0, 'efficiency' : 1}
def _float(obj, attr):
    """ Help function to convert string input from database string of tag[key]
    to float with explicit value error message and default setting of
    attributes.
    """

    default = defaults.get(attr)
    try:
        return float(obj.tags.get(attr, default))
    except:
        raise ValueError('Your attribute {0} of object {1} is supposed to be\
         a number. Did you specifiy it and use `.` as decimal sign?'.format(attr,
                                                            obj.tags.get('name')))

def simulate(folder, **kwargs):
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

    # emission factor (hardcoded for now....) t/MWh
    emission_factors = {'gas': 0.2, 'coal': 0.34, 'oil': 0.27, 'lignite': 0.4,
                        'waste': 0.3, 'biomass': 0, 'wind':0, 'solar':0}
    #########################################################################
    # OEMOF SOLPH
    #########################################################################
    # We need a datetimeindex for the optimization problem / energysystem
    datetimeindex = pd.date_range('1/1/'+scenario.tags.get('year', '2012'),
                                  periods=scenario.tags.get('hours', 4),
                                  freq='H')

    energy_system = EnergySystem(groupings=GROUPINGS,
                                 timeindex=datetimeindex)

    ## CREATE BUSES FROM RELATIONS OF TYPE "HUB RELATION"
    buses = {}
    for r in relations:
        if r.tags.get('type') is not None:
            if r.tags['type'] == 'hub_relation':
                 name = r.tags.get('name')
                 buses[name] = Bus(label=str(name))
                 buses[name].energy_sector = r.tags['energy_sector']
        else:
            raise ValueError('Missing tag type of component with ' +
                             'name {0}.'.format(r.tags['name']))

    ## GLOBAL FUEL BUSES FOR TRANSFORMER INPUTS (THAT ARE NOT IN RELATIONS)
    global_buses = {}
    for n in nodes:
        if n.tags.get('oemof_class') == 'linear_transformer':
            # Only create global bus if not already exist
            if global_buses.get(n.tags['fuel_type']) is None:
                global_buses[n.tags['fuel_type']] =  Bus(
                                    label=n.tags['fuel_type'], balanced=False)


    ## Create Nodes (added automatically to energysystem)
    for n in nodes:
        # GET RELATIONS 'HUB ASSIGNMENT' FOR NODE
        node_bus = [r.tags['name'] for r in n.referencing_relations
                    if r.tags['name'] in list(buses.keys())]
        # create the variable cost timeseries if specified, otherwise use
        # variable costs key from tags
        if n.tags.get('variable_costs', 0) == 'timeseries':
            variable_costs = n.timeseries.get('variable_costs')
            if variable_costs is None:
                raise ValueError('No timeseries `variable cost` found for ' +
                                 'node {0}.'.format(n.tags.get('name')))
        else:
            variable_costs = _float(n, 'variable_costs')

        # CREATE SINK OBJECTS
        if n.tags.get('oemof_class') == 'sink':
            if n.tags.get('energy_amount') is None:
                nominal_value = None
                if n.timeseries.get('load_profile') is not None:
                    raise ValueError('No enery amount has been specified' +
                                     ' but the load_profile has been set!')
            else:
                nominal_value = _float(n, 'energy_amount')
            s = Sink(label=n.tags['name'],
                     inputs={buses[node_bus[0]]:
                     Flow(nominal_value=nominal_value,
                          actual_value=n.timeseries['load_profile'],
                          variable_costs=variable_costs,
                          fixed=True)})
            s.type = n.tags['type']
        # CREATE SOURCE OBJECTS
        if n.tags.get('oemof_class') == 'source':
            s = Source(label=n.tags['name'],
                       outputs={buses[node_bus[0]]:
                           Flow(nominal_value=_float(n, 'installed_power'),
                                actual_value=n.timeseries.get('load_profile'),
                                variable_costs=variable_costs,
                                fixed=True)})
            s.fuel_type = n.tags['fuel_type']
            s.type = n.tags['type']
        # CREATE TRANSFORMER OBJECTS
        if n.tags.get('oemof_class') == 'linear_transformer':
            # CREATE LINEAR TRANSFORMER
            if n.tags.get('type') == 'flexible_generator':
                ins =  global_buses[n.tags['fuel_type']]
                outs = buses[node_bus[0]]
                t = LinearTransformer(label=n.tags['name'],
                        inputs={ins: Flow(variable_costs=variable_costs)},
                        outputs={outs: Flow(nominal_value=_float(n, 'installed_power'))},
                        conversion_factors={outs:_float(n, 'efficiency')})
                # store fuel_type as attribute for identification
                t.fuel_type = n.tags['fuel_type']
                t.type = n.tags['type']

            # CREATE COMBINED HEAT AND POWER AS LINEAR TRANSFORMER
            if n.tags.get('type') == 'combined_flexible_generator':
                ins =  global_buses[n.tags['fuel_type']]
                heat_out = [buses[k] for k in node_bus
                            if buses[k].energy_sector == 'heat'][0]
                power_out = [buses[k] for k in node_bus
                             if buses[k].energy_sector == 'electricity'][0]
                t = LinearTransformer(label=n.tags['name'],
                                inputs={ins: Flow(variable_costs=variable_costs)},
                                outputs={power_out: Flow(
                                    nominal_value=_float(n, 'installed_power')),
                                         heat_out: Flow()},
                                conversion_factors={
                            heat_out: _float(n, 'thermal_efficiency'),
                            power_out: _float(n, 'electrical_efficiency')})
                t.fuel_type = n.tags['fuel_type']
                t.type = n.tags['type']

        # CRAETE STORAGE OBJECTS
        if n.tags.get('oemof_class') == 'storage':
            # Oemof solph does not provide direct way to set power in/out of
            # storage hence, we need to caculate the needed ratios upfront
            nicr = (_float(n,'installed_power') /
                    _float(n,'installed_energy'))
            nocr = (_float(n,'installed_power') /
                    _float(n,'installed_energy'))
            s = Storage(label=n.tags['name'],
                        inputs={buses[node_bus[0]]:
                                    Flow(variable_costs=variable_costs)},
                        outputs={buses[node_bus[0]]:
                                    Flow(variable_costs=variable_costs)},
                        nominal_capacity=_float(n,'installed_energy'),
                        nominal_input_capacity_ratio=nicr,
                        nominal_output_capacity_ration=nocr)
            s.energy_sector = n.tags['energy_sector']
            s.type = n.tags['type']

    # loop over all ways to create transmission objects
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
                # 1st transformer
                t1 = LinearTransformer(label=w.tags['name']+'_1',
                          inputs={outs: Flow()},
                         outputs={
                    ins: Flow(nominal_value=_float(w,'installed_power'))},
                conversion_factors={ins:_float(w,'efficiency')})
                t1.type = w.tags.get('type')
                # 2nd transformer
                t2 = LinearTransformer(label=w.tags['name']+'_2',
                                  inputs={
                    ins: Flow()},
                                  outputs={
                    outs: Flow(nominal_value=_float(w,'installed_power'))},
                conversion_factors={outs:_float(w,'efficiency')})
                t2.type = w.tags.get('type')

    # Create optimization model, solve it, wrtie back results
    om = OperationalModel(es=energy_system)
    if 'solver' in kwargs.keys():
        solver = kwargs['solver']
    else:
        solver = 'glpk'
    om.solve(solver=solver,
             solve_kwargs={'tee': True, 'keepfiles': False})
    om.results()

    # create results dataframe based on oemof's outputlib (multiindex)
    esplot = output.DataFramePlot(energy_system=energy_system)


    # select subsets of data frame (full hub balances) and write to temp-csv
    csv_links = {}
    for b in buses.values():
        subset = esplot.slice_by(bus_label=b.label,
                                 type='to_bus').unstack([0,1,2])
        fd, temp_path = mkstemp(dir=folder, suffix='.csv')
        file = open(temp_path, 'w')
        file.write(subset.to_csv())
        file.close()
        os.close(fd)

        head, tail = os.path.split(temp_path)
        link = "/static/" + tail
        # storage csv-file links in dictionary for html result page
        csv_links[b.label] = link

    ####################### CALCULATIONS FOR OUTPUT ###########################
    # get electical hubs production

    el_buses = [b.label for b in buses.values()
                if b.energy_sector == 'electricity']
    components = [n for n in energy_system.nodes if not isinstance(n, Bus)]

    #plot_nodes = [c.label for c in components if c.type != 'transmission']
    renewables = [c for c in components if isinstance(c, Source)]
    wind = [c.label for c in renewables if c.fuel_type == 'wind']
    solar = [c.label for c in renewables if c.fuel_type == 'solar']


    wind_production =  esplot.slice_by(bus_label=el_buses, obj_label=wind,
                                       type='to_bus').unstack(2).sum(axis=1)
    wind_production.index = wind_production.index.droplevel(1)
    wind_production = wind_production.unstack(0)
    #pdb.set_trace()
    if not wind_production.empty:
        wind_production.columns = ['wind']
    solar_production = esplot.slice_by(bus_label=el_buses, obj_label=solar,
                                       type='to_bus').unstack(2).sum(axis=1)
    solar_production.index = solar_production.index.droplevel(1)
    solar_production = solar_production.unstack(0)
    if not solar_production.empty:
        solar_production.columns = ['solar']

    # slice fuel types, unstack components and sum components by fuel type
    fossil_production = esplot.slice_by(bus_label=global_buses.keys(),
                                        type='from_bus').unstack(2).sum(axis=1)
    # drop level 'from_bus' that all rows have anyway
    fossil_production.index = fossil_production.index.droplevel(1)
    # turn index with fuel type to columns
    fossil_production = fossil_production.unstack(0)

    all_production = pd.concat([fossil_production,
                                wind_production,
                                solar_production], axis=1)
    all_production = all_production.resample('1D', how='sum')

    fossil_emissions = fossil_production.copy()
    #pdb.set_trace()
    for col in fossil_production:
        fossil_emissions[col] = fossil_production[col] * emission_factors[col]
    # sum total emissions
    emission = fossil_emissions.sum(axis=1)
    emission = emission.resample('1D', how='sum')
    # helpers for generating python-html ouput
    help_fill = ['tozeroy'] + ['tonexty']*(len(all_production.columns)-1)
    fill_dict = dict(zip(all_production.columns, help_fill))


    colors = {'gas': '#9bc8c8', 'coal': '#9b9499',
              'oil': '#2e1629', 'lignite': '#c89b9b',
              'waste': '#8b862a', 'biomass': '#187c66',
              'wind': '#2b99ff', 'solar':'#ffc125'}
    p = Bar(all_production.sum()/1e3, legend='top_right',
            title="Summend energy production",
            xlabel="Type", ylabel="Energy Production in GWh",
            width=400, height=400, palette=[colors[col]
                                            for col in all_production])
    output_file(os.path.join(folder, 'all_production.html'))

    show(p)

    e = Bar(fossil_emissions.sum(), legend='top_right',
            title="Summend CO2-emissions of production",
            xlabel="Type", ylabel="Energy Production in tons",
            width=400, height=400, palette=[colors[col]
                                            for col in all_production])
    output_file(os.path.join(folder, 'emissions.html'))
    show(e)

    plots= {'production': p, 'emissions': e}
    script, div = bokeh_components(plots)

    pdb.set_trace()
    #pdb.set_trace()
    response = (
        "<head>" +
        "<title>openmod.sh results</title>" +
        "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>" +
        "</head>" +
        ############################### Plot ##################################
        ("<body>" +
        div + script +
        "<div id='myDiv' style='width: 1000px; height: 600px;'></div>" +
        "<script>" +
        "var traces = [" +
        ", ".join(["{{x: {0}, y: {1}, fill: '{fillarg}', name: '{name}'}}".format(
                   list(range(len(all_production.index.values))),
                   list(all_production[col].values),
                   name=col,
                   fillarg=fill_dict[col]) for col in all_production]) + "];" +
        "function stackedArea(traces) {" +
                "for(var i=1; i<traces.length; i++) {" +
                    "for(var j=0; j<(Math.min(traces[i]['y'].length, traces[i-1]['y'].length)); j++) {" +
                        "traces[i]['y'][j] += traces[i-1]['y'][j];}}" +
                "return traces;}" +
        "var layout = {title: 'Total electricity production on all hubs'," +
                       "xaxis: {title: 'Day of the year'},"+
                       "yaxis : {title: 'Energy in MWh'}," +
                       "yaxis2: {title: 'CO2-emissions in tons', " +
                           "range: [0, {0}],".format(emission.max()*1.1) +
                           #"titlefont: {color: 'rgb(148, 103, 189)'}, " +
                           #"tickfont: {color: 'rgb(148, 103, 189)'}," +
                           "overlaying: 'y', side: 'right'}," +
                        "legend: {x: 0, y: 1,}};" +
        #"var data = " + "["+",".join(["{0}".format(col) for col in subset]) + "];"
        "var emission = {{x: {0}, y: {1}, type: 'scatter', yaxis: 'y2', name: 'CO2-Emissions'}};".format(
                                    list(range(len(emission.index.values))),
                                    list(emission.values)) +
        "data = stackedArea(traces);" +
        "data.push(emission);" +
        "Plotly.newPlot('myDiv', data, layout);" +
        "</script>" +
        "</body>") +
        #######################################################################
        ("You can download your results below:<br />  Hub: " +
               "<br /> Hub: ".join([
               "<a href='{1}'>{0}</a>".format(*x) for x in csv_links.items()]))
        )

    return response

