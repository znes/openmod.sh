# **openMod.sh**: The open energy model for Schleswig-Holstein.

## Requirements

The following python packages have to be installed in order to use this:

  * flask
  * flask-sqlalchemy
  * sqlachemy
  * geoalchemy2
  * psycopg2

Additionally there has to be a file called `uphpd` containing:

  * the username with which to log into the database management system (DBMS),
  * the password for the given username,
  * the hostname at which the DBMS can be reached,
  * the port on which the DBMS is listening for connections and
  * the name of the database inside the DBMS from which to access data.

Each of those should be on a line on it's own with nothing else in between.
Once you installed those, you can just do `python openmod.sh.py`.

