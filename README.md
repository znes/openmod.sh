# **openMod.sh**: The open energy model for Schleswig-Holstein.

## Requirements

The following python packages have to be installed in order to use this:

  * flask
  * geoalchemy2
  * oemof.db
  * psycopg2
  * sqlalchemy

As you can see, `openmod.sh` depends on `oemof.db`. Have a look at it's
[README][0] for information on how to configure database access. There's
also a `requirements.txt` file at the repository root, so you should be
able to simply do

```
pip install -r requirements.txt
python openmod.sh.py
```

[0]: https://github.com/oemof/oemof.db/blob/dev/README.rst#configuration

