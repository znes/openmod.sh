import openmod.sh.schemas.osm as osm
import openmod.sh.schemas.dev as dev
from openmod.sh import web

web.app.app_context().push()
osm.DB.create_all()
osm.DB.session.commit()

dev.DB.create_all()
dev.DB.session.commit()

username = 'admin'
user = osm.User(username, username)
osm.DB.session.commit()

