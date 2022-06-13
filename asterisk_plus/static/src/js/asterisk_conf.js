odoo.define('asterisk_plus.asterisk_conf_widget', function (require) {
  "use strict";

  var field_registry = require('web.field_registry');
  var basicFields = require('web.basic_fields');

  var AsteriskConfField = basicFields.DebouncedField.extend({
    template: 'AsteriskConf',
    cssLibs: [
      "/asterisk_plus/static/lib/codemirror/lib/codemirror.css",
      "/asterisk_plus/static/lib/codemirror/theme/blackboard.css",
      "/asterisk_plus/static/lib/codemirror/addon/scroll/simplescrollbars.css",
      "/asterisk_plus/static/lib/codemirror/addon/scroll/simplescrollbars.css"
    ],
    jsLibs: [
      '/asterisk_plus/static/lib/codemirror/lib/codemirror.js',
      [
        '/asterisk_plus/static/lib/codemirror/mode/asterisk/asterisk.js',
        '/asterisk_plus/static/lib/codemirror/addon/display/autorefresh.js',
        '/asterisk_plus/static/lib/codemirror/addon/scroll/simplescrollbars.js',
      ]
    ],
    events: {},

    _formatValue: function (value) {
        return this._super.apply(this, arguments) || '';
    },

    _getValue: function () {
        return this.myCodeMirror.getValue();
    },

    _render: function (node) {
      var self = this      
      if (! self.myCodeMirror) {

        setTimeout(function() {
          self.myCodeMirror = CodeMirror(
            function(elt) { self.$el[0].parentNode.replaceChild(elt, self.$el[0]); },
            {
              'mode': 'asterisk',
              'autofocus': true,
              'autoRefresh': true,
              'theme': 'blackboard',
              'scrollbarStyle': 'overlay',
            }
          );
          // self.myCodeMirror.setSize(null, 500);
          self.myCodeMirror.setValue(self._formatValue(self.value));
          if (self.mode === 'edit') {
            self.myCodeMirror.setOption('readOnly', false);
            self.myCodeMirror.on("change", self._doDebouncedAction.bind(self));
            self.myCodeMirror.on("blur", self._doAction.bind(self));
          }
          if (self.mode === 'readonly') self.myCodeMirror.setOption('readOnly', true);
        }, 0.1);
      }
    },
  });

  field_registry.add('asterisk_conf', AsteriskConfField);

});
