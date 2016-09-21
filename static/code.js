$(document).ready(function() {
  $.ajax({ url: "series",
           success: function (d, _, _) {$.plot($("#timeseries-plot"), d);},
           dataType: "json"});

  var map = new ol.Map({
    target: 'map',
    layers: [
      new ol.layer.Tile({source: new ol.source.OSM()})
    ],
    view: new ol.View({
      center: ol.proj.transform([11.618492, 52.117532],
                                'EPSG:4326', 'EPSG:3857'),
      zoom: 4
    })
  });

  var marker = new ol.Overlay({
    element: document.getElementById('marker'),
    position: ol.proj.transform([11.618492, 52.117532],
                                'EPSG:4326', 'EPSG:3857'),
  });

  map.addOverlay(marker);

});

