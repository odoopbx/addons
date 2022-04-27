odoo.define('asterisk_plus.console', function(require) {
    "use strict";

  var field_registry = require('web.field_registry');
  var basicFields = require('web.basic_fields');

  var ConsoleFormButton = basicFields.DebouncedField.extend({    
      // template: 'ServerCli',
      events: {},

      _render: function() {
        this._super();
        var self = this;
        var button = document.createElement('button');
        button.setAttribute('class', 'btn btn-info bt-sm');
        button.innerHTML = '<span class="fa fa-tv"/>';
        button.onclick = function(e) {
          window.open(self.value, 'Terminal', 
            'width=1024,height=900,top=10,left=10,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes');
        }
        // console.log(self.getParent().$el)
        self.$el[0].appendChild(button);
      },
    });

  var ConsoleTreeButton = basicFields.DebouncedField.extend({
      events: {},

      _render: function() {
        this._super();
        var self = this;
        var button = document.createElement('button');
        button.setAttribute('class', 'btn bt-sm');
        button.innerHTML = '<span class="fa fa-tv"/>';
        button.onclick = function(event) {
          event.stopPropagation();
          window.open(self.value, 'Terminal', 
            'width=1024,height=900,top=10,left=10,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes');
        }
        self.$el[0].appendChild(button);
      },
    });  

    field_registry.add('console_form_button', ConsoleFormButton);
    field_registry.add('console_tree_button', ConsoleTreeButton);
});    