import itertools
import json

from flask import Flask, render_template
from geoalchemy2.functions import ST_AsGeoJSON as geojson
from sqlalchemy.orm import sessionmaker

import sqlalchemy as db

from schemas import dev as schema  # dev as schema


app = Flask(__name__)

Plant = schema.Plant
Timeseries = schema.Timeseries
Grid = schema.Grid

with open("uphpd") as f:
    config = {k: v for (k, v) in
              zip(["user", "password", "host", "port", "database"],
                  filter(bool, f.read().splitlines()))}

engine = db.create_engine(
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
        **config))

Session = sessionmaker(bind=engine)
session = Session()


@app.route('/')
def root():
    plants = session.query(Plant).count()
    series = session.query(Timeseries).count()
    grids = session.query(Grid).count()
    return render_template('index.html', plants=plants, series=series, grids=grids)


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
def plant_coordinate_json():
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
                           ).order_by(Plant.geometry).all()
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
                           Grid.voltage, Grid.id
                           ).all()
    return json.dumps({"features": [{"type": "Feature",
                                     "geometry": json.loads(g.gjson),
                                     "properties": {
                                         "grids": [{"id": g.id,
                                                     "voltage": g.voltage}]
                                     }}
                                    for g in grids],
                       "type": "FeatureCollection"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
