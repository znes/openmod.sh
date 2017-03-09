import networkx as nx

nodes = [1,2,3,4]
demand = [-5,2,2,1]

# create directed graph
graph = nx.complete_graph(len(nodes), create_using=nx.DiGraph())

for edge in graph.edges():
    graph.edge[edge[0]][edge[1]]['weight'] = 1

# add node to graph with negative (!) supply for each supply node 
for i in range(len(nodes)):
    graph.node[i]['demand'] = demand[i]

flow_cost, flow_dct = nx.network_simplex(graph)

# set negative values for cooresponding negative flows
flow_lookup = flow_dct.copy()
for k,v in flow_lookup.items():
    for kk, vv in v.items():
        if vv > 0:
            flow_dct[kk][k] = - vv

print(flow_dct)
