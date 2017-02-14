# Catering for the iD editor

If your want your data to properly be displayed by the iD editor, your
`Element`s **have** to have a `geom` attribute. For the time being these
attributes are `openmod.sh.schemas.oms.Geom` objects with the following
possible combinations of parameters:

  - `type`: the string `'Point'`
    `geom`: a string containing a lattitude longitude tuple, i.e
            `'(lattitude, longitude)'`

