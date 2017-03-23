from sys import stdout

from sqlalchemy.orm import sessionmaker

from oemof.core.energy_system import EnergySystem as ES
from oemof.core.network.entities import Bus
import oemof.core.network.entities.components as components
import oemof.db as db

from .schemas import dev as schema

# This is debugging stuff that can be ignored.
from datetime import datetime
def stopwatch():
    if not hasattr(stopwatch, "now"):
        stopwatch.now = datetime.now()
        return None
    last = stopwatch.now
    stopwatch.now = datetime.now()
    return str(stopwatch.now-last)[0:-4]
### Debugging stuff over.

def from_db(debug=False):
    engine = db.engine("openMod.sh")

    Session = sessionmaker(bind=engine)
    session = Session()

    es = ES()

    nrg = "Energie"
    buses = {t: Bus(uid=t, type=t) for t in ["Gas", "Biomasse", nrg]}
    query = session.query(schema.Plant)
    count = query.count()
    time = stopwatch()
    perc = 0
    for i, p in enumerate(query.all()):
        time = stopwatch() if not int(perc * 10) == int(10 * i/count) else time
        perc = i/count
        stdout.write("\r{0:5}: {1:6.2%} ({2} for last 10%)".format(
            i,
            perc,
            time if time else "?")) if debug else None
        if p.type in ["Wasserkraft", "Windkraft", "Solarstrom"]:
            components.Source(uid=p.id, outputs=[buses[nrg]], val=p.feedin)
        elif p.type in ["Gas", "Biomasse"]:
            components.Transformer(uid=p.id, inputs=[buses[p.type]],
                                   outputs=[buses[nrg]],
                                   val=p.feedin)


    print() if debug else None
    return es

