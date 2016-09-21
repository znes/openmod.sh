import itertools
import json

# TODO: Change this to `import flask` so that it is easier to see what flast
#       utilities are accessed.
from flask import Flask, make_response, render_template, request
import flask_cors as cors # TODO: Check whether the `@cors.cross_origin()`
                          #       decorators are still necessary once 'iD' is
                          #       served from within this app.
import wtforms as wtf
from geoalchemy2.functions import ST_AsGeoJSON as geojson
from sqlalchemy.orm import sessionmaker

import oemof.db as db

from .schemas import dev as schema  # test as schema


app = Flask(__name__)

Plant = schema.Plant
Timeseries = schema.Timeseries
Grid = schema.Grid

engine = db.engine("openMod.sh")

Session = sessionmaker(bind=engine)
session = Session()

##### User Management #########################################################
#
# User management code. This should probably go into it's own module but I'm
# putting it all here for now, as some parts need to stay in this module while
# some parts can be factored out later.
# The 'factoring out' part can be considered an open TODO.
#
##############################################################################

class Login(wtf.Form):
    username = wtf.StringField('Username', [wtf.validators.Length(min=3,
                                                                  max=79)])
    password = wtf.StringField('Password', [wtf.validators.Length(min=3,
                                                                  max=79)])

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = Login(request.form)
    return render_template('login.html', form=form)

##### User Management stuff ends here.

@app.route('/')
def root():
    return render_template('index.html')

# TODO: Factor adding the 'Content-Type' header out into a separate function.

@app.route('/osm/api/capabilities')
@app.route('/osm/api/0.6/capabilities')
@cors.cross_origin()
def capabilities():
    template = render_template('capabilities.xml', area={"max": 1}, timeout=250)
    response = make_response(template)
    response.headers['Content-Type'] = 'text/xml'
    return response

@app.route('/osm/api/0.6/map')
@cors.cross_origin()
def osm_map():
    left, bottom, right, top = map(float, request.args['bbox'].split(","))
    minx, maxx = sorted([top, bottom])
    miny, maxy = sorted([left, right])
    nodes = [dict(id=id(n), **n)
            for n in osm_map.nodes
            for x, y in ((n["lat"], n["lon"]),)
            if minx <= x and  miny <= y and maxx >= x and maxy >= y]
    template = render_template('map.xml', nodes=nodes,
                                          minlon=miny, maxlon=maxy,
                                          minlat=minx, maxlat=maxx)

    response = make_response(template)
    response.headers['Content-Type'] = 'text/xml'
    return response

# Put a test node on the osm.map function. In a real app that data would be
# retrieved from the database.
osm_map.nodes = [{"lat": 0.0075, "lon": -0.0025,
                  "tags": {"ele": 0, # stands for 'elevation' (usually)
                           "name": "A Test Node"}}]

@app.route('/series/<path:ids>')
def series(ids):
    ids = ids.split("/")
    series = session.query(Timeseries).order_by(Timeseries.plant,
                                                Timeseries.step)
    if ids:
        series = series.filter(Timeseries.plant.in_(ids))
    # Better but still improvable. Now generates one query per plant, which
    # incurs the time overhead of a database request for each plant. But at
    # least we no longer have quadratic complexity.
    # If you want to know why the data is structured the way it is, consult the
    # [Flot data format][0] documentation.
    #
    # [0]: https://github.com/flot/flot/blob/master/API.md#data-format
    series_data = [{"lines": {"show": False}, "lines": {"fill": True},
                    "label": plant,
                    "data": [[t.step, t.value]
                             for t in ts]}
                   for plant, ts in itertools.groupby(series,
                                                      lambda s: s.plant)]
    series_json = json.dumps(series_data)
    return series_json


@app.route('/plants-json')
@app.route('/plants-json/<t>')
def plant_coordinate_json(t=None):
    # TODO: Maybe SQLAlchemy's "relationship"s can be used to do this in a
    #       simpler or more efficient way. The only problem is, that here,
    #       there is a one-to-many relationship from points/locations to
    #       powerplants, but points do not have a separate/dedicated table and
    #       therefore no uid (create a view maybe?).
    #       BUT: Using groupby on an ordered collection is already very
    #            efficient because:
    #
    #              * there is only one query (yeah, it's ordered, but thats
    #                what the DBMS is for),
    #              * the queryset is only traversed once,
    #              * 'groupby' is written in C (i.e. lightning fast) and MEANT
    #                for exactly this scenario.
    #
    #            So even if we figure out a way to do this via SQLAlchemy
    #            relationships, it's questionable whether those are faster.
    plants = session.query(geojson(Plant.geometry).label("gjson"),
                           Plant.capacity, Plant.id
                           ).order_by(Plant.geometry)
    if t:
        plants = plants.filter(Plant.type == t)
    return json.dumps({"features": [{"type": "Feature",
                                     "geometry": json.loads(k),
                                     "properties": {
                                         "plants": [{"id": p.id,
                                                     "capacity": p.capacity}
                                                    for p in ps]
                                     }}
                                    for k, ps in itertools.groupby(
                                        plants, lambda p: p.gjson)],
                       "type": "FeatureCollection"})


@app.route('/grids-json')
def grid():
    grids = session.query(geojson(Grid.geometry).label("gjson"),
                          Grid.voltage, Grid.id).all()
    return json.dumps({"features": [{"type": "Feature",
                                     "geometry": json.loads(g.gjson),
                                     "properties": {"id": g.id,
                                                    "voltage": g.voltage
                                                    }}
                                    for g in grids],
                       "type": "FeatureCollection"})


@app.route('/types')
def types():
    return json.dumps([p.type for p in
                       session.query(Plant.type).distinct().all()])


@app.route('/csv/<path:ids>')
def csv(ids):
    ids = ids.split("/")
    plants = session.query(Plant.id, Plant.capacity).order_by(Plant.id)
    if ids:
        plants = plants.filter(Plant.id.in_(ids))
    header = [d["name"] for d in plants.column_descriptions]
    app.logger.debug(header)
    plants = plants.all()
    body = "\n".join([",".join([str(getattr(p, k)) for k in header])
                      for p in plants])
    response = make_response(",".join(header) + "\n" + body)
    response.headers["Content-Disposition"] = ("attachment;" +
                                               "filename=eeg_extract.csv")
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
