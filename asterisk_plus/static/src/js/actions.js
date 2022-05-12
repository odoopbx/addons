/** @odoo-module **/

import {registry} from "@web/core/registry";
import {uid} from "web.session";
import {useService} from "@web/core/utils/hooks";

var personal_channel = 'asterisk_plus_actions_' + uid;
var common_channel = 'asterisk_plus_actions';

export const actionService = {
    dependencies: ["action", "notification", "rpc"],

    start(env, {action, notification, rpc}) {
        const legacyEnv = owl.Component.env;
        legacyEnv.services.bus_service.addChannel(personal_channel);
        legacyEnv.services.bus_service.addChannel(common_channel);
        legacyEnv.services.bus_service.onNotification(this, this.on_asterisk_plus_action);
        legacyEnv.services.bus_service.startPolling();

        this.notification = useService("notification");
    },

    on_asterisk_plus_action: function (action) {
        for (var i = 0; i < action.length; i++) {
            var {type, payload} = action[i];
            if (type == 'asterisk_plus_notify') {
                try {
                    this.asterisk_plus_handle_action(payload);
                } catch (err) {
                    console.log(err);
                }
            }
        }
    },

    asterisk_plus_handle_action: function (msg) {
        // console.log(msg)
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

    asterisk_plus_handle_open_record: function (message) {
        // console.log('Opening record form')
        this.do_action({
            'type': 'ir.actions.act_window',
            'res_model': message.model,
            'target': 'current',
            'res_id': message.res_id,
            'views': [[message.view_id, 'form']],
            'view_mode': 'tree,form',
        })
    },

    asterisk_plus_handle_reload_view: function (message) {
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

    asterisk_plus_handle_notify: function ({title, message, sticky, warning}) {
        // console.log({title, message, sticky, warning})
        if (warning == true)
            this.notification.notify({title, message, sticky, type: 'danger'})
        else
            this.notification.notify({title, message, sticky, type: 'warning'})
    },
}

registry.category("services").add("actionService", actionService);
