import pydot

def make_graph_plot(scenario):
    graph = pydot.Dot(graph_type='digraph')
    graph.add_edge(pydot.Edge('parent', 'child', label='child-attr'))
    graph.add_edge(pydot.Edge('parent', 'child', label='parent-attr', color='gray'))
    graph.add_edge(pydot.Edge('predecessor', 'successor', label='pre-attr', color='blue'))
    graph.add_edge(pydot.Edge('predecessor', 'successor', label='suc-attr', color='red'))
    for child in scenario.get('children'):
        edge = pydot.Edge(scenario.get('name'), child.get('name'))
        graph.add_edge(edge)
        for par in child.get('parents'):
            edge = pydot.Edge(par, child.get('name'), color='gray')
            graph.add_edge(edge)
        for pre in child.get('predecessors'):
            edge = pydot.Edge(pre, child.get('name'), color='blue')
            graph.add_edge(edge)
        for suc in child.get('successors'):
            edge = pydot.Edge(child.get('name'), suc, color='red')
            graph.add_edge(edge)
    svgs = graph.create_svg()
    svgs = svgs.decode('utf-8')
    return svgs
