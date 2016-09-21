import pandas as pd
import openmod.sh.schemas.osm as osm
from openmod.sh import web

web.app.app_context().push()
db = osm.DB.session
cs = osm.Changeset()
db.add(cs)
db.commit()

x = pd.read_csv("renewable_power_plants_germany.csv")

for i, r in x.iterrows():
    print(i)
    print(r)
    node = osm.Node(r['lat'], r['lon'], 1, cs.id, myid="hereami",
                    tags=[("area", "yes"), ("type", r["generator_type"])])
    db.add(node)
    db.commit()
    break


                      
