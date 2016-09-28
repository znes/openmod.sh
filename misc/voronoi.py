"""
This script creates voronoi cells for every geo reference temperature station
of and a weiths table. For thie to work the db-tables region and 
temperature_station need to exist. (Run the populate scripts accordingly before
this one)
"""

from sqlalchemy import create_engine

uri = "postgresql+psycopg2://openmodsh_admin:3nergykollekt!v@localhost:5434/openmodsh"
engine = create_engine(uri)
    
       
# meta = MetaData(schema="voronoi")
# meta.reflect(bind=engine)

# TODO: make script shorter/combine sql commands...

schema = 'simon'

sql = "\
ALTER TABLE {0}.temperature_station ADD COLUMN geom_point geometry(Point,4326);\
UPDATE {0}.temperature_station SET geom_point = ST_SetSRID(ST_Point(lon, lat), 4326);".format(schema)
x = engine.execute(sql)
print(x)


sql = "\
CREATE TABLE {0}.temperature_station_temp\
  AS SELECT ST_Voronoi(mytable.mycolumn, null, 0.0, true) AS voronoi_collection\
    FROM (SELECT ST_Collect(geom_point) AS mycolumn FROM {0}.temperature_station) AS mytable;".format(schema)

x = engine.execute(sql)
print(x)

sql =  "\
ALTER TABLE {0}.temperature_station\
  ADD COLUMN voronoi geometry(Polygon, 4326);".format(schema)

x = engine.execute(sql)
print(x)

sql =  "\
CREATE TABLE {0}.temperature_station2 AS\
  SELECT (ST_Dump(voronoi_collection)).geom AS voronoi FROM {0}.temperature_station_temp;".format(schema)

x = engine.execute(sql)
print(x)

sql =  "\
ALTER TABLE {0}.temperature_station2\
  ADD COLUMN voronoi_polygon geometry(POLYGON);\
UPDATE {0}.temperature_station2\
  SET voronoi_polygon = ST_SetSRID(voronoi,4326);".format(schema)

x = engine.execute(sql)
print(x)

sql =  "\
UPDATE {0}.temperature_station \
SET voronoi = temp.voronoi_polygon \
FROM {0}.temperature_station2 AS temp \
WHERE ST_Contains(temp.voronoi_polygon, temperature_station.geom_point)".format(schema)
x = engine.execute(sql)
print(x)


sql = "\
CREATE TABLE {0}.area_weights AS  \
	SELECT  t.station_id t_station_id, r.region_id r_station_id, \
		st_intersection (r.geom_polygon, t.voronoi) geom, \
		st_area (st_intersection (r.geom_polygon, t.voronoi)::geography) area \
		FROM {0}.region r, {0}.temperature_station t \
		WHERE ST_Intersects(r.geom_polygon,t.voronoi);".format(schema)
x = engine.execute(sql)
print(x)

