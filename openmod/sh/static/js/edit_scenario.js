function initPage(region_plot_id, timeseries_plot_id, region_plot_json, timeseries_plot_json) {
	var currentSortStatus = false;
	// Get the element with id="defaultOpen" and click on it
	document.getElementById("defaultOpen").click();
	makeRegionPlot(0, region_plot_id, region_plot_json);
	makeTimeseriesPlot(timeseries_plot_id, timeseries_plot_json);


	/**
	 * [initClickListener description]
	 * 
	 */
	//(function initClickListener() {
		d3.select("#solor_range_slider").on("change", function(){
			console.log(region_plot_id);
			console.log(this.value);
			updateValue(this.value, installed_power_solar, region_plot_id, region_plot_json);
		});
		d3.select("#wind_range_slider").on("change", function(){
			updateValue(this.value, installed_power_wind, region_plot_id, region_plot_json);
		});

		d3.select("#sortButton").on("click", function() {
			resortDataSet(timeseries_plot_id, timeseries_plot_json, currentSortStatus);
			this.innerHTML = currentSortStatus ? "Sort by Y" : "Sort by date";
			currentSortStatus = !currentSortStatus;
		})
	//})()
}

function updateValue(newValue, slider_id, plot_id, region_plot_json) {
	showValue(newValue, slider_id);
	makeRegionPlot(newValue, plot_id, region_plot_json);
}

function showValue(newValue, slider_id) {
	console.log(newValue);
	slider_id.innerHTML = newValue;
}

function makeRegionPlot(newValue, plot_id, graph) {
	//graph.data[4]['lat'][1]=graph.data[4]['lat'][0]+newValue/100.0;
	Plotly.newPlot(plot_id, // the ID of the div, created above
		graph.data,
		graph.layout || {});
}

function makeTimeseriesPlot(plot_id, graph) {
	Plotly.newPlot(plot_id,
		graph.data,
		graph.layout || {});

	console.log("graph.data");
	console.log(graph.data);	
}

function changeDataToArray(data) {
	var newData = [];
	for (var i = 0; i < data.y.length; i++) {
		newData[i] = {
			x: data.x[i],
			y: data.y[i]
		};
	}

	return newData;
}

function resortDataSet(timeseries_id, timeseries_plot_json, sortStatus) {
	// 
	if (!sortStatus) {
		var data = timeseries_plot_json.data[0];
		var sortData = changeDataToArray(data);

		sortData.sort(function(a, b) {
			if (a.y < b.y) {
				return 1;
			} else if (a.y > b.y) {
				return -1;
			}
			return 0;
		});

		var sortedData = {
			layout: {
				xaxis: {
					type: 'category'
				}
			},
			data: [{
				type: "lines",
				x: [],
				y: []
			}]
		};
		for (var i = 0; i < sortData.length; i++) {
			sortedData.data[0].x[i] = sortData[i].x;
			sortedData.data[0].y[i] = sortData[i].y;
		}
		makeTimeseriesPlot(timeseries_id, sortedData);
	}
	else {
		makeTimeseriesPlot(timeseries_id, timeseries_plot_json);
	}
}
function newScenario(scenario) {
 console.log(scenario);
 scenario['name'] = prompt("New name", scenario['name']);
 console.log(scenario);
}
