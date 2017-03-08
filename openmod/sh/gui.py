import json

import flask
import flask_login as fl

from openmod.sh.api import (provide_element_api, json_to_db,
                           provide_elements_api, provide_sequence_api,
                           allowed_file, explicate_hubs, delete_element_from_db,
                           results_to_db, get_results, create_transmission)
from openmod.sh.forms import ComputeForm
from openmod.sh.visualization import make_graph_plot
from openmod.sh.web import app
from openmod.sh import mcbeth

import multiprocessing.pool as mpp
# Set up a pool of workers to which jobs can be submitted and a dictionary
# which stores the asynchronous result objects.
app.workers = mpp.Pool(1)
app.results = {}

@app.route('/API/element', methods=['GET', 'POST'])
def provide_element_api_route():
    if flask.request.method == 'GET':
        query_args = flask.request.args.to_dict()
        if 'id' in query_args.keys():
            element_dct = provide_element_api(query_args)
            return flask.jsonify(element_dct)
        return "Please provide correct query parameters. At least 'id'."
    if flask.request.method == 'POST':
        data = flask.request.get_json()
        json_to_db(data)
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route('/API/elements', methods=['GET'])
def provide_elements_api_route():
    query_args = flask.request.args.to_dict()
    json = provide_elements_api(query_args)
    return flask.jsonify(json)

@app.route('/API/sequence', methods=['GET'])
def provide_sequence_api_route():
    query_args = flask.request.args.to_dict()
    if 'id' in query_args.keys():
        json = provide_sequence_api(query_args)
        return flask.jsonify(json)
    return "Provide at least id as query parameter."


@app.route('/import', methods=['GET', 'POST'])
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
            if json_file['api_parameters']['query']['hubs_explicitly'] == 'false':
                json_file = create_transmission(json_file)
                json_file = explicate_hubs(json_file)

            val = json_to_db(json_file)

            return flask.render_template('imported_successfully.html',
                                         val=val, scenario=json_file)
    return flask.render_template('import.html')


@app.route('/export')
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
def edit_scenario():
    query_args = flask.request.args.to_dict()
    query_args['expand'] = 'children'

    scenario_db_id=query_args['id']
    scenario = provide_element_api(query_args)

    return flask.render_template('edit_scenario.html', scenario=scenario,
                                 scenario_db_id=scenario_db_id)

@app.route('/graph_plot', methods=['GET'])
def plot_graph():
    query_args = flask.request.args.to_dict()
    query_args['expand'] = 'children'
    scenario = provide_element_api(query_args)
    graph_svg = make_graph_plot(scenario)
    return flask.render_template('graph_plot.html',
                                 graph_svg=graph_svg)
@app.route('/scenario_overview')
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
def show_results():
    flask.flash('Processing results...')
    return flask.render_template('show_results.html')

@app.route('/delete', methods=['GET'])
def delete_scenario():
    """
    """
    query_args = flask.request.args.to_dict()

    delete_element_from_db(element_identifier=query_args['id'],
                           by='id')

    return flask.render_template('deleted_successfully.html')

@app.route('/download', methods=['GET'])
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
def main_menu():
    return flask.render_template('main_menu.html')


@app.route('/simulate', methods=['GET', 'POST'])
def run_simulation():
    """
    """
    #scenario_json = flask.request.get_json()
    query_args = flask.request.args.to_dict()
    query_args['expand'] = 'children'
    scenario_json = provide_element_api(query_args)

    #try:
    result = app.workers.apply_async(mcbeth.wrapped_simulation,
                                     args=[scenario_json])

    key = str(id(result))

    app.results[key] = result

    #return result #json.dumps({'success':True, 'job':key})
    return '<a href="/simulation/{0}">{0}</a>'.format(key)

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


##### Persistence code ends here ##############################################


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
