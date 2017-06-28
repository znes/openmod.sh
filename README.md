# **openMod.sh**: The open energy model for Schleswig-Holstein.

## Requirements

The packages that `openmod.sh` depends on are listed in `requirements.txt`.
So until `openmod.sh` is properly packaged, it's best to just do:

  ```
  pip install -r requirements.txt
  ```

to install all necessary requirements.

## Configuration

`Openmod.sh` depends on `oemof.db`. Have a look at it's [README][0] for
information on how to configure database access. Note that `openMod.sh`
expects its database configuration to be in a `config.ini` section named
`openMod.sh R/W`. Be careful. As the 'R/W' suggests, the editor expects
read and write access. Additionaly to the standard `oemof.db` options the
following section have to be specified:
schema: e.g. public, the database schema to be used
webport: e.g. 8000, the port being used when running openmod.sh.py

## Installation and Execution

As `openmod.sh` is not a full fledged python package yet, there's really
nothing to install, you'll have to clone the repository manually. As mentioned
in [Requirements](#requirements). After you have done this, you should have a 
directory containing the source code for `openmod.sh`. Let's call it
OPENMOD.SH for the reminder of this section.

## Setting up the `openmod.sh` database (aka.: create the tables)

`Openmod.sh` expects its database structure to already be set up in a
working state so that all necessary tables already exist and data can be
queried and stored. Setting things up is best achieved by a few lines of
Python code, which the fine folks behind [flask-sqlalchemy][1] were
kind enough to [document][2].

Initializing the application to work with flask-sqlalchemy is taken care
of in the `openmod.sh` codebase, so all you have to do is import the
right modules, push an application context, create the tables and commit
the transaction. To do so, `cd` into the repository's directory and run:

  ```
  python setup-database.py
  ```

## Ready to start

Now you're ready to start `openmod.sh` which is as simple as

  ```
  python openmod.sh.py
  ```

Note that you should still be residing in OPENMOD.SH, obviously.
Then open your browser and point it to the port which is specified in
`config.ini`.

To import a scenario navigate to the `Import` page and choose a suitable file on
your hard disc. You can find example files in `OPENMOD.SH/data/scenarios`.

Enjoy.

[0]: https://github.com/oemof/oemof.db/blob/dev/README.rst#configuration
[1]: http://flask-sqlalchemy.pocoo.org/2.1/
[2]: http://flask-sqlalchemy.pocoo.org/2.1/contexts/#introduction-into-contexts

