#!/usr/bin/env python3
from oemof.db import config as cfg

activate_this = cfg.get(configsection, 'venv_path')
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

import sys
sys.path.insert(0, cfg.get(configsection, 'openmod_path'))

from openmod.sh.web import app as application
application.debug = True

