/** @odoo-module **/

import {registry} from "@web/core/registry";
import {uid} from "web.session";

var personal_channel = 'asterisk_plus_actions_' + uid;
var common_channel = 'asterisk_plus_actions';

export const pbxActionService = {
    dependencies: ["action", "notification"],

    start(env, {action, notification}) {
        this.bus = env.bus;
        this.action = action;
        this.notification = notification;

        const legacyEnv = owl.Component.env;
        legacyEnv.services.bus_service.addChannel(personal_channel);
        legacyEnv.services.bus_service.addChannel(common_channel);
        legacyEnv.services.bus_service.onNotification(this, this.on_asterisk_plus_action);
        legacyEnv.services.bus_service.startPolling();
    },

    on_asterisk_plus_action: function (action) {
        for (var i = 0; i < action.length; i++) {
            try {
                var {type, payload} = action[i];
                if (typeof payload == 'string')
                    payload = JSON.parse(payload)
                if (type == 'asterisk_plus_notify')
                    this.asterisk_plus_handle_notify(payload);
                else if (type == 'open_record')
                    this.asterisk_plus_handle_open_record(payload)
                else if (type == 'reload_view')
                    this.asterisk_plus_handle_reload_view(payload)
            } catch (e) {
                console.log(e)
            }
        }
    },

    asterisk_plus_handle_open_record: function (message) {
        // console.log('Opening record form')
        let action = this.action.currentController.action
        if (action.res_model == 'asterisk_plus.call') {
            this.action.doAction({
            'type': 'ir.actions.act_window',
            'res_model': message.model,
            'target': 'current',
            'res_id': message.res_id,
            'views': [[message.view_id, 'form']],
            'view_mode': 'tree,form',
            })
        }
    },

    asterisk_plus_handle_reload_view: function (message) {
        const action = this.action.currentController.action

        if (action.res_model != message.model) {
            // console.log('Not message model view')
            return
        }

        this.bus.trigger("ROUTE_CHANGE");
    },

    asterisk_plus_handle_notify: function ({title, message, sticky, warning}) {
        if (warning == true)
            this.notification.add(message, {title, sticky, type: 'danger', messageIsHtml: true})
        else
            this.notification.add(message, {title, sticky, type: 'warning', messageIsHtml: true})
    },
}

registry.category("services").add("pbxActionService", pbxActionService);