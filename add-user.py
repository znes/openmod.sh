"""
add a user to the database with

add user
python add-user.py -u USERNAME -p PASSWORD

delete user
python add-user.py -d USERNAME

"""

from getopt import getopt
import sys

import openmod.sh.schemas.oms as oms
from openmod.sh import web

args = sys.argv[1:]

options, remainder = getopt(args, 'u:p:d:')

options_dct = {opt: arg for opt, arg in options}
print(options_dct)


web.app.app_context().push()
if '-u' in options_dct:
    username = options_dct['-u']
    password = options_dct['-p']

    user = oms.User(username, password)
    oms.DB.session.add(user)
    oms.DB.session.commit()
    oms.DB.session.close()
    print("User {} with password {} added to database.".format(username,
                                                              password))

if '-d' in options_dct:
    username = options_dct['-d']
    to_be_deleted = oms.DB.session.query(oms.User).filter_by(name=username).first()
    if to_be_deleted is None:
        raise Exception("User {} not in database.".format(username))
    oms.DB.session.delete(to_be_deleted)
    oms.DB.session.commit()
    oms.DB.session.close()
    print("User {} successfully deleteted.".format(username))
