from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base

import sqlalchemy as db
import sqlalchemy.orm as orm


class Plant(declarative_base()):
    __tablename__ = "eeg_register"
    __table_args__ = {"schema": "dev"}
    id = db.Column("id", db.String(), primary_key=True)
    type = db.Column("type", db.String())
    geometry = db.Column("geom", Geometry(geometry_type="POINT"))
    capacity = db.Column("capacity", db.Integer())

    @property
    def feedin(self):
        return (x.value for x in self.timeseries)


class Timeseries(declarative_base()):
    __tablename__ = "feed_in"
    __table_args__ = {"schema": "dev"}
    plant = db.Column("id", db.String(), db.ForeignKey(Plant.id),
                      primary_key=True)
    step = db.Column("hour", db.Integer, primary_key=True)
    value = db.Column("feed", db.Float())


class Grid(declarative_base()):
    __tablename__ = "grid"
    __table_args__ = {"schema": "dev"}
    id = db.Column("osm_id", db.Integer(), primary_key=True)
    type = db.Column("power", db.String())
    geometry = db.Column("way", Geometry(geometry_type="LineString"))
    voltage = db.Column("voltage", db.String())


Plant.timeseries = orm.relationship(Timeseries, order_by=Timeseries.step)

