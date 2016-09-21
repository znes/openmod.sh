# -*- coding: utf-8 -*-
"""

"""


import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from openmod.sh.schemas import dev as dev
from openmod.sh import web


# This line is necessary so that flask-sqlalchemy creates a database session
# for us.
web.app.app_context().push()

# Let's store a shortcut to the session to save some typing.
DB = dev.DB.session

#df = pd.read_csv('../data/region-shapes-sh.csv', dtype={'region_key':str})
#for i,r in df.iterrows():
#    region = dev.Region(region_id=r['region_key'],
#                        geom_polygon=r['wkt_polygon'],
#geom_point=r['wkt_point'])
#    DB.add(region)
#    print('Commiting region {}.'.format(i))
#    DB.commit()

df = pd.read_csv('../data/temperature_stations.csv')

for i,r in df.iterrows():
    station  = dev.TemperatureStation(station_id=r['station_id'],
                                      lon=r['lon'],
                                      lat=r['lat'],
                                      name=r['name'])
    DB.add(station)
    print('Commiting station {}.'.format(i))
    DB.commit()
