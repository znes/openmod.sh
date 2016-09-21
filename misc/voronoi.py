from sqlalchemy import create_engine

uri = "postgresql+psycopg2://openmodsh_admin:op3nmod!sh@localhost:5434/openmodsh"
engine = create_engine(uri)
           
# meta = MetaData(schema="voronoi")
# meta.reflect(bind=engine)

sql = "\
ALTER TABLE voronoi.temperature_station\
 ADD COLUMN geom_point geometry(Point,4326); \
UPDATE voronoi.temperature_station\
 SET geom_point = ST_SetSRID(ST_Point(lon, lat), 4326);"
x = engine.execute(sql)
print(x)


sql =  "\
ALTER TABLE voronoi.temperature_station\
    ALTER COLUMN geom_point TYPE geometry(MultiPoint,4326) USING ST_Multi(geom_point);"

x = engine.execute(sql)
print(x)

sql = "\
ALTER TABLE voronoi.temperature_station\
 ADD COLUMN geom_polygon geometry(MultiPolygon,4326); \
UPDATE voronoi.temperature_station\
 SET geom_polygon = ST_SetSRID(ST_CollectionExtract(ST_Voronoi(geom_point, null, 0.0, true), 3), 4326);"

x = engine.execute(sql)
print(x)
