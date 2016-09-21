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
             var pped = JSON.stringify(d, null, 2);
             var dom =
               "<div><p>JSON for Plants as returned per the \"/plants\" URI:" +
               "</p><pre>" + pped + "</pre></div>";
             $("#debug").append(dom);
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
                 console.log("Clicked: " + feature);
               })});
             map.addLayer(layer, projections);
           },
           dataType: "json"});

});

