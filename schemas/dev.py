from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base

import sqlalchemy as db


class Plant(declarative_base()):
    __tablename__ = "eeg_register"
    __table_args__ = {"schema": "dev"}
    id = db.Column("id", db.String(), primary_key=True)
    type = db.Column("type", db.String())
    geometry = db.Column("geom", Geometry(geometry_type="POINT"))
    capacity = db.Column("capacity", db.Integer())


class Timeseries(declarative_base()):
    __tablename__ = "feed_in"
    __table_args__ = {"schema": "dev"}
    plant = db.Column("id", db.String(), primary_key=True)
    step = db.Column("hour", db.Integer, primary_key=True)
    value = db.Column("feed", db.Float())
