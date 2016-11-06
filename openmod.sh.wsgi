#!/usr/bin/python3
import logging
logging.basicConfig(stream=sys.stderr)

activate_this = cfg.get(configsection, 'venv_path')
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

from oemof.db import config as cfg
import sys
sys.path.insert(0, cfg.get(configsection, 'openmod_path'))

from openmod.sh.web import app as application
#application.debug = True

