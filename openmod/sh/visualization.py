import json
import plotly as py
import shapely

def make_regionplot_dict(scenario):
    geoms = [shapely.wkt.loads(e['geom']) for e in scenario['children'] if e.get('geom', False)]
    data=[]
    for geom in geoms:
        if isinstance(geom, shapely.geometry.polygon.Polygon):
            lat, lon = geom.exterior.coords.xy
            data.append(
                dict(type = 'scattergeo',
                     lat = list(lon),
                     lon = list(lat),
                     mode = 'lines',
                     line = dict(width = 2, color = 'red'),
                     opacity = 0.5))

    fig = dict(
        data=data,
        layout={
            "title": "Kiel and Region",
            "geo": {
                "lataxis": {
                    "range": [53.9, 54.7]
                },
                "lonaxis": {
                    "range": [9.2, 10.8]
                },
                "scope": "germany",
                "resolution": 50
            }
        }
    )
    return fig
