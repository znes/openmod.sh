import openmod.sh.schemas.osm as osm
from openmod.sh import web

web.app.app_context().push()
osm.DB.create_all()
osm.DB.session.commit()

