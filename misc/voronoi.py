from sqlalchemy import create_engine

uri = "postgresql+psycopg2://openmodsh_admin:op3nmod!sh@localhost:5434/openmodsh"
engine = create_engine(uri)
           
# meta = MetaData(schema="voronoi")
# meta.reflect(bind=engine)

# TODO: make script shorter/combine sql commands...

sql = "\
ALTER TABLE voronoi.temperature_station ADD COLUMN geom_point geometry(Point,4326);\
UPDATE voronoi.temperature_station SET geom_point = ST_SetSRID(ST_Point(lon, lat), 4326);"
x = engine.execute(sql)
print(x)


sql = "\
CREATE TABLE voronoi.temperature_station_temp\
  AS SELECT ST_Voronoi(mytable.mycolumn, null, 0.0, true) AS voronoi_collection\
    FROM (SELECT ST_Collect(geom_point) AS mycolumn FROM voronoi.temperature_station) AS mytable;"

x = engine.execute(sql)
print(x)

sql =  "\
ALTER TABLE voronoi.temperature_station\
  ADD COLUMN voronoi geometry(Polygon, 4326);"

x = engine.execute(sql)
print(x)

sql =  "\
CREATE TABLE voronoi.temperature_station2 AS\
  SELECT (ST_Dump(voronoi_collection)).geom AS voronoi FROM voronoi.temperature_station_temp;"

x = engine.execute(sql)
print(x)

sql =  "\
ALTER TABLE voronoi.temperature_station2\
  ADD COLUMN voronoi_polygon geometry(POLYGON);\
UPDATE voronoi.temperature_station2\
  SET voronoi_polygon = ST_SetSRID(voronoi,4326);"

x = engine.execute(sql)
print(x)

sql =  "\
UPDATE voronoi.temperature_station \
SET voronoi = temp.voronoi_polygon \
FROM voronoi.temperature_station2 AS temp \
WHERE ST_Contains(temp.voronoi_polygon, temperature_station.geom_point)"

x = engine.execute(sql)
print(x)

