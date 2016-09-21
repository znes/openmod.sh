# **openMod.sh**: The open energy model for Schleswig-Holstein.

## Requirements

The packages that `openmod.sh` depends on are listed in `requirements.txt`.
So until `openmod.sh` is properly packaged, them it's best to just do:

  ```
  pip install -r requirements.txt
  ```

to install all necessary requirements.

The only additional requirement is a version of the [iD][2] editor that
is modified to work with `openmod.sh` instead of [openstreetmap][1]. We
have a fork for this. It's not public yet, so if you don't know where
to find it, I can't tell you just yet. Just one hint: it's

  ```
  openmod.sh/repository/url/../iD
  ```

## Configuration

`Openmod.sh` depends on `oemof.db`. Have a look at it's [README][0] for
information on how to configure database access. Note that `openMod.sh`
expects its database configuration to be in a `config.ini` section named
`openMod.sh R/W`. Be careful. As the 'R/W' suggests, have the iD editor
expects read and write access.

## Installation and Execution

As `openmod.sh` is not a full fledged python package yet, there's really
nothing to install. You just clone the repository, `cd` into the
directory and issue a:

  ```
  python openmod.sh.py
  ```

After that, you have to serve our iD fork. So clone the corresponding
repository and run:

  ```
  python -m http.server
  ```

Then open your browser and point it to port 5000.
Enjoy.

[0]: https://github.com/oemof/oemof.db/blob/dev/README.rst#configuration
[1]: https://www.openstreetmap.org/
[2]: https://github.com/openstreetmap/iD

