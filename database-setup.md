# Setting up the `openmod.sh` database (aka.: create the tables)

`Openmod.sh` expects its database structure to already be set up in a
working state so that all necessary tables already exist and data can be
queried and stored. Setting things up is best achieved by a few lines of
Python code, which the fine folks behind [flask-sqlalchemy][0] were
kind enough to [document][1].

Initializing the application to work with flask-sqlalchemy is taken care
of in the `openmod.sh` codebase, so all you have to do is import the
right modules, push an application context, create the tables and commit
the transaction. To do so, `cd` into the repository's directory and do:

  ```
  python
  >>> import openmod.sh.schemas.osm as osm
  >>> from openmod.sh  import web
  >>> web.app.app_context().push()
  >>> osm.DB.create_all()
  >>> osm.DB.session.commit()
  ```

[0]: http://flask-sqlalchemy.pocoo.org/2.1/
[1]: http://flask-sqlalchemy.pocoo.org/2.1/contexts/#introduction-into-contexts

