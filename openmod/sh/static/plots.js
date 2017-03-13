function makeBarPlot(hub_name) {

    result = getResults(scenario_db_id, hub_name, function(data) {

            if (data == false) {
                document.getElementById("Tab4").innerHTML = 'No results in db';
            }
            else {
                var x_vals = [];
                var y_vals = [];

		var import_sum = 0;
		var export_sum = 0;

                $.each(data, function(key, value) {
                    //console.log(key, value);
                    $.each(value['production'], function(comp_name, production) {
                        x_vals.push(comp_name);
                        y_vals.push(production);
                        //console.log(comp_name, production);
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

                var layout =  {title: 'Summed electricity production',
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
                }
            ];

            Plotly.newPlot('bar_plot', data, layout);
          }

    });
}

function makeHeatmapPlot() {
    var dates = Array.apply(null, Array(8760)).map(function(_, i) {
        return new Date(i * 3600 * 1000);
    });
    var heat = scenario.children_dict.kiel_demand_heat.sequences.load_profile;
    heat = heat.map(function(i) {
        return i * scenario.children_dict.kiel_demand_heat.tags.amount
    });


    var data = []

    for (var i = 0; i < 24; i++) {
        data[i] = []
        for (var j = 0; j < 365; j++) {
            data[i].push(heat[j * 24 + i])
        }
    }

    var layout = {
        title: 'Heat demand MW in Kiel',
        axis: {
            title: 'Day of the year'
        },
        yaxis: {
            title: 'Hour of the day'
        }
    };

    var data = [{
        z: data,
        type: 'heatmap'
    }];

    Plotly.newPlot('heatmap_plot', data, layout);
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
        Plotly.newPlot('timeseries_plot', data, layout);
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
        Plotly.newPlot('timeseries_plot', data, layout);
    }
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

    // start the map in South-East England
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
    var bars = ['installed_power_solar', 'installed_power_wind'];
    bars.forEach(function(b) {
        var l = lookup[b];
        barBottom = l.pos;
        barTop = [l.pos[0] + scenario.children_dict[l.child].tags[l.tag] / 100.0, l.pos[1]];
        var line = L.polyline([barBottom, barTop], {
            color: l.color,
            weight: 10,
            lineCap: 'butt'
        }).addTo(map);
    });
}
