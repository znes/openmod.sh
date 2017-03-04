import json

import flask
import flask_login as fl

from openmod.sh.api import (provide_element_api, json_to_db,
                           provide_elements_api, provide_sequence_api,
                           allowed_file, explicate_hubs, delete_element_from_db)
from openmod.sh.forms import ComputeForm
from openmod.sh.visualization import make_graph_plot
from openmod.sh.web import app
from openmod.sh import mcbeth

@app.route('/API/element', methods=['GET', 'POST'])
def provide_element_api_route():
    if flask.request.method == 'GET':
        query_args = flask.request.args.to_dict()
        if 'id' in query_args.keys():
            json = provide_element_api(query_args)
            return flask.jsonify(json)
        return "Please provide correct query parameters. At least 'id'."
    if flask.request.method == 'POST':
        data = flask.request.get_json()
        json_to_db(data)
        return flask.render_template('imported_successfully.html')

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
                json_file = explicate_hubs(json_file)
            val = json_to_db(json_file)
            #
            if val:
                return flask.render_template('imported_successfully.html')
            else:
                # TODO: Here goes a 'request prompt to update new scenario name
                raise ValueError('Element with name {} already ' \
                                 'exist in database'.format(json_file['name']))

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
    scenario = provide_element_api(query_args)

    return flask.render_template('edit_scenario.html', scenario=scenario)

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

@app.route('/compute_results', methods=['GET'])
def compute_results(model='oemof'):
    # model will come l
    scenario = flask.request.args.get('scenario', '')
    form = ComputeForm()
    if form.validate_on_submit():
        scn_name = form.scn_name.data
        return flask.redirect(flask.url_for('/show_results'))

    if model == 'oemof':
        return flask.render_template('compute_results.html',
                                     model=model,
                                     form=form,
                                     scenario_default=scenario)

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

    return flask.render_template('delete.html')

@app.route('/main_menu')
def main_menu():
    return flask.render_template('main_menu.html')

##### Persistence code ends here ##############################################


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
