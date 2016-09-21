'use strict';

/* Grmbl. Apparently, this doesn't work. So until I figure out how to
 * dynamically patch the iD object from outside, this code get's commented out
 * and instead there will be functions adding our widgets to the iD editor.
 * These functions then have to be called in the iD editor's code in every
 * place, where we want to have those widgets.

(function () {
  var old_PresetList = window.iD.ui.PresetList; console.log("Overriding PresetList.");
  window.iD.ui.PresetList = function(context) {

    var result = old_PresetList(context);
    var old_presetList = result.presetList;

    console.log("Overriding presetList.");
    result.presetList = function(selection) {

      console.log("In custom presetList.");

      var result = old_presetList(selection);

      if (selection.selectAll('.inspector-body').length === 0) {
        selection.append('div').attr('class', 'inspector-body');
      };

      selection.selectAll('.inspector-body')[0]
        .insert('div', ':first-child')
        .attr('class', 'foobar fillL cf')
        .append('span')
        .style('margin-left', 'auto')
        .style('margin-right', 'auto')
        .style('border', '1px solid black')
        .html('FOOBAR!');

      return result;

    };

    return result;

  };

  window.iD.ui.PresetList.test_attribute = "_T_";

})();
*/

(function () {
var widgets = {};
var openmod = window.openmod || {};
openmod.sh = {widgets: widgets};

function first_or_new(selection, selector){
  if (selection.selectAll(selector).empty()) {
    selection.append('div').attr('class', selector);
  };
  return selection.selectAll(selector)[0];
};

function prepend(element, parent){
  return parent.insert(element, ':first-child');
};

widgets.scenarios = function (parent, context) {
  var outer = prepend('div', parent)
    .attr('class', 'foobar inspector-inner fillL cf')
    .append('span');
  outer.html('');
  var input = outer.append('input')
    .attr('class', 'value combobox-input')
    .attr('type', 'text')
    .attr('placeholder', 'Getting scenarios');
  outer.append('div').attr('class', 'combobox-caret');

  d3.xhr('/scenario')
    .on('load', function(xhr) {
      if (xhr.response === '') {
        input.attr('placeholder', 'Select a scenario');
      } else {
        var e = JSON.parse(xhr.response);
        prepend('span', outer).text('Selected scenario: ' + e.value);
        input.attr('placeholder', 'Change selected scenario');
      };
    })
    .send('GET');

  d3.xhr('/scenarios')
    .on('load', function(xhr){
      var data = JSON.parse(xhr.response);
      input.call(d3.combobox()
        .data(data)
        .minItems(1)
        .on('accept', function (e) {
          d3.xhr('/scenario/' + e.title)
            .on('load', function (_) {
              if (e.title === null){
                window.location.reload(true);
                return ;
              };
              context.enter(iD.modes.Select(context, ["r" + e.title]))
              window.location.reload(true);
        }).send('PUT')}));
      input.attr("defaultValue", data[0]);
    })
    .send('GET');

  return input;
};

window.openmod = openmod;
})();

