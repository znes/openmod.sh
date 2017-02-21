import json
import plotly as py
import shapely

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
