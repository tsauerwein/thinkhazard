(function() {


  //
  // Main
  //


  var map = new ol.Map({
    target: 'map',
    interactions: [],
    controls: [],
    layers: [
      new ol.layer.Tile({
        source: new ol.source.Stamen({
          layer: 'watercolor'
        }),
        opacity: 0.5
      })
    ]
  });
  map.getView().fit(app.divisionBounds, map.getSize());

  var vectorLayer = addVectorLayer(map, app.mapUrl);

  if (app.leveltype < 3) {
    addSelectInteraction(map, vectorLayer);

    // change mouse cursor when over division
    map.on('pointermove', function(e) {
      var feature = map.forEachFeatureAtPixel(e.pixel, filterFn);
      map.getTargetElement().style.cursor = feature ? 'zoom-in' : '';

      $('#map .tooltip').empty().hide();
      if (feature) {
        $('#map .tooltip').show()
          .css({
            top: e.pixel[1] + 10,
            left: e.pixel[0] + 10
          })
          .html(feature.get('name'));
      }
    });

    // drill down
    map.on('click', function(e) {
      var feature = map.forEachFeatureAtPixel(e.pixel, filterFn);
      if (feature) {
        var code = feature.get('code');
        window.location = app.reportpageUrl.replace('__divisioncode__', code);
      }
    });
  }


  //
  // Functions
  //


  /**
   * @param {ol.Map} map
   * @param {string} url
   * @return {ol.layer.Vector}
   */
  function addVectorLayer(map, url) {
    var styleFn = function(feature) {
      var fillColors = getFillColors(0.5);
      var transparent = 'rgba(1, 1, 1, 0)';
      var fillStyle = new ol.style.Fill({
        color: fillColors[feature.get('hazardLevel')] || transparent
      });
      var styles = [
        new ol.style.Style({
          fill: fillStyle,
          stroke: new ol.style.Stroke({
            color: '#333',
            width: isSubDivision(feature) ? 0.5 : 1.5
          })
        })
      ];
      // More than one feature indicates that there are subdivision. We still
      // want to show the parent division but with no fill.
      if (layer.getSource().getFeatures().length > 1 &&
          !isSubDivision(feature)) {
        fillStyle.setColor(transparent);
      }
      return styles;
    };
    var layer = new ol.layer.Vector({
      style: styleFn,
      source: new ol.source.Vector({
        url: url,
        format: new ol.format.GeoJSON({
          defaultDataProjection: 'EPSG:3857'
        })
      })
    });
    map.addLayer(layer);
    return layer;
  }


  /**
   * @param {ol.Feature} feature
   * @return {?ol.Feature}
   */
  function filterFn(feature) {
    if (isSubDivision(feature)) {
      return feature;
    }
  }


  /**
   * @param {ol.Feature} feature
   * @return {boolean}
   */
  function isSubDivision(feature) {
    return feature.get('code') != app.divisionCode;
  }


  /**
   * @param {ol.Map} map
   * @param {ol.layer.Vector} layer
   * @return {ol.interaction.Select}
   */
  function addSelectInteraction(map, layer) {
    var fillColors = getFillColors(0.9);
    var fillStyle = new ol.style.Fill({
      color: ''
    });
    var styles = [
      new ol.style.Style({
        fill: fillStyle,
        stroke: new ol.style.Stroke({
          color: '#000000',
          width: 2
        })
      })
    ];
    var styleFn = function(feature) {
      var hazardLevel = feature.get('hazardLevel');
      var fillColor = hazardLevel in fillColors ?
          fillColors[hazardLevel] : 'rgba(1, 1, 1, 0.5)';
      fillStyle.setColor(fillColor);
      return styles;
    };
    var interaction = new ol.interaction.Select({
      layers: [layer],
      condition: ol.events.condition.pointerMove,
      style: styleFn,
      filter: isSubDivision
    });
    map.addInteraction(interaction);
    return interaction;
  }


  /**
   * @param {number} opacity
   * @return {Object.<string, Array.<number>>}
   */
  function getFillColors(opacity) {
    return {
      'HIG': [217, 31, 44, opacity],
      'MED': [213, 124, 39, opacity],
      'LOW': [224, 176, 37, opacity],
      'NPR': [142, 157, 146, opacity]
    };
  }

})();
