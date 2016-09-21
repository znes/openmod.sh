# **openMod.sh**: The open energy model for Schleswig-Holstein.

## Requirements

The following python packages have to be installed in order to use this:

  * flask
  * geoalchemy2
  * oemof.db
  * psycopg2
  * sqlalchemy

As you can see, `openmod.sh` depends on `oemof.db`. Have a look at it's
[README][0] for information on how to configure database access. Note
that `openMod.sh` expects its database configuration to be in a
`config.ini` section named `openMod.sh`.

As `omoef.db` is not yet released as a package on PyPI, you have to
install it from source. Be sure to install from the
`feature/select-db-to-connect-on` branch if installing manually. To
lower the barrier of entry, there's also a `requirements.txt` file at
the repository root which takes care of dependencies for you, so you
should be able to simply do:

  ```
  pip install -r requirements.txt
  python openmod.sh.py
  ```

[0]: https://github.com/oemof/oemof.db/blob/dev/README.rst#configuration

