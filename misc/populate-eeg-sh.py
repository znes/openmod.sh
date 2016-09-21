import pandas as pd
import openmod.sh.schemas.osm as osm
from openmod.sh import web

web.app.app_context().push()
db = osm.DB.session
cs = osm.Changeset()
db.add(cs)
db.commit()

x = pd.read_csv("eeg-sh.csv")

for i, r in x.iterrows():
    node = osm.Node(r['lat'], r['lon'], 1, cs.id,
                    tags=[("area", "yes"),
                          ("type", r["generation"]),
                           ("installed_capacity", r["electrical"])])
    db.add(node)
    db.commit()
    print(i)



