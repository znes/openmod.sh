import json
import shapely
import igraph
import plotly.plotly as py
import plotly.graph_objs as go

from io import StringIO

def make_regionplot_dict(scenario):
    bar_height = 0.3
    bar_width = 6
    bar_left_corner = (10.12, 54.3)
    geoms = [shapely.wkt.loads(e['geom']) for e in scenario['children'] if e.get('geom', False)]
    data=[]
    for geom in geoms:
        if isinstance(geom, shapely.geometry.polygon.Polygon):
            lon, lat = geom.exterior.coords.xy
            data.append(
                dict(type = 'scattergeo',
                     lon = list(lon),
                     lat = list(lat),
                     mode = 'lines',
                     line = dict(width = 2, color = 'red'),
                     opacity = 0.5))
    
    data.append(dict(
        type = 'scattergeo',
        lon = [bar_left_corner[0], bar_left_corner[0]],
        lat = [bar_left_corner[1], bar_left_corner[1]+bar_height],
        hoverinfo = 'text',
        text = ['here it is', 'and here it ends'],
        mode = 'lines',
        line = dict( 
            width=10, 
            color='rgb(0, 0, 255)')
#            line = dict(
#                width=bar_width,
#                color='rgba(68, 68, 68, 0)'
            )
        )
    layout=dict(
            title="Kiel and Region",
            geo={"lataxis": {"range": [53.9, 54.7]},
                 "lonaxis": {"range": [9.2, 10.8]},
                 "scope": "germany",
                 "resolution": 50},
            showlegend=False)
    fig = dict(data=data, layout=layout)
    return fig

def make_timeseriesplot_dict(scenario):
    # take timeseries from scenario
    from datetime import datetime, timedelta
    from random import random
    base = datetime(2020,1,1)
    date_list = [base + timedelta(hours=x) for x in range(8760)]
    ts = [ [random() for i in range(8760)] ]
    data=[]
    for t in ts:
        data.append(
            dict(type = 'scatter',
                 x=date_list,
                 y=t))

    layout = dict(
        title='Time series with range slider and selectors',
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label='1m',
                         step='month',
                         stepmode='backward'),
                    dict(count=3,
                        label='3m',
                        step='month',
                        stepmode='backward'),
                    dict(step='all')
                ])
            ),
            rangeslider=dict(),
            type='date'
        )
    )

    fig = dict(data=data, layout=layout)
    return fig

def make_tree_plot(scenario):
    G = igraph.Graph(directed=True)
    
    G.add_vertex(scenario['name'])
    
    for i in scenario['children']:
        G.add_vertex(i)
    
    for i in scenario['children']:
        G.add_edge(scenario['name'], i)

    es = igraph.EdgeSeq(G) # sequence of edges
    E = [e.tuple for e in G.es] # list of edges
    
    nr_vertices = G.vcount()
    lay = G.layout('fr')
    position = {k: lay[k] for k in range(nr_vertices)}
    Y = [lay[k][1] for k in range(nr_vertices)]
    M = max(Y)
    
    L = len(position)
    Xn = [position[k][0] for k in range(L)]
    Yn = [2*M-position[k][1] for k in range(L)]
    Xe = []
    Ye = []
    for edge in E:
        Xe+=[position[edge[0]][0],position[edge[1]][0], None]
        Ye+=[2*M-position[edge[0]][1],2*M-position[edge[1]][1], None]

    p = igraph.plot(G)
    import pdb; pdb.set_trace()
#    imgdata = StringIO()
#    import pdb; pdb.set_trace()
#    G.write_svg(imgdata, lay)
#    print(imgdata.read())

    lines = dict(x=Xe,
                 y=Ye,
                 mode='lines',
                 line=dict(color='rgb(210,210,210)', width=1),
                 hoverinfo='none'
                 )
    dots = dict(x=Xn,
                y=Yn,
                mode='markers+text',
                marker=dict(symbol='dot',
                              size=18, 
                              color='#6175c1',    #'#DB4551', 
                              line=dict(color='rgb(50,50,50)', width=1)
                              ),
                hoverinfo='text',
                opacity=0.8,
                text=G.vs['name']
                )

    axis = dict(showline=False, # hide axis line, grid, ticklabels and  title
                zeroline=False,
                showgrid=False,
                showticklabels=False)

    layout = dict(title= 'Tree with Reingold-Tilford Layout',
                  font=dict(size=12),
                  showlegend=False,
                  xaxis=go.XAxis(axis),
                  yaxis=go.YAxis(axis),          
                  margin=dict(l=40, r=40, b=85, t=100),
                  hovermode='closest',
                  plot_bgcolor='rgb(248,248,248)'          
                  )

    data=[lines, dots]
    fig=dict(data=data, layout=layout)
    return fig
