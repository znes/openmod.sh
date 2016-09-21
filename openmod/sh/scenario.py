# Contains the simulation code

import time

from sqlalchemy.orm import sessionmaker

import oemof.db as db

# Here you would now import the `oemof` modules and proceed to customize the
# `simulate` function to generate objects and start the simulation.

from .schemas import osm


def simulate(**kwargs):
    # This is how you get a scenario object from the database.
    # Since the iD editor prefixes element ids with their type ('r' for
    # relation, 'w' for way and 'n' for node), we have to strip a leading
    # character from the scenario id string before converting it to int.
    # This is what the [1:] is for.

    engine = db.engine('openMod.sh R/W')

    Session = sessionmaker(bind=engine)
    session = Session()

    scenario = session.query(osm.Relation).get(int(kwargs['scenario'][1:]))

    # Delete the scenario id from `kwargs` so that is doesn't show up in the
    # response later.
    del kwargs['scenario']

    # Now you can access the nodes, ways and relations this scenario contains
    # and build oemof objects from them. I'll only show you how to access the
    # contents here.
    # These are lists with Node, Way and Relation objects.
    # See the .schemas.osm module for the API.
    nodes = scenario.referenced_nodes
    ways = scenario.referenced_ways
    relations = scenario.referenced # Make sure to traverse these recursively.

    # Generate a response so that we see something is actually happening.
    lengths = [len(l) for l in [nodes, ways, relations]]
    response = (
            "Done running scenario: '{scenario}'.<br />" +
            "Contents:<br />" +
            "  {0[0]:>5} nodes<br />" +
            "  {0[1]:>5} ways<br />" +
            "  {0[2]:>5} relations<br />" +
            "Parameters:<br />  " +
            "<br />  ".join(["{}: {}".format(*x) for x in kwargs.items()])
            ).format(lengths,
                     scenario=scenario.tags['name'])

    # Now sleep for 5 minutes to pretend we are doing something.
    time.sleep(300)
    return response

