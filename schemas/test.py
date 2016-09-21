from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base

import sqlalchemy as db


class Plant(declarative_base()):
    __tablename__ = "plants"
    __table_args__ = {"schema": "test"}
    id = db.Column("id", db.String(), primary_key=True)
    type = db.Column("type", db.String())
    geometry = db.Column("geom", Geometry("POINT"))
    capacity = db.Column("capacity", db.Integer())


class Timeseries(declarative_base()):
    __tablename__ = "timeseries"
    __table_args__ = {"schema": "test"}
    plant = db.Column("plantid", db.String(), primary_key=True)
    step = db.Column("timestep", db.Integer, primary_key=True)
    value = db.Column("value", db.Integer())
    
class Grid(declarative_base()):
    __tablename__ = "grid"
    __table_args__ = {"schema": "test"}
    id = db.Column("osm_id", db.Integer(), primary_key=True)
    type = db.Column("power", db.String())
    geometry = db.Column("way", Geometry(geometry_type="LineString"))
    voltage = db.Column("voltage", db.String())
    
