from json import load
from oemof.tools import helpers

basicpath = helpers.get_basic_path()
config_file = helpers.get_fullpath(basicpath, 'openmodsh.cfg.json')

try:
    with open(config_file, 'r') as f:
        openmodsh_config = load(f)
except FileNotFoundError:
    raise Exception("There is no openmodsh.cfg.json file in {}".format(basicpath))

def get_config(section=None, default=None, openmodsh_config=openmodsh_config):
    if section:
        try:
            return openmodsh_config[section]
        except KeyError:
            if default is not None:
                return default
            raise Exception("Config section not available in {}".format(config_file))
    return openmodsh_config

if __name__ == '__main__':
    print(get_config())
