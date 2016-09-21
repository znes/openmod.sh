$(document).ready(function() {
  $.ajax({ url: "series",
           success: function (d, _, _) {$.plot($("#timeseries-plot"), d);},
           dataType: "json"});

  var map = new ol.Map({
    target: 'map',
    layers: [
      new ol.layer.Tile({source: new ol.source.OSM()})
    ],
    view: new ol.View({ // Center the viewport somewhere around the middle of SH.
                        center: ol.proj.transform([9.78, 54.17],
                                                  'EPSG:4326', 'EPSG:3857'),
                        zoom: 7 })
  });


  $.ajax({ url: "plants-json",
           success: function (d, _, _) {
             var gjs = new ol.format.GeoJSON;
             var projections = {dataProjection: 'EPSG:4326',
                                featureProjection: 'EPSG:3857'};
             var features = gjs.readFeatures(d, projections);
             var layer = new ol.layer.Vector(
                 {source: new ol.source.Vector({features: features})});
             map.addLayer(layer, projections);
           },
           dataType: "json"});

});

