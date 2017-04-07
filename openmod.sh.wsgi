import logging
import sys
import os
logging.basicConfig(stream=sys.stderr)

# specify path to virtual environment
activate_this = '/home/kiel2/venv/bin/activate_this.py'

with open(activate_this) as venv_file:
    exec(venv_file.read(), dict(__file__=activate_this))

# specify path to root of openmod.sh
sys.path.insert(0, '/home/kiel2/openmod.sh/')

from openmod.sh.gui import app as application
application.debug = False


