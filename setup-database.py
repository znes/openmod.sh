import openmod.sh.schemas.oms as oms
from openmod.sh import web

web.app.app_context().push()
oms.DB.create_all()
oms.DB.session.commit()

username = 'admin'
user = oms.User(username, username)
oms.DB.session.add(user)
oms.DB.session.commit()


################################################################################
# Add test data ################################################################
################################################################################

tag = oms.Tag('installed_power', '10')
oms.DB.session.add(tag)
oms.DB.session.commit()

sequence = oms.Sequence('profile', [1,5,6,3])
oms.DB.session.add(sequence)
oms.DB.session.commit()

# so far geom type is still a string
geom = oms.Geom('point', '54.5,17.1')
oms.DB.session.add(geom)
oms.DB.session.commit()

element = oms.Element(user=user,
                      geom=geom,
                      # many to many association not working yet therefore ids...
                      tag_id=tag.tag_id,
                      sequence_id=sequence.sequence_id)
oms.DB.session.add(element)
oms.DB.session.commit()

