# -*- coding: utf-8 -*-
"""

"""
import numpy as np
import overpy
from overpy import RelationWay as RW

api = overpy.Overpass()

ways_and_nodes = api.query("""area[admin_level=4]
                                  ["name"="Schleswig-Holstein"]
                                  [boundary=administrative]->.boundaryarea;
                              rel(area.boundaryarea)[boundary=administrative]
                                                    [admin_level=6];
                              (way(r);>;);
                              out;""")

relations = api.query("""area[admin_level=4]
                          ["name"="Schleswig-Holstein"]
                          [boundary=administrative]->.boundaryarea;
                      rel(area.boundaryarea)[boundary=administrative]
                                            [admin_level=6];
                      out;""")
ways_and_nodes.expand(relations)

result = ways_and_nodes
def squeeze(way):
    if len(way) > 2000:
        f = int(np.ceil(len(way) / 2000))
        squeezed = way[0:-1][::f] + [way[-1]]
    else:
        return way
    return squeezed


for r in result.relations:
    r.master_way = []
    for m in r.members:
        if isinstance(m, RW) and m.role=='outer':
            sub_ways = result.get_way(m.ref)
            r.master_way = r.master_way + sub_ways.nodes
    r.master_way_squeezed = squeeze(r.master_way)
    if r.master_way_squeezed[0] != r.master_way_squeezed[-1]:
        print(r.id)
        #raise ValueError("First Node ID and last Node ID not matching!")

### plot for testing .....
import matplotlib.pyplot as plt

for r in result.relations:
    coords = [[c.lon,c.lat] for c in r.master_way_squeezed]
    x = [i for i,j in coords]
    y = [j for i,j in coords]
    plt.plot(x,y)
