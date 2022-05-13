/** @odoo-module **/

import {registry} from "@web/core/registry";
import {uid} from "web.session";
import {useService} from "@web/core/utils/hooks";

var personal_channel = 'asterisk_plus_actions_' + uid;
var common_channel = 'asterisk_plus_actions';

export const actionService = {
    dependencies: ["action", "notification", "rpc"],

    start(env, {action, notification, rpc}) {
        this.action = action;
        const legacyEnv = owl.Component.env;
        legacyEnv.services.bus_service.addChannel(personal_channel);
        legacyEnv.services.bus_service.addChannel(common_channel);
        legacyEnv.services.bus_service.onNotification(this, this.on_asterisk_plus_action);
        legacyEnv.services.bus_service.startPolling();

        this.notification = useService("notification");
    },

    on_asterisk_plus_action: function (action) {
        console.log(action)
        for (var i = 0; i < action.length; i++) {
            try {
                var {type, payload} = action[i];
                if (typeof payload == 'string')
                    var payload = JSON.parse(payload)
                if (type == 'asterisk_plus_notify')
                    this.asterisk_plus_handle_notify(payload);
                else if (type == 'open_record')
                    this.asterisk_plus_handle_open_record(payload)
                else if (type == 'reload_view')
                    this.asterisk_plus_handle_reload_view(payload)
            }
            catch (e) { console.log(e) }
        }
    },

    asterisk_plus_handle_open_record: function (message) {
        // console.log('Opening record form')
        this.action.doAction({
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
        console.log('Reload')
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
