from flask import Flask, render_template

import json
import plotly as py

app = Flask(__name__)
app.debug = True


def make_regionplot_dict():
    fig = dict(
        data=[
            dict(
            type = 'scattergeo',
            lon = [ 9, 10, 11, 9 ],
            lat = [ 54, 54, 55, 54 ],
            mode = 'lines',
            line = dict(
                width = 1,
                color = 'red',
            ),
            opacity = 0.5,
        )
        ],
        layout={
            "title": "Kiel and Region",
            "geo": {
                "lataxis": {
                    "range": [53, 56]
                },
                "lonaxis": {
                    "range": [8, 12]
                },
                "scope": "germany",
                "showland": True,
                "showsubunits": True,
                "resolution": 50
            }
        }
    )

    return fig

@app.route('/')
def index():
    
    graphs = [make_pydict()]

    # Add "ids" to each of the graphs to pass up to the client
    # for templating
    ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]

    # Convert the figures to JSON
    # PlotlyJSONEncoder appropriately converts pandas, datetime, etc
    # objects to their JSON equivalents
    graphJSON = json.dumps(graphs, cls=py.utils.PlotlyJSONEncoder)

    return render_template('edit_scenario.html',
                           ids=ids,
                           graphJSON=graphJSON)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
