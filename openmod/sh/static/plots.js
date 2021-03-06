function makeEmissionBarPlot(div, data, layout) {
    var plotly_layout =  {
            title: layout.title,
            yaxis: {
                title: "Emissionen in t"
            },
            hovermode: !1,
            barmode: 'stack'
    };

    var heat = {
        x: ["Produktion", "Export", "Gesamt"],
        y: [data["heat"], 0, 0],
        name: "Wärme",
        type: "bar",
        marker: {color: global_colors["heat"]}
    }
    var elec = {
        x: ["Produktion", "Export", "Gesamt"],
        y: [data["electricity"], 0, 0],
        name: "Strom",
        type: "bar",
        marker: {color: global_colors["electricity"]}
    }
    var impor = {
        x: ["Produktion", "Export", "Gesamt"],
        y: [data["import"], 0, 0],
        name: "Import",
        type: "bar",
        marker: {color: global_colors["import"]}
    }
    var expor = {
        x: ["Produktion", "Export", "Gesamt"],
        y: [0, data["export"], 0],
        name: "Export",
        type: "bar",
        marker: {color: global_colors["export"]}
    }
    var total = {
        x: ["Produktion", "Export", "Gesamt"],
        y: [0, 0, data["import"]+data["export"]+data["electricity"]+data["heat"]],
        name: "Gesamt",
        type: "bar",
        marker: {color: "black"}
    }

    var data = [heat, elec, impor, expor, total];

    Plotly.newPlot(div, data, plotly_layout);
}


function makeBarPlot(div, data, layout) {
    var x_vals = [];
    var y_vals = [];

    var import_sum = 0;
    var export_sum = 0;

    $.each(data, function(key, value) {
        $.each(value['production'], function(comp_name, production) {
            x_vals.push(getLabel(comp_name));
            y_vals.push(production);
        });
        $.each(value['demand'], function(comp_name, demand) {
            x_vals.push(getLabel(comp_name));
            y_vals.push(demand);
        });
        $.each(value['import'], function(comp_name, impor) {
            import_sum = import_sum + impor
        });
		    x_vals.push('Import');
	            y_vals.push(import_sum);
		    $.each(value['export'], function(comp_name, expor) {
            export_sum = export_sum + expor
        });
		    x_vals.push('Export');
	         y_vals.push(export_sum);
    });


    var plotly_layout =  {
            title: layout.title,
            yaxis: {
                title: 'Energie in MWh',
                hoverformat: '.1f'
            },
            margin: {
                b : 160
            }
    };

    var data = [{
        x: x_vals,
        y: y_vals,
        type: 'bar'
    }];

    Plotly.newPlot(div, data, plotly_layout);

}

function makeHeatmapPlot(div, data, layout) {

    var ts = data.ts;

    var ts_matrix = []

    for (var i = 0; i < 24; i++) {
        ts_matrix[i] = []
        for (var j = 0; j < 365; j++) {
            ts_matrix[i].push(ts[j * 24 + i])
        }
    }

    var plotly_layout = {
        title: layout.title,
        axis: {
            title: 'Tag des Jahres',
        },
        yaxis: {
            title: 'Stunde des Jahres'
        }
    };

    var plotly_data = [{
        z: ts_matrix,
        type: 'heatmap'
    }];

    Plotly.newPlot(div, plotly_data, plotly_layout);
}

function makeStackedResultPlot(div, data, layout) {
    // layout_args: Object with title, div_id
    // ts: Array ot ts Object with name, ts, color
    // first element in ts is highest in stack

    var date = new Date(data.start_date);
    var timestep = data.timestep;
    var dates = Array.apply(null, Array(8760)).map(function(_, i) {
        return new Date(Date.parse(date) + ((i-1)*timestep*1000));
    });

    var selectorOptions = {
        buttons: [{
                step: 'month',
                stepmode: 'backward',
                count: 1,
                label: '1m'
            },
            {
                step: 'all'
            }
        ]
    };

    var plotly_layout = {
        title: layout.title,
        xaxis: {
            rangeselector: selectorOptions,
            rangeslider: {},
            tickformat: "%a %d-%m-%Y"
        },
        yaxis: {
            fixedrange: true,
            title: layout.yaxis_title,
            hoverformat: '.1f'
        }
    };

    var demand_objects = [];
    var storage_demand_objects = [];
    var objects = [];

    $.each(data, function(key, value) {
        $.each(value['production'], function(name, ts) {
            objects.push({'name': name, 'ts': ts})
        });
        $.each(value['demand'], function(name, ts) {
            if (scenario.children_dict[name].type == 'demand') {
                demand_objects.push({'name': name, 'ts': ts})
            }
            if (scenario.children_dict[name].type == 'storage') {
                storage_demand_objects.push({'name': name, 'ts':ts})
            }
        });
    });

    var traces = [];



    d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates, hoverinfo: "x+text+name"};
    t = objects[0];
    d.name = getLabel(t.name);
    d.marker = {"color": data.coloring[t.name].color}
    d.opacity = data.coloring[t.name].opacity

    d.y = t.ts;
    var text = [];
    t.ts.forEach(function(x) {text.push(Number(x).toFixed(1))});
    d.text = text;



    traces.push(d);
    base = t.ts;
    for (var j = 1; j <= objects.length-1; j++) {
        t = objects[j];
        d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tonexty',
             x: dates, hoverinfo: "x+text+name"};
        d.name = getLabel(t.name);
        d.marker = {"color": data.coloring[t.name].color}
        d.opacity = data.coloring[t.name].opacity
        base_plus = [];
        for (var i = 0; i < base.length; i++) {
            base_plus.push(base[i] + t.ts[i]);
        }
        d.y = base_plus;
        base = base_plus;
        var text = [];
        t.ts.forEach(function(x) {text.push(Number(x).toFixed(1))});
        d.text = text;
        //d.fillcolor = t.color;
        traces.push(d);
    };


    // Demand line
    var demand = {type: 'scatter', mode: 'lines', x: dates, hoverinfo: "x+text+name"};
    demand.name = getLabel(demand_objects[0].name);
    demand.marker = {"color": data.coloring[demand_objects[0].name].color};
    demand.line = {"width": 1};
    demand.y = demand_objects[0].ts.map(function(x) { return x * -1; });
    traces.push(demand)
    // Storage Demand line
    if (storage_demand_objects.length > 0) {
        var storage_demand = {type: 'scatter', mode: 'lines', x: dates, hoverinfo: "x+text+name"};
        storage_demand.name = getLabel(storage_demand_objects[0].name) + " (laden)";
        storage_demand.marker = {"color": "darkred"};
        storage_demand.line = {"dash": "dashdot", "width": 1};
        var y = storage_demand_objects[0].ts.map(function(x) { return x * -1; });
        storage_demand.y = addArrays([y, demand.y]);
        traces.push(storage_demand);
    }

    Plotly.newPlot(div, traces, plotly_layout);
}

function makeStackedInputPlot(div, data, layout) {
    // layout_args: Object with title, div_id
    // ts: Array ot ts Object with name, ts, color
    // first element in ts is highest in stack

    var date = new Date(data.start_date);
    var timestep = data.timestep;
    var dates = Array.apply(null, Array(8760)).map(function(_, i) {
        return new Date(Date.parse(date) + ((i-1)*timestep*1000));
    });

    var selectorOptions = {
        buttons: [{
                step: 'month',
                stepmode: 'backward',
                count: 1,
                label: '1m'
            },
            {
                step: 'all'
            }
        ]
    };

    var plotly_layout = {
        title: layout.title,
        xaxis: {
            rangeselector: selectorOptions,
            rangeslider: {},
            tickformat: "%a %d-%m-%Y",
        },
        yaxis: {
            fixedrange: true,
            title: layout.yaxis_title,
            hoverformat: '.1f'
        }
    };

    var objects = [];
    var demand_objects = [];

    $.each(data, function(key, value) {
        $.each(value['production'], function(name, ts) {
            objects.push({'name': name, 'ts': ts})
        });
        $.each(value['demand'], function(name, ts) {
            demand_objects.push({'name': name, 'ts': ts})
        });
    });

    var traces = [];
    // WE ONLY SELECT THE FIRST OBJECT OF DEMAND; AS WE ASSUME THAT THERE IS ONLY
    // AT THE MOMENT
    demand = {type: 'scatter', mode: 'lines', x: dates, hoverinfo: "x+text+name"};
    demand.name = getLabel(demand_objects[0].name)
    demand.marker = {"color": data.coloring[demand_objects[0].name].color}
    demand.y = demand_objects[0].ts
    traces.push(demand)

    d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates, hoverinfo: "x+text+name"};
    t = objects[0];
    d.name = getLabel(t.name);
    d.marker = {"color": data.coloring[t.name].color}
    d.opacity = data.coloring[t.name].opacity

    d.y = t.ts;
    var text = [];
    t.ts.forEach(function(x) {
        text.push(Number(x).toFixed(1));
    });
    d.text = text;
    //d.fillcolor = t.color;

    traces.push(d);
    base = t.ts;
    for (var j = 1; j <= objects.length-1; j++) {
        t = objects[j];
        d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tonexty',
             x: dates, hoverinfo: "x+text+name"};
        d.name = getLabel(t.name);
        d.marker = {"color": data.coloring[t.name].color}
        d.opacity = data.coloring[t.name].opacity
        base_plus = [];
        for (var i = 0; i < base.length; i++) {
            base_plus.push(base[i] + t.ts[i]);
        }
        d.y = base_plus;
        base = base_plus;
        var text = [];
        t.ts.forEach(function(x) {
            text.push(Number(x).toFixed(1));
        });
        d.text = text;
        //d.fillcolor = t.color;
        traces.push(d);
    };
    Plotly.newPlot(div, traces, plotly_layout);
}




function makeRegionPlot(plot_id) {
    document.getElementById(plot_id).outerHTML = '<div id="'+plot_id+'" style="width: 700px; height: 450px; position: relative;"></div>';
    var map = new L.Map(plot_id);
    // create the tile layer with correct attribution
    var osmUrl = 'http://{s}.tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png';
    var osmAttrib = 'Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
    var osm = new L.TileLayer(osmUrl, {
        minZoom: 8,
        maxZoom: 12,
        attribution: osmAttrib
    });

    map.setView(new L.LatLng(54.32133, 10.13489), 9);
    map.addLayer(osm);
    var polygons = ['kiel_electricity', 'ploe_electricity', 'nms_electricity', 'rdeck_electricity'];
    polygons.forEach(function(p) {
        var wicket = new Wkt.Wkt();
        var wkt_geom = scenario.children_dict[p].geom;
        wicket.read(wkt_geom);
        var polygon = wicket.toObject();
        map.addLayer(polygon);
    });
    return map;
}

function addBarToRegionPlot(map, x, y, value, label, color) {
    var line = L.polyline([[x, y], [x+value, y]],
                          {color: color,
                          weight: 10,
                          opacity: 0.8,
                          lineCap: 'butt'});
    line.bindTooltip(label);
    line.on('mouseover', function(e) {
        var layer = e.target;
        layer.setStyle({
            opacity: 1,
            weight: 11
        });
    });
    line.on('mouseout', function(e) {
        var layer = e.target;
        layer.setStyle({
            opacity: 0.8,
            weight: 10
        });
    });
    line.addTo(map);
}

function addGridToRegionPlot(map, pos, height, width) {
    var x = pos[0];
    var y = pos[1];
    var bounds = [[x-0.5*height, y-0.5*width], [x+0.5*height, y+0.5*width]];
    L.rectangle(bounds, {color: "gray", weight: 1}).addTo(map);
    return bounds;
}

function addArrowToRegionPlot(map, pos0, pos1, value, label, pixel, shorten=true) {
    if (shorten) {
        var vector = [];
        for (var i=0; i<pos0.length; i++) {
            vector.push(pos1[i]-pos0[i]);
        }
        var start_point = [];
        for (var i=0; i<pos0.length; i++) {
            start_point.push(pos0[i]+0.515*vector[i]);
        }
        var end_point = [];
        for (var i=0; i<pos0.length; i++) {
            end_point.push(start_point[i]+0.12*vector[i]);
        }
    } else {
        var start_point = pos0;
        var end_point = pos1;
    }
    var arrow_color = "red";
    var pixel_line = 4;
    var pixel_decorator = (pixel_line+pixel+1)*2;
    var polyline = L.polyline([start_point, end_point],
                              {color: arrow_color,
                               lineCap: 'butt',
                               opacity: 0.8,
                               weight: pixel_line}).addTo(map);
    var decorator = L.polylineDecorator(polyline, {
        patterns: [{repeat: 0,
                    offset: '100%',
                    symbol: L.Symbol.arrowHead({pixelSize: pixel_decorator,
                                                polygon: true,
                                                pathOptions: {stroke: true,
                                                              color: arrow_color,
                                                              fillOpacity: 0.8,
                                                              weight: 3}})
                   }]
        }).addTo(map);
    decorator.bindTooltip(label);
    decorator.on('mouseover', function(e) {
        var layer = e.target;
        layer.setStyle({
            opacity: 1,
            weight: 6
        });
    });
    decorator.on('mouseout', function(e) {
        var layer = e.target;
        layer.setStyle({
            opacity: 0.8,
            weight: 3
        });
    });
}

function makeTimeseriesPlot(div, data, layout) {

    var ts = data.ts;
    var date = new Date(data.start_date);
    var timestep = data.timestep; //in seconds

    var dates = Array.apply(null, Array(ts.length)).map(function(_, i) {
        return new Date(Date.parse(date) + ((i-1)*timestep*1000));
    });

    var selectorOptions = {
        buttons: [{
                step: 'month',
                stepmode: 'backward',
                count: 1,
                label: '1m'
            },
            {
                step: 'all'
            }
        ]
    };
    var layout_plotly = {
        xaxis: {
            rangeselector: selectorOptions,
            rangeslider: {},
            tickformat: "%a %d-%m-%Y"
        },
        yaxis: {
            fixedrange: true,
            title: layout.yaxis_title,
            hoverformat: '.1f'
        }
    };
    layout_plotly.title = layout.title;


    var data_plotly = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates};

    data_plotly.name = data.name;
    data_plotly.y = ts;
    data_plotly.fillcolor = data.color;

    data_plotly = [data_plotly];

    Plotly.newPlot(div, data_plotly, layout_plotly);
}

function makeOrderedTimeseriesPlot(div, data, layout) {
    var ts_ordered = JSON.parse(JSON.stringify(data.ts));
    var ts_ordered = ts_ordered.sort(function(a, b) {
            return b - a
        });

    var dates = Array.apply(null, Array(ts_ordered.length)).map(function(_, i) {
        return i + 1;
    });

    var selectorOptions = {
        buttons: [{
                step: 'month',
                stepmode: 'backward',
                count: 1,
                label: '1m'
            },
            {
                step: 'all'
            }
        ]
    };
    var layout_plotly = {
        xaxis: {
            title: "Hours",
            rangeselector: selectorOptions,
            rangeslider: {}
        },
        yaxis: {
            title: layout.yaxis_title,
            fixedrange: true,
            hoverformat: '.2f'
        }
    };
    layout_plotly.title = layout.title;


    var data_plotly = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates};

    data_plotly.name = data.name;
    data_plotly.y = ts_ordered;
    data_plotly.fillcolor = data.color;

    data_plotly = [data_plotly];

    Plotly.newPlot(div, data_plotly, layout_plotly);
}
