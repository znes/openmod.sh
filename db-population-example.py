#! /usr/bin/env python

# First we have to import some code from openmod.sh so we can just work with
# the models it declares.
import openmod.sh.schemas.osm as osm
from openmod.sh import web

# This line is necessary so that flask-sqlalchemy creates a database session
# for us.
web.app.app_context().push()

# Let's store a shortcut to the session to save some typing.
db = osm.DB.session

# The OSM API (kind of) requires a changeset on everything. We don't use the
# features it provides for now, but in order to please the iD editor, let's
# create one which we can attach to all edits later on.
cs = osm.Changeset()
db.add(cs)
db.commit()

# This assumes that you have stored the data you want to populate the database
# with in a file called 'data.pickle'.
import dill as pickle
with open("data.dill", "r+b") as f:
  result = pickle.load(f)

# The file format is as follows:
#
#   * the `results` variable created above has the attribute `relations` which
#     is the one we are currently interested in.
#   * this attribute is a list of objects.
#   * each of these objects has the attribute `master_way_squeezed`.
#   * `master_way_squeezed` is a list of objects with the attributes `lat`,
#     `lon` and `id`. These objects correspond to nodes in the OSM database.
#     The `id` attribute is the `id` of the node in the OSM database, which we
#     currently don't care about.
#   * the whole `master_way_squeezed` list corresponds to one "way" in the OSM
#     database.
#
# Let's see how easy it is to populate our database with data in this format.

for i, r in enumerate(result.relations):
    nodes = [osm.Node(n.lat, n.lon, 1, cs.id)
            for n in r.master_way_squeezed[0:-1:50]]
    nodes.append(nodes[0])
    way = osm.Way(version='1', nodes=nodes, uid=1, changeset=cs,
                  tags=( [osm.Tag(key="area", value="yes")] +
                         ([osm.Tag(key="name", value=r.tags["name"])]
                                if r.tags.get("name")
                                else [])))
    db.add(way)
    print("Committing way #{}".format(i))
    db.commit()

