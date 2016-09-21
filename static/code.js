$(document).ready(function() {
  $.ajax({ url: "series",
           success: function (d, _, _) {$.plot($("#timeseries-plot"), d);},
           dataType: "json"});

  var fl = ol.proj.transform([ 9.448389, 54.794287], 'EPSG:4326', 'EPSG:3857');
  var md = ol.proj.transform([11.618492, 52.117532], 'EPSG:4326', 'EPSG:3857');

  var map = new ol.Map({
    target: 'map',
    layers: [
      new ol.layer.Tile({source: new ol.source.OSM()})
    ],
    view: new ol.View({ center: md, zoom: 4 })
  });

  var md_marker = new ol.Overlay({
    element: $('#marker').clone().attr("id", "md_marker"),
    positioning: "center-center",
    position: md });
  var md_label = new ol.Overlay({
    element: $('#label').clone().attr("id", "md_label").text("Magdeburg"),
    positioning: "bottom-center",
    position: md });
  var fl_marker = new ol.Overlay({
    element: $('#marker').clone().attr("id", "fl_marker"),
    positioning: "center-center",
    position: fl });
  var fl_label = new ol.Overlay({
    element: $('#label').clone().attr("id", "md_label").text("Flensburg"),
    positioning: "bottom-center",
    position: fl });

  map.addOverlay(md_marker);
  map.addOverlay(md_label);
  map.addOverlay(fl_marker);
  map.addOverlay(fl_label);

});

