odoo.define("asterisk_plus.actions", function (require) {
    "use strict";
  
    var WebClient = require('web.WebClient');
    var ajax = require('web.ajax');
    var utils = require('mail.utils');
    var session = require('web.session');
    var personal_channel = 'asterisk_plus_actions_' + session.uid;
    var common_channel = 'asterisk_plus_actions';

    WebClient.include({
        start: function() {
            this._super()
            let self = this
            ajax.rpc('/web/dataset/call_kw/asterisk_plus', {
                    "model": "asterisk_plus.user",
                    "method": "has_asterisk_plus_group",
                    "args": [],
                    "kwargs": {},            
            }).then(function (res) {
              if (res == true) {
                ajax.rpc('/web/dataset/call_kw/res.users', {
                        "model": "res.users",
                        "method": "get_pbx_user_settings",
                        "args": [session.uid],
                        "kwargs": {},
                }).then(function (settings) {
                  console.log(settings)
                })
                // Start polling
                self.call('bus_service', 'addChannel', personal_channel);
                self.call('bus_service', 'addChannel', common_channel);
                self.call('bus_service', 'onNotification', self,
                          self.on_asterisk_plus_action)
                // console.log('Listening on Asterisk Plus actions')
              }
            })
        },

        on_asterisk_plus_action: function (action) {
          for (var i = 0; i < action.length; i++) {
             var ch = action[i][0]
             var msg = action[i][1]
             if (ch == personal_channel || ch == common_channel) {
                 try {
                  this.asterisk_plus_handle_action(msg)
                }
                catch(err) {console.log(err)}
             }
           }
        },

        asterisk_plus_handle_action: function(msg) {
          console.log(msg)
          if (typeof msg == 'string')
            var message = JSON.parse(msg)
          else
            var message = msg
          // Check if this is a reload action.
          if (message.action == 'reload_view') {
            return this.asterisk_plus_handle_reload_view(message)
          }
          // Check if this is a notification action
          else if (message.action == 'notify') {
            return this.asterisk_plus_handle_notify(message)
          }
          // Check if it a open record action
          else if (message.action == 'open_record') {
            return this.asterisk_plus_handle_open_record(message) 
          }
        },

        asterisk_plus_handle_open_record: function(message) {
          // console.log('Opening record form')
          var controller = this.action_manager.getCurrentController()
          if (controller.widget.modelName == 'asterisk_plus.call') {
            this.do_action({
              'type': 'ir.actions.act_window',
              'res_model': message.model,
              'target': 'current',
              'res_id': message.res_id,
              'views': [[message.view_id, 'form']],
              'view_mode': 'tree,form',
              })
            }
        },

        asterisk_plus_handle_reload_view: function(message) {
          var action = this.action_manager && this.action_manager.getCurrentAction()
          if (!action) {
              // console.log('Action not loaded')
              return
          }
          var controller = this.action_manager.getCurrentController()
          if (!controller) {
              // console.log('Controller not loaded')
              return
          }
          if (controller.widget.modelName != message.model) {
              // console.log('Not message model view')
              return
          }
          // console.log('Reload')
          controller.widget.reload()
        },

        asterisk_plus_handle_notify: function(message) {
          console.log(message)
          if (message.warning == true)
            this.do_warn(message.title, message.message, message.sticky)
          else
            this.do_notify(message.title, message.message, message.sticky)
      },

    })
})
