$(document).ready(function() {
  function time(label, f) {
    console.log(label + ".");
    var then = Date.now();
    result = f();
    console.log(label + ": " + ((then - Date.now()) / 1000) + "s");
    return result;
  };

  $.ajax({ url: "series",
           success: function (d, _, _) {$.plot($("#timeseries-plot"), d);},
           dataType: "json"});

  var popup = { close: $('#close-popup'), content: $('#popup-content'),
                container: $('#popup') };
  var overlay = new ol.Overlay({ element: popup.container.get(0),
                                 autoPan: false });
  popup.close.on('click', function (e) {
    overlay.setPosition(undefined);
    popup.close.blur();
    return false;
  });

  var map = new ol.Map({
    target: 'map',
    layers: [
      new ol.layer.Tile({source: new ol.source.Stamen({layer: 'watercolor'})})
    ],
    overlays: [overlay],
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
                 {source: new ol.source.Vector({features: features}),
                  style: new ol.style.Style({image: new ol.style.Icon({
                    src: "/static/dot.svg",
                    anchorXUnits: 'pixel',
                    anchorYUnits: 'pixel',
                    scale: 1
                  })})});
             // I wasn't able to get ol.interaction.Select to work the way it
             // should so I settlet for this.
             map.on("click", function(e) {
               map.forEachFeatureAtPixel(e.pixel, function (feature, layer) {
                 var position = feature.getGeometry().getCoordinates();
                 var content = $(
                     '<table><tr><th>EEG ID</th><th>capacity</th></tr></table>');
                 $.each(feature.get("plants"), function (i, x) {
                   var button = $(
                       '<a class="plant-id" href="#">' + x.id + '</a>' );
                   content.append($('<tr></tr>').append(
                         $('<td></td>').append(button)).append(
                         $("<td>" + x.capacity + "</td>")));
                 });
                 popup.content.html(content);
                 overlay.setPosition(position);
               })});
             map.addLayer(layer, projections);
           },
           dataType: "json"});

});

