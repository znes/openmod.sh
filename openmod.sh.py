import itertools
import json

from flask import Flask, render_template
from geoalchemy2.functions import ST_AsGeoJSON as geojson
from sqlalchemy.orm import sessionmaker

import sqlalchemy as db

from schemas import test as schema  # dev as schema


app = Flask(__name__)

Plant = schema.Plant
Timeseries = schema.Timeseries

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
    return render_template('index.html', plants=plants, series=series)


@app.route('/series')
def series():
    # TODO: Don't use a hardcoded limit. Use a parameter.
    plants = zip(itertools.count(), session.query(Plant).limit(5))
    series = session.query(Timeseries)
    # Better but still improvable. Now generates one query per plant, which
    # incurs the time overhead of a database request for each plant. But at
    # least we no longer have quadratic complexity.
    # If you want to know why the data is structured the way it is, consult the
    # [Flot data format][0] documentation.
    #
    # [0]: https://github.com/flot/flot/blob/master/API.md#data-format
    series_data = [{"lines": {"show": False}, "lines": {"fill": True},
                    "label": "P" + str(i),
                    "data": [[t.step, t.value]
                             for t in series.filter(Timeseries.plant ==
                                                    plant.id)]}
                   for i, plant in plants]
    series_json = json.dumps(series_data)
    return series_json


@app.route('/plants-json')
def plant_coordinate_json():
    plants = session.query(geojson(Plant.geometry)).all()
    return json.dumps({"features": [{"type": "Feature",
                                     "geometry": json.loads(p[0]),
                                     "properties": None
                                     }
                                    for p in plants],
                       "type": "FeatureCollection"})


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
