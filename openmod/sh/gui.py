import json
import multiprocessing.dummy as mpd
import multiprocessing.pool as mpp

import flask
import flask_login as fl
from flask_babel import Babel, gettext, ngettext, lazy_gettext

from openmod.sh.api import (provide_element_api, json_to_db,
                           provide_elements_api, provide_sequence_api,
                           allowed_file, explicate_hubs, delete_element_from_db,
                           results_to_db, get_hub_results, create_transmission)
from openmod.sh.forms import ComputeForm
from openmod.sh.visualization import make_graph_plot
from openmod.sh.web import app
from openmod.sh import mcbeth
from openmod.sh.config import get_config


# Set up a pool of workers to which jobs can be submitted and a dictionary
# which stores the asynchronous result objects.
app.workers = mpd.Pool(1) if app.debug else mpp.Pool(1)
app.results = {}

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
        return gettext("Please provide correct query parameters. At least 'id'.")
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


@app.route('/import', methods=['GET', 'POST'])
@fl.login_required
def upload_file():
    if flask.request.method == 'POST':
        # if a json file is posted, try to write it to db
        json_dict = flask.request.get_json()

        if json_dict:
            val = json_to_db(json_dict)
            if val:
                return json.dumps({'success':True});
            else:
                return json.dumps({'success':False})
        # if no json file is posted we assum that its a file
        # check if the post request has the file part
        if 'file' not in flask.request.files:
            flask.flash('No file part')
            return flask.redirect(flask.request.url)
        file = flask.request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flask.flash('No selected file')
            return flask.redirect(flask.request.url)
        if file and allowed_file(file.filename):
            #filename = secure_filename(file.filename)
            json_file = json.loads(str(file.read(), 'utf-8'))
            if (json_file.get('api_parameters', {})
                         .get('query', {})
                         .get('hubs_explicitly') == 'false'):
                json_file = create_transmission(json_file)
                json_file = explicate_hubs(json_file)

            db_response = json_to_db(json_file)
            return flask.render_template('imported_successfully.html',
                                         val=db_response['success'],
                                         scenario=json_file)
    return flask.render_template('import.html')


@app.route('/export')
@fl.login_required
def export_dataset():
    return flask.render_template('export.html')

@app.route('/id_editor')
@fl.login_required
def id_editor():
    scenario_id = flask.request.args.get('id')
    try:
        flask.session["scenario"] = json.loads(scenario_id)
    except:
        pass
    return flask.render_template('iD.html')

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
                                 jobs=sorted(app.results))

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

@app.route('/show_results', methods=['GET', 'POST'])
@fl.login_required
def show_results():
    flask.flash('Processing results...')
    return flask.render_template('show_results.html')

@app.route('/delete', methods=['GET'])
@fl.login_required
def delete_scenario():
    """
    """
    query_args = flask.request.args.to_dict()

    delete_element_from_db(element_identifier=query_args['id'],
                           by='id')

    return flask.render_template('deleted_successfully.html')

@app.route('/download', methods=['GET'])
@fl.login_required
def download_json():
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

    data = dict(provide_element_api(query_args))

    return flask.Response(json.dumps(data, indent=2),
               mimetype='application/json',
               headers={'Content-Disposition':'attachment;filename=file.json'})


@app.route('/main_menu')
@fl.login_required
def main_menu():
    return flask.render_template('main_menu.html')

@app.route('/jobs')
def jobs():
  return flask.render_template('jobs.html', jobs=sorted(app.results))

@app.route('/simulate', methods=['GET', 'PUT'])
def run_simulation():
    """
    """

    scenario = flask.request.get_json()
    result = app.workers.apply_async(mcbeth.wrapped_simulation,
                                     args=[scenario])

    key = str(id(result))

    app.results[key] = result

    return json.dumps({'success': True, 'job': key,
                       'jobs': jobs()})

@app.route('/simulation/<job>')
def simulation(job):
    if not job in app.results:
        return "Unknown job."
    elif not app.results[job].ready():
        return ("Job running, but not finished yet. <br />" +
                "Please come back later.")
    else:
        result = app.results[job].get()
        del app.results[job]
        return result


@app.route('/API/results/aggregated')
def provide_results_api():
    """
    """
    query_args = flask.request.args.to_dict()

    if 'hub_name' in query_args:
        hub_results = get_hub_results(query_args['scenario_id'],
                                      hub_name=query_args['hub_name'],
                                      by='id',
                                      aggregated=True)
        return flask.jsonify(hub_results)

    if 'sector' in query_args:
        # TODO : implement sector results
        return False



##### Persistence code ends here ##############################################


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
