# **openMod.sh**: The open energy model for Schleswig-Holstein.

## Requirements

The packages that `openmod.sh` depends on are listed in `requirements.txt`.
So until `openmod.sh` is properly packaged, it's best to just do:

  ```
  pip install -r requirements.txt
  ```

to install all necessary requirements.

The only additional requirement is a version of the [iD][2] editor that
is modified to work with `openmod.sh` instead of [openstreetmap][1]. We
have a fork for this, which, currently, you have to clone manually. It's not
public yet, so if you don't know where to find it, I can't tell you just yet.
Just one hint, it's:

  ```
  openmod.sh/repository/url/../iD
  ```

## Configuration

`Openmod.sh` depends on `oemof.db`. Have a look at it's [README][0] for
information on how to configure database access. Note that `openMod.sh`
expects its database configuration to be in a `config.ini` section named
`openMod.sh R/W`. Be careful. As the 'R/W' suggests, the iD editor expects
read and write access. Additionaly to the standard `oemof.db` options, `schema`
has to be specified as well, e.g. `public`.

## Installation and Execution

As `openmod.sh` is not a full fledged python package yet, there's really
nothing to install, you'll have to clone the repository manually. As mentioned
in [Requirements](#requirements), you also have to clone our fork of the iD
editor. After you have done this, you should have directories containing the
source code for `openmod.sh` and our iD for, respectively. Let's call them
OPENMOD.SH and ID for the reminder of this section.

First do:

  ```sh
  cd ID
  make
  ```

That bundles iD into a servable state under its 'dist' subdirectory. Now we
have to enable serving the iD editor via `openmod.sh`:

  ```
  cd OPENMOD.SH
  ln -s /../ID/dist openmod/sh/static/iD
  ```

Please note that ID **has** to be specified as an absolute path here or
things **will not work**.

## Setting up the `openmod.sh` database (aka.: create the tables)

`Openmod.sh` expects its database structure to already be set up in a
working state so that all necessary tables already exist and data can be
queried and stored. Setting things up is best achieved by a few lines of
Python code, which the fine folks behind [flask-sqlalchemy][3] were
kind enough to [document][4].

Initializing the application to work with flask-sqlalchemy is taken care
of in the `openmod.sh` codebase, so all you have to do is import the
right modules, push an application context, create the tables and commit
the transaction. To do so, `cd` into the repository's directory and run:

  ```
  python setup-database.py
  ```
## Creating test scenario

To setup the test scenario, just run
  ```
  python create-test-scenario.py
  ```
## Ready to start

Now you're ready to start `openmod.sh` which is as simple as

  ```
  python openmod.sh.py
  ```

Note that you should still be residing in OPENMOD.SH, obviously.
Then open your browser and point it to port 8000.
Enjoy.

[0]: https://github.com/oemof/oemof.db/blob/dev/README.rst#configuration
[1]: https://www.openstreetmap.org/
[2]: https://github.com/openstreetmap/iD
[3]: http://flask-sqlalchemy.pocoo.org/2.1/
[4]: http://flask-sqlalchemy.pocoo.org/2.1/contexts/#introduction-into-contexts

