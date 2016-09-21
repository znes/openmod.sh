from sqlalchemy import create_engine, MetaData

uri = "postgresql+psycopg2://openmodsh_admin:op3nmod!sh@localhost:5434/openmodsh"
engine = create_engine(uri)
           
meta = MetaData(schema="voronoi")
meta.reflect(bind=engine)

#node = meta.tables["..."]