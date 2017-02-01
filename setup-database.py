import openmod.sh.schemas.oms as oms
from openmod.sh import web

web.app.app_context().push()
oms.DB.create_all()
oms.DB.session.flush()

username = 'admin'
user = oms.User(username, username)
oms.DB.session.add(user)
oms.DB.session.flush()


################################################################################
# Add test data ################################################################
################################################################################

tags = [oms.Tag('name', '1'), oms.Tag('name', '2')]

for tag in tags: oms.DB.session.add(tag)
oms.DB.session.flush()

sequence = oms.Sequence('profile', [1,5,6,3])
oms.DB.session.add(sequence)
oms.DB.session.flush()

# so far geom type is still a string
geom = oms.Geom('point', '54.5,17.1')
oms.DB.session.add(geom)
oms.DB.session.flush()

elements = []
for tag in tags:
    element = oms.Element(user=user,
                          geom=geom,
                          # many to many association not working yet therefore ids...
                          tags=[tag],
                          sequences=[sequence])
    oms.DB.session.add(element)
    elements.append(element)

element.children = [elements[0]]

for element in elements: oms.DB.session.add(element)

oms.DB.session.commit()
