from geoalchemy2 import Geometry
import sqlalchemy as db
from flask_sqlalchemy import SQLAlchemy
from oemof.db import config as cfg

metadata = db.MetaData(schema=cfg.get('openMod.sh R/W', 'schema'))
DB = SQLAlchemy(metadata=metadata)

class Region(DB.Model):
    __tablename__ = 'region'
    region_id = DB.Column("region_id", DB.String(), primary_key=True)
    #temperature_station_id = DB.Column("temperature_station_id", DB.String())
    geom_polygon = DB.Column("geom_polygon",
                             Geometry(geometry_type="MULTIPOLYGON", srid=4326))
    geom_point = DB.Column("geom_point",
                           Geometry(geometry_type="POINT", srid=4326))
    #heatdemand = DB.relationship("AnnualHeatDemand", uselist=False)
    #heatpattern = DB.relationship("HeatDemandPattern", uselist=False)

    def __init__(self, region_id, geom_point, geom_polygon):
        """
        """
        self.region_id = region_id
        #self.temperature_station_id = temperature_station_id
        self.geom_polygon = geom_polygon
        self.geom_point = geom_point

class TemperatureStation(DB.Model):
    __tablename__ = "temperature_station"
    station_id = DB.Column("station_id", DB.String(), primary_key=True)
    lon = DB.Column("lon", DB.Float())
    lat = DB.Column("lat", DB.Float())
    name = DB.Column("name", DB.String())
    def __init__(self, station_id, lon, lat, name):
        """
        """
        self.station_id = station_id
        self.lon = lon
        self.lat = lat
        self.name = name


#class AnnualHeatDemand(DB.Model):
#    __tablename__ = 'annual_heat_demand'
#    region_id = DB.Column(DB.String(), DB.ForeignKey('regions.region_id'))
#    sector = DB.Column(DB.String())
#    year = DB.Column(DB.Integer())
#    value = DB.Column(DB.Float(), nullable=False)
#    regions = DB.relationship('Regions')
#    __table_args__ = (
#        DB.PrimaryKeyConstraint('region_id', 'sector', 'year'), {},)
#
#    def __init__(self, region_id, sector, year, value):
#        """
#        """
#        self.region_id = region_id
#        self.sector = sector
#        self.year = year
#        self.value = value
#
#class HeatDemandPattern(DB.Model):
#    __tablename__ = 'heat_demand_pattern'
#    region_id = DB.Column(DB.String(), DB.ForeignKey('regions.region_id'))
#    sector = DB.Column(DB.String())
#    value = DB.Column(DB.Float(), nullable=False)
#    hour = DB.Column(DB.Float(), nullable=False)
#    regions = DB.relationship('Regions')
#
#    __table_args__ = (
#        DB.PrimaryKeyConstraint('region_id', 'sector', 'hour'), {},)
#
#    def __init__(self, region_id, sector, hour, value):
#        """
#        """
#        self.region_id = region_id
#        self.sector = sector
#        self.hour = hour
#        self.value = value
