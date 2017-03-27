from collections import OrderedDict as OD
import json
import pandas as pd
import multiprocessing as mp
import multiprocessing.dummy as mpd
import multiprocessing.pool as mpp

import flask
import flask_login as fl
from flask_babel import Babel, gettext, ngettext, lazy_gettext

from .bookkeeping import Job
from openmod.sh.api import (provide_element_api, json_to_db,
                           provide_elements_api, provide_sequence_api,
                           allowed_file, explicate_hubs, delete_element_from_db,
                           results_to_db, get_hub_results, create_transmission,
                           get_flow_results, get_co2_results)
from openmod.sh.forms import ComputeForm
from openmod.sh.visualization import make_graph_plot
from openmod.sh.web import app, csrf
from openmod.sh import mcbeth
from openmod.sh.config import get_config


# Set up a pool of workers to which jobs can be submitted and a dictionary
# which stores the asynchronous result objects.
app.workers = mpd.Pool(1) if app.debug else mpp.Pool(1)
app.results = OD()

babel = Babel(app)

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(flask.g, 'user', None)
    if user is not None:
        return user.locale
    # otherwise try to guess the language from the user accept
    # header the browser transmits. The best match wins.
    return flask.request.accept_languages.best_match(['de', 'en'])

@babel.timezoneselector
def get_timezone():
    user = getattr(flask.g, 'user', None)
    if user is not None:
        return user.timezone

@app.route('/API/element', methods=['GET', 'POST'])
@fl.login_required
def provide_element_api_route():
    if flask.request.method == 'GET':
        query_args = flask.request.args.to_dict()
        if 'id' in query_args.keys():
            element_dct = provide_element_api(query_args)
            return flask.jsonify(element_dct)
        return gettext(
            "Please provide correct query parameters. At least 'id'.")
    if flask.request.method == 'POST':
        data = flask.request.get_json()
        db_response = json_to_db(data)
        status=409
        if db_response['success']:
            status=201
        response = flask.Response(json.dumps(db_response),
                                  status=status, mimetype='application/json')
        return response

@app.route('/API/elements', methods=['GET'])
@fl.login_required
def provide_elements_api_route():
    query_args = flask.request.args.to_dict()
    json = provide_elements_api(query_args)
    return flask.jsonify(json)

@app.route('/API/sequence', methods=['GET'])
@fl.login_required
def provide_sequence_api_route():
    query_args = flask.request.args.to_dict()
    if 'id' in query_args.keys():
        json = provide_sequence_api(query_args)
        return flask.jsonify(json)
    return "Provide at least id as query parameter."

# TODO: should we really excempt csrf for this route?
@csrf.exempt
@app.route('/import', methods=['GET', 'POST'])
@fl.login_required
def upload_file():
    file = flask.request.files['scenariofile']
    scenario_dct = json.loads(str(file.read(), 'utf-8'))
    if flask.request.form['new_scenario_name'] != '':
        scenario_dct['name'] = flask.request.form['new_scenario_name']
    if (scenario_dct.get('api_parameters', {})
                    .get('query', {})
                    .get('hubs_explicitly') == 'false'):
        scenario_dct = create_transmission(json_file)
        scenario_dct = explicate_hubs(json_file)

    db_response = json_to_db(scenario_dct)
    status=409
    if db_response['success']:
        status=200
    db_response['scenario_name'] = scenario_dct['name']
    response = flask.Response(json.dumps(db_response),
                              status=status, mimetype='application/json')
    return response


@app.route('/export')
@fl.login_required
def export_dataset():
    return flask.render_template('export.html')

@app.route('/edit_scenario', methods=['GET'])
@fl.login_required
def edit_scenario():
    query_args = flask.request.args.to_dict()
    query_args['expand'] = 'children'

    scenario_db_id=query_args['id']
    scenario = provide_element_api(query_args)

    return flask.render_template('edit_scenario.html',
                                 scenario=scenario,
                                 scenario_db_id=scenario_db_id,
                                 slider_lookup=get_config('gui_slider', {}),
                                 global_colors=get_config('global_colors', {}),
                                 hubs=get_config('hubs', {}),
                                 region_bar_plot=get_config('region_bar_plot', {}),
                                 timeseries_available=get_config(
                                     'timeseries_available',
                                     {}),
                                 plot_tabs=get_config('plot_tabs', {}))

@app.route('/graph_plot', methods=['GET'])
@fl.login_required
def plot_graph():
    query_args = flask.request.args.to_dict()
    query_args['expand'] = 'children'
    scenario = provide_element_api(query_args)
    graph_svg = make_graph_plot(scenario)
    return flask.render_template('graph_plot.html',
                                 graph_svg=graph_svg)

@app.route('/scenario_overview')
@fl.login_required
def show_scenarios():
    model='pypsa'


    scenarios = provide_elements_api({'type': 'scenario',
                                      'parents': 'false',
                                      'predecessors': 'false',
                                      'successors': 'false',
                                      'sequences': 'false',
                                      'geom': 'false'})
    scenarios.pop('api_parameters')

    for k,v in scenarios.items():
        # additional information for scenario overview
        scenarios[k]['json'] = "/API/element?id="+str(k)+"&expand=children"

    return flask.render_template('show_scenarios.html',
                                 scenarios=scenarios,
                                 model=model)

@app.route('/delete', methods=['GET'])
@fl.login_required
def delete_scenario():
    """
    """
    query_args = flask.request.args.to_dict()

    db_response = delete_element_from_db(element_identifier=query_args['id'],
                                         by='id')

    status=500
    if db_response:
        status=204
    return flask.Response(json.dumps(db_response),
                          status=status, mimetype='application/json')

@app.route('/download', methods=['GET'])
@fl.login_required
def download():
    """
    """
    query_args = flask.request.args.to_dict()

    # comfiure the output format of the json download
    query_args.update({'expand': 'children',
                       'parents': 'true',
                       'predecessors': 'true',
                       'successors': 'true',
                       'sequences': 'true',
                       'geom': 'true',
                       'hubs_explicitly':'true'})

    if "results" in query_args:
        flow_dct = get_flow_results(scenario_identifier=query_args['id'], by='id')

        if flow_dct:
            df = pd.DataFrame(flow_dct)
            resp = flask.make_response(df.to_csv(encoding='utf-8'))
            resp.headers["Content-Disposition"] = "attachment; filename=simulation-results.csv"
            resp.headers["Content-Type"] = "text/csv"

            return resp
        else:
            return "No results available, did you compute the result of the scenario?"
    else:
        data = dict(provide_element_api(query_args))

        return flask.Response(json.dumps(data, indent=2),
                              mimetype='application/json',
                              headers={'Content-Disposition':'attachment;filename=file.json'})


@app.route('/widgets/jobs')
@fl.login_required
def jobs_widget():
  return flask.render_template('widgets/jobs.html', jobs=app.results)

@app.route('/jobs')
@fl.login_required
def jobs_page():
  return flask.render_template('pages/jobs.html', jobs=app.results)

@app.route('/kill/<job>', methods=['PUT'])
@fl.login_required
def kill(job):
    if job in app.results:
        app.results[job].cancel()
    return flask.jsonify({'jobs': jobs_widget()})

@app.route('/remove/<job>', methods=['PUT'])
@fl.login_required
def remove(job):
    if job in app.results:
        if not app.results[job].dead():
            app.results[job].cancel()
        del app.results[job]
        return flask.jsonify({'jobs': jobs_widget()})
    if job == "dead":
        for job in [j for j in app.results if app.results[j].dead()]:
            del app.results[job]
    return flask.jsonify({'jobs': jobs_widget()})

@app.route('/simulate', methods=['GET', 'PUT'])
@fl.login_required
def run_simulation():
    """
    """

    scenario = flask.request.get_json()
    user = fl.current_user.name
    parent, child = mp.Pipe()
    result = app.workers.apply_async(mcbeth.wrapped_simulation,
                                     args=(scenario, child))
    job = Job(result=result, connection=parent, scenario=scenario['name'],
              user=user)

    app.results[job.key()] = job

    return flask.jsonify({'success': True, 'job': job.key(),
                          'jobs': jobs_widget()})

@app.route('/simulation/<job>')
@fl.login_required
def simulation(job):
    job = app.results.get(job)
    if not job:
        return "Unknown job."
    elif not job.ready():
        if job.status() == "Cancelled.":
            return ("Job cancelled. <br/>" +
                    "It's still queued but will be disposed " +
                    "of before it starts.")
        return ("Job running, but not finished yet. <br />" +
                "Please come back later.")
    else:
        result = job.get()
        return result


@app.route('/API/co2_results')
@fl.login_required
def provide_co2_results_api():
    """
    """
    query_args = flask.request.args.to_dict()

    co2_results, emission_factor = get_co2_results(scenario_identifier=query_args['scenario_id'],
                                                   multi_hub_name=query_args['multi_hub_name'],
                                                   by='id', aggregated=True)
    return flask.jsonify(co2_results)

@app.route('/API/flow_results')
@fl.login_required
def provide_flow_results_api():
    """
    """
    query_args = flask.request.args.to_dict()

    # by scenario id
    flow_results = get_flow_results(query_args['scenario_id'],
                                    subset=query_args.get('subset', 'false'))

    if flow_results:
        flow_results = {k[0]+' -> '+k[1]: v for k,v in flow_results.items()}

    return flask.jsonify(flow_results)


@app.route('/API/hub_results')
@fl.login_required
def provide_results_api():
    """
    """
    query_args = flask.request.args.to_dict()

    if query_args.get('aggregated','') == 'true':
        hub_results = get_hub_results(query_args['scenario_id'],
                                      hub_name=query_args['hub_name'],
                                      by='id',
                                      aggregated=True)
        return flask.jsonify(hub_results)
    if query_args.get('aggregated', '') == 'false':
        hub_results = get_hub_results(query_args['scenario_id'],
                                      hub_name=query_args['hub_name'],
                                      by='id',
                                      aggregated=False)
        return flask.jsonify(hub_results)



##### Persistence code ends here ##############################################


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
