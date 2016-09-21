import json

from flask import Flask, render_template
from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import sqlalchemy as db

app = Flask(__name__)

with open("uphpd") as f:
    config = {k: v for (k, v) in
              zip(["user", "password", "host", "port", "database"],
                  filter(bool, f.read().splitlines()))}

engine = db.create_engine(
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
        **config))

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class Plant(Base):
    __tablename__ = "plants"
    __table_args__ = {"schema": "test"}
    id = db.Column("id", db.String(), primary_key=True)
    type = db.Column("type", db.String())
    geometry = db.Column("geom", Geometry("POINT"))
    capacity = db.Column("capacity", db.Integer())


class Timeseries(Base):
    __tablename__ = "timeseries"
    __table_args__ = {"schema": "test"}
    plant = db.Column("plantid", db.String(), primary_key=True)
    step = db.Column("timestep", db.Integer, primary_key=True)
    value = db.Column("value", db.Integer())


@app.route('/')
def root():
    plants = session.query(Plant).count()
    series = session.query(Timeseries).count()
    return render_template('index.html', plants=plants, series=series)

@app.route('/series')
def series():
    plants = session.query(Plant).all()
    series = session.query(Timeseries).all()
    # This is not clever. It iterates through all timeseries, for all plants in
    # the 'plants' database. It would of course be better, to do this via some
    # clever SQL statement or (even better) via a concise, ORM powered join.
    # But as a proof of concept this should suffice.
    # Also: premature optimization is the root of all evil. ;)
    # The first line just contains some constant options for plotting.
    # If you want to know why the data is structured the way it is, consult the
    # [Flot data format][0] documentation.
    #
    # [0]: https://github.com/flot/flot/blob/master/API.md#data-format
    series_data = [{"lines": {"show": False}, "points": {"show": True},
                    "label": plant.id,
                    "data": [[t.step, t.value]
                             for t in series if t.plant == plant.id]}
                   for plant in plants]
    series_json = json.dumps(series_data)
    return series_json

if __name__ == '__main__':
    app.run(debug=True)

