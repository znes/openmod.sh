from flask import Flask
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
    response = "The openMod.sh landing page.<br>|<br>"
    plants = session.query(Plant).all()
    series = session.query(Timeseries).all()
    response += "| # of plants: {0}<br>| # of timeseries: {1}<br>|".format(
        len(plants), len(series))
    return response

if __name__ == '__main__':
    app.run(debug=True)

