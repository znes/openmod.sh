import json
import plotly as py
import shapely

def make_regionplot_dict(scenario):
    """
    for variable bar_height on update of slider one could change d attribute of:
    
    <g class="trace scattergeo" style="opacity: 1;"><path class="js-line" d="M245.41489361702133,150.11702127659737L245.41489361702133,27.329787234046307" style="fill: none; stroke: rgb(0, 0, 255); stroke-opacity: 1; stroke-width: 10px;"></path></g>
    
    with javascript in html template
    
    or change
    
    graphs[i].data[4]['lat']
    
    see console.log in html template    
    """
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
                "resolution": 50}
         }
    )
    return fig
