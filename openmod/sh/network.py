from sys import stdout

from sqlalchemy.orm import sessionmaker

from oemof.core.energy_system import EnergySystem as ES
from oemof.core.network.entities import Bus
import oemof.core.network.entities.components as components
import oemof.db as db

from .schemas import dev as schema

def from_db(debug=False):
    engine = db.engine("openMod.sh")

    Session = sessionmaker(bind=engine)
    session = Session()

    es = ES()

    nrg = "Energie"
    buses = {t: Bus(uid=t, type=t) for t in ["Gas", "Biomasse", nrg]}
    query = session.query(schema.Plant)
    count = query.count()
    for i, p in enumerate(query.all()):
        stdout.write("\r{0:5}: {1:6.2%}".format(i, i/count)) if debug else None
        if p.type in ["Wasserkraft", "Windkraft", "Solarstrom"]:
            components.Source(uid=p.id, outputs=[buses[nrg]], val=p.feedin)
        elif p.type in ["Gas", "Biomasse"]:
            components.Transformer(uid=p.id, inputs=[buses[p.type]],
                                   outputs=[buses[nrg]],
                                   val=p.feedin)


    print() if debug else None
    return es

