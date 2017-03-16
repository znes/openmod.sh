function makeEmissionBarPlot(div, data, layout) {

    var x_vals = [];
    var y_vals = [];

    $.each(data, function(key, value) {
                x_vals.push(key);
                y_vals.push(value);
        });

    var plotly_layout =  {
            title: layout.title,
            yaxis: {
                title: "Emission in t"
            },
            hovermode: !1,
            barmode: 'stack'
    };

    var heat = {
        x: ["Production", "Export", "Total"],
        y: [data["heat"], 0, 0],
        name: "Heat",
        type: "bar"
    }
    var elec = {
        x: ["Production", "Export", "Total"],
        y: [data["electricity"], 0, 0],
        name: "Electricity",
        type: "bar"
    }
    var impor = {
        x: ["Production", "Export", "Total"],
        y: [data["import"], 0, 0],
        name: "Import",
        type: "bar"
    }
    var expor = {
        x: ["Production", "Export", "Total"],
        y: [0, data["export"], 0],
        name: "Export",
        type: "bar"
    }
    var total = {
        x: ["Production", "Export", "Total"],
        y: [0, 0, data["import"]+data["export"]+data["electricity"]+data["heat"]],
        name: "Total",
        type: "bar"
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
            x_vals.push(comp_name);
            y_vals.push(production);
        });
        $.each(value['demand'], function(comp_name, demand) {
            x_vals.push(comp_name);
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

    var plotly_layout =  {title: layout.title,
            axis: {
                title: 'Technologies'
            },
            yaxis: {
                title: 'Production in MWh'
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
            title: 'Day of the year'
        },
        yaxis: {
            title: 'Hour of the day'
        }
    };

    var plotly_data = [{
        z: ts_matrix,
        type: 'heatmap'
    }];

    Plotly.newPlot(div, plotly_data, plotly_layout);
}


function reorderTimeseries() {
    timeseriesOrder = !timeseriesOrder;
    makeTimeseriesPlot();
}

function makeTimeseriesPlot() {
    var dates = Array.apply(null, Array(8760)).map(function(_, i) {
        return new Date(i * 3600 * 1000);
    });
    var solar = scenario.children_dict.kiel_solar.sequences.generator_profile;
    solar = solar.map(function(i) {
        return i * scenario.children_dict.kiel_solar.tags.installed_power
    });
    var wind = scenario.children_dict.kiel_wind.sequences.generator_profile;
    wind = wind.map(function(i) {
        return i * scenario.children_dict.kiel_wind.tags.installed_power
    });

    var ts = []
    for (var i = 0; i < solar.length; i++) {
        ts.push(solar[i] + wind[i]);
    }

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
    var layout = {
        xaxis: {
            rangeselector: selectorOptions,
            rangeslider: {}
        },
        yaxis: {
            fixedrange: true
        }
    };

    if (timeseriesOrder) {
        ts = ts.sort(function(a, b) {
            return b - a
        });
        dates = Array.apply(null, Array(8760)).map(function(_, i) {
            return i + 1;
        });
        var data = [{
            type: 'scatter',
            mode: 'lines',
            line: {
                color: 'black'
            },
            fill: 'tozeroy',
            x: dates,
            y: ts
        }];
        layout.title = "Duration curve of electricity production in Kiel";
        Plotly.newPlot('old_timeseries_plot', data, layout);
    } else {
        var data = [{
            name: 'solar',
            type: 'scatter',
            mode: 'lines',
            line: {
                color: 'orange',
                width: 0
            },
            fill: 'tozeroy',
            fillcolor: 'orange',
            x: dates,
            y: solar
        }, {
            name: 'wind',
            type: 'scatter',
            mode: 'lines',
            line: {
                color: 'darkblue',
                width: 0
            },
            fill: 'tonexty',
            fillcolor: 'darkblue',
            x: dates,
            y: ts
        }];
        layout.title = "Stacked electricity production in Kiel";
        Plotly.newPlot('old_timeseries_plot', data, layout);
    }
}

function makeStackedResultPlot(div, data, layout) {
    // layout_args: Object with title, div_id
    // ts: Array ot ts Object with name, ts, color
    // first element in ts is highest in stack

    // TODO: make dates accoring to scenario.tags.year
    dates = Array.apply(null, Array(8760)).map(function(_, i) {
        return new Date(i * 3600 * 1000);
    });

    selectorOptions = {
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
            rangeslider: {}
        },
        yaxis: {
            fixedrange: true
        }
    };

    var objects = []
    $.each(data, function(key, value) {
        $.each(value['production'], function(name, ts) {
            objects.push({'name': name, 'ts': ts})
        });
    });

    var traces = [];

    d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates};
    t = objects[0];
    d.name = t.name;
    d.y = t.ts;
    d.fillcolor = t.color;

    traces.push(d);
    console.log(traces)
    base = t.ts;
    for (var j = 1; j <= objects.length-1; j++) {
        t = objects[j];
        d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tonexty',
             x: dates};
        d.name = t.name;
        base_plus = []
        for (var i = 0; i < base.length; i++) {
            base_plus.push(base[i] + t.ts[i]);
        }
        d.y = base_plus;
        base = base_plus;
        //d.fillcolor = t.color;
        traces.push(d);
    };
    console.log(traces)
    Plotly.newPlot(div, traces, plotly_layout);
}


function makeSimpleTimeseriesPlot(layout_args, ts) {
    // layout_args: Object with title, div_id
    // ts: Array ot ts Object with name, ts, color
    // first element in ts is highest in stack

    // TODO: make dates accoring to scenario.tags.year
    dates = Array.apply(null, Array(ts[0].ts.length)).map(function(_, i) {
        return new Date(i * 3600 * 1000);
    });

    selectorOptions = {
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
    layout = {
        xaxis: {
            rangeselector: selectorOptions,
            rangeslider: {}
        },
        yaxis: {
            fixedrange: true
        }
    };
    layout.title = layout_args.title;

    data = [];
    d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates};

    t = ts.pop();
    d.name = t.name;
    d.y = t.ts;
    d.fillcolor = t.color;
    data.push(d);

    base = t.ts;
    for (var j = ts.length-1; j >= 0; j--) {
        t = ts[j];
        d = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tonexty',
             x: dates};
        d.name = t.name;
        base_plus = []
        for (var i = 0; i < base.length; i++) {
            base_plus.push(base[i] + t.ts[i]);
        }
        d.y = base_plus;
        base = base_plus;
        d.fillcolor = t.color;
        data.push(d);
    };

    Plotly.newPlot(layout_args.div_id, data, layout);
}

function makeRegionPlot() {
    region_plot.outerHTML = '<div id="region_plot" style="width: 700px; height: 450px; position: relative;"></div>';
    var map = new L.Map('region_plot');
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
    var bars = ['kiel_solar', 'kiel_wind'];
    bars.forEach(function(b) {
        var l = lookup[b];
        barBottom = l.pos;
        barTop = [l.pos[0] + scenario.children_dict[b].tags[l.value] / 100.0, l.pos[1]];
        var line = L.polyline([barBottom, barTop], {
            color: l.color,
            weight: 10,
            lineCap: 'butt'
        }).addTo(map);
    });
}


function makeResultTimeseriesPlot(div, data, layout) {

    var that_ts = data.ts;

    // TODO: make dates accoring to scenario.tags.year

    var dates = Array.apply(null, Array(that_ts.length)).map(function(_, i) {
        return new Date(i * 3600 * 1000);
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
            rangeslider: {}
        },
        yaxis: {
            fixedrange: true
        }
    };
    layout_plotly.title = layout.title;


    var data_plotly = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates};
    
    data_plotly.name = data.name;
    data_plotly.y = that_ts;
    data_plotly.fillcolor = data.color;

    data_plotly = [data_plotly];

    Plotly.newPlot(div, data_plotly, layout_plotly);
}

function makeOrderedResultTimeseriesPlot(div, data, layout) {

    var this_ts = data.ts;
    // TODO: make dates accoring to scenario.tags.year
    this_ts = this_ts.sort(function(a, b) {
        return b - a
    });
    var dates = Array.apply(null, Array(this_ts.length)).map(function(_, i) {
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
            rangeselector: selectorOptions,
            rangeslider: {}
        },
        yaxis: {
            fixedrange: true
        }
    };
    layout_plotly.title = layout.title;


    var data_plotly = {type: 'scatter', mode: 'lines', line: {width: 0}, fill: 'tozeroy',
         x: dates};
    
    data_plotly.name = data.name;
    data_plotly.y = this_ts;
    data_plotly.fillcolor = data.color;

    data_plotly = [data_plotly];

    Plotly.newPlot(div, data_plotly, layout_plotly);
}
