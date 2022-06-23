odoo.define('asterisk_plus.web_phone_core', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    const session = require('web.session');
    const SystrayMenu = require('web.SystrayMenu');
    const Widget = require('web.Widget');

    const bus = new owl.core.EventBus();

    const {Component, useState} = owl;
    const {xml} = owl.tags;

    class WebPhoneCore extends Component {
        static template = xml`
    <div  t-attf-class="{{state.isDisplay ? '' : 'o_hide'}} o_root_phone">
<!--Header-->
      <div class="o_header_phone">
        <div class="o_header_content">
          <i class="fa fa-phone" role="img"/>
          <div class="o_header_title">
            <b t-esc="title"/>
          </div>
          <div aria-label="Close" class="fa fa-close o_header_close" title="Close" t-on-click="_onClickClose"/>
        </div>
      </div>
<!--Keypad-->
      <div t-attf-class="{{state.isKeypad ? '' : 'o_hide'}} o_body_phone">
        <div class="o_phone_number_content">
          <input class="o_phone_number_input" type="tel" t-att-value="state.phone_number" readonly="readonly" placeholder="Enter the number..."/>
          <div aria-label="Backspace" class="fa fa-long-arrow-left o_phone_number_back" role="img" title="Backspace" t-on-click="_onClickBackSpace"/>
        </div>
        <div class="o_keypad">
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">1</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">2</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">3</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">4</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">5</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">6</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">7</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">8</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">9</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">*</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">0</button>
          <button class="o_keypad_button" t-on-click="_onClickKeypadButton">#</button>
        </div>
      </div>
<!--Dial panel-->
      <div t-attf-class="{{ !state.isKeypad and state.inCall and !state.isTransfer ? '' : 'o_hide' }} o_body_phone">
        <div class="o_phone_call_details">
          <t t-if="state.isPartner">
            <a t-att-href="state.partnerUrl" class="o_partner_link" >
              <img alt="Avatar" class="o_partner_avatar" t-if="state.partnerAvatar" t-attf-src="data:image/jpg;base64,{{ state.partnerAvatar }}"/>
              <span class="o_partner_name"><t t-esc="state.partnerName"/></span>
            </a>
          </t>
          <t t-else="">
            <span class="o_partner_name">
              <t t-esc="state.phone_number"/>
            </span>
          </t>
        </div>
      </div>
<!--Contacts-->
      <div t-attf-class="{{ !state.isKeypad and state.isContacts ? '' : 'o_hide' }} o_body_phone">
        <div class="o_phone_number_content">
          <input id="search_query" class="o_phone_number_input" placeholder="Enter the name or number..." t-att-value="state.search_query" t-on-keyup="_onSearchContact"/>
          <div aria-label="Clear" class="fa fa-times-circle o_phone_number_back" role="img" title="Clear" t-on-click="_onClickClearSearchContact"/>
        </div>
        <div class="o_dial_contact_list">
          <t t-if="state.contacts">
            <table class="o_contact_table">
              <t t-foreach="state.contacts" t-as="contact">
                <tr t-key="contact.id">
                  <td class="o_contact_avatar">
                    <img alt="Avatar" class="o_contact_avatar" t-attf-src="data:image/jpg;base64,{{ contact.image_128 }}"/>
                  </td>
                  <td class="o_contact_info">
                    <span><t t-esc="contact.name"/></span>
                    <t t-if="contact.phone">
                      <div>
                        <div class="fa fa-phone o_phone_number_back"/>
                        <span class="o_contact_phone"><t t-esc="contact.phone"/></span>
                      </div>
                    </t>
                    <t t-if="contact.mobile">
                      <div>
                        <div class="fa fa-mobile o_phone_number_back"/>
                        <span class="o_contact_phone"><t t-esc="contact.mobile"/></span>
                      </div>
                    </t>
                  </td>
                  <td class="o_contact_call_button">
                    <div style="display: flex;">
                      <div style="width: 40px; height: 30px;">
                        <t t-if="contact.mobile">
                          <t t-if="state.isTransfer">
                            <button aria-label="Call" title="Transfer" t-att-contact-phone="contact.mobile" t-on-click="_onClickMakeTransfer">
                              <i class="fa fa-mobile" t-att-contact-phone="contact.mobile"/>
                            </button>
                          </t>
                          <t t-else="">
                            <button aria-label="Call" title="Call" t-att-contact-phone="contact.mobile" t-on-click="_onClickContactCall">
                              <i class="fa fa-mobile" t-att-contact-phone="contact.mobile"/>
                            </button>
                          </t>
                        </t>
                      </div>
                      <t t-if="contact.phone">
                        <t t-if="state.isTransfer">
                          <button aria-label="Call" title="Transfer" t-att-contact-phone="contact.phone" t-on-click="_onClickMakeTransfer">
                            <i class="fa fa-phone" t-att-contact-phone="contact.phone"/>
                          </button>
                        </t>
                        <t t-else="">
                          <button aria-label="Call" title="Call" t-att-contact-phone="contact.phone" t-on-click="_onClickContactCall">
                            <i class="fa fa-phone" t-att-contact-phone="contact.phone"/>
                          </button>
                        </t>
                      </t>
                    </div>
                  </td>
                </tr>
              </t>
            </table>
          </t>
        </div>
      </div>
<!--Optional call buttons-->
      <div t-attf-class="{{ state.inCall and !state.inIncoming ? '' : 'o_hide' }} o_dial_panel o_optional_dial_panel_position">
        <button aria-label="Keypad" class="col-4" title="Keypad" t-on-click="_onClickKeypad">
          <i class="fa fa-keyboard-o"/>
        </button>
        <button aria-label="Transfer" class="col-4" title="Transfer" t-on-click="_onClickTransfer">
          <i class="fa fa-exchange"/>
        </button>
        <button aria-label="Mute" class="col-4" title="Mute" t-on-click="_onClickMute">
          <i t-attf-class="fa {{ state.isMute ? 'fa-microphone-slash' : 'fa-microphone' }}"/>
        </button>
      </div>
<!--Call buttons-->
      <div  t-attf-class="{{ state.inIncoming ? 'o_hide' : '' }} o_dial_panel o_dial_panel_position">
        <button aria-label="Contacts" t-attf-class="{{ state.inCall ? 'o_hide' : '' }} col-6" title="Contacts" t-on-click="_onClickContacts">
          <i class="fa fa-address-book"/>
        </button>
        <button aria-label="Call" t-attf-class="{{ state.inCall ? 'o_hide' : '' }} col-6" title="Call" t-on-click="_onClickCall">
          <i class="fa fa-phone"/>
        </button>
        <button aria-label="End Call" t-attf-class="{{ state.inCall ? '' : 'o_hide' }} col-6" title="End Call" t-on-click="_onClickEndCall">
          <i class="fa fa-phone"/>
        </button>
      </div>
<!--Incoming buttons-->
      <div t-attf-class="{{ state.inIncoming ? '' : 'o_hide' }} o_dial_panel o_dial_panel_position">
        <button aria-label="Reject call" class="col-6" title="Reject">
          <i class="fa fa-phone reject-call" t-on-click="_onClickRejectIncoming"/>
        </button>
        <button aria-label="Take call" class="col-6" title="Accept" t-on-click="_onClickAcceptIncoming">
          <i class="fa fa-phone"/>
        </button>
      </div>
    </div>
    `

        constructor() {
            super(...arguments);
            this.title = 'Web Phone';
            this.state = useState({
                isActive: true,
                isDisplay: false,
                isMute: false,
                isKeypad: true,
                isContacts: false,
                isPartner: false,
                isTransfer: false,
                inCall: false,
                inIncoming: false,
                phone_number: '',
                search_query: '',
                partnerName: '',
                partnerAvatar: '',
                partnerUrl: "",
                raw_contacts: [],
                contacts: [],
            });
            this.user = this.env.session.uid;
            this.web_phone_configs = {
                web_phone_sip_protocol: '',
                web_phone_sip_proxy: '',
                web_phone_sip_secret: '',
                web_phone_sip_user: '',
                web_phone_stun_server: '',
                web_phone_websocket: '',
            };

            this.notify = new Notification(this);
            this.notify.mount(document.body);

            bus.on('web_phone_toggle_display', this, function (...args) {
                if (this.state.isActive) {
                    this.toggleDisplay();
                } else {
                    this.notify.add('Missing configs! Check "User / Preferences"!')
                }
            });
        }

        async willStart() {
            const [web_phone_pbx_configs] = await this.env.services.rpc({
                model: "asterisk_plus.settings",
                method: "search_read",
                fields: [
                    'web_phone_sip_protocol',
                    'web_phone_sip_proxy',
                    'web_phone_websocket',
                    'web_phone_stun_server',
                ],
                limit: 1,
            });
            if (web_phone_pbx_configs) {
                delete web_phone_pbx_configs['id'];
                Object.assign(this.web_phone_configs, web_phone_pbx_configs);
            }

            const [web_phone_user_configs] = await this.env.services.rpc({
                model: "res.users",
                method: "search_read",
                domain: [
                    ['id', '=', this.user],
                ],
                fields: [
                    'web_phone_sip_user',
                    'web_phone_sip_secret',
                ],
                limit: 1,
            });
            if (web_phone_user_configs) {
                delete web_phone_user_configs['id'];
                Object.assign(this.web_phone_configs, web_phone_user_configs);
            }

            this.dialPlayer = document.createElement("audio");
            this.dialPlayer.volume = 1;
            this.dialPlayer.setAttribute("src", "/asterisk_plus/static/src/sounds/outgoing-call2.mp3");

            this.incomingPlayer = document.createElement("audio");
            this.incomingPlayer.volume = 1;
            this.incomingPlayer.setAttribute("src", "/asterisk_plus/static/src/sounds/incomingcall.mp3");

            this._userAgent = null;
            this.session = null;
            this.get_contacts();
        }

        mounted() {
            for (let key in this.web_phone_configs) {
                if (!this.web_phone_configs[key]) {
                    console.error(`Missing config: "${key}" for Web Phone!`);
                    this.state.isActive = false;
                }
            }
            this._initUserAgent();
        }

        _initUserAgent() {
            const self = this;
            if (!self.state.isActive) {
                return
            }

            const {
                web_phone_sip_user,
                web_phone_sip_secret,
                web_phone_sip_proxy,
                web_phone_sip_protocol,
                web_phone_websocket,
                web_phone_stun_server
            } = self.web_phone_configs;

            try {
                self.socket = new JsSIP.WebSocketInterface(web_phone_websocket);
            } catch (e) {
                console.error(e);
                this.state.isActive = false;
                return
            }
            self.socket.via_transport = web_phone_sip_protocol;
            self.configuration = {
                sockets: [self.socket],
                ws_servers: web_phone_websocket,
                realm: 'OdooPBX',
                display_name: web_phone_sip_user,
                uri: `sip:${web_phone_sip_user}@${web_phone_sip_proxy}`,
                password: web_phone_sip_secret,
                contact_uri: `sip:${web_phone_sip_user}@${web_phone_sip_proxy}`,
                register: true,
                stun_server: web_phone_stun_server,
            };
            self._userAgent = new JsSIP.UA(self.configuration);
            // JsSIP.debug.enable('JsSIP:*');
            JsSIP.debug.disable('JsSIP:*');
            self._userAgent.start();

            self._userAgent.on('connected', function (e) {
                console.log('SIP Connected');
            });

            // HANDLE RTCSession
            self._userAgent.on("newRTCSession", function ({session}) {
                if (session.direction === "outgoing") {
                    session.connection.addEventListener("track", (e) => {
                        const remoteAudio = document.createElement('audio');
                        remoteAudio.srcObject = e.streams[0];
                        remoteAudio.play();
                    });
                }

                if (session.direction === "incoming") {
                    session.on('peerconnection', function (data) {
                        data.peerconnection.addEventListener('addstream', function (e) {
                            const remoteAudio = document.createElement('audio');
                            remoteAudio.srcObject = e.stream;
                            remoteAudio.play();
                        });
                    });
                    if (self.state.inCall) {
                        session.terminate();
                        return;
                    }
                    self.session = session;
                    if (!self.state.isDisplay) {
                        self.toggleDisplay();
                    }
                    self.state.inIncoming = true;
                    self.startCall();
                    const phone_number = self.session._request.from._uri._user
                    self.state.phone_number = phone_number;
                    self.get_partner(phone_number);

                    self.incomingPlayer.play();
                    self.incomingPlayer.loop = true;

                    // incoming call here
                    self.session.on("accepted", function (data) {
                        // console.log('incoming -> accepted: ', data);
                        self.incomingPlayer.pause();
                        self.incomingPlayer.currentTime = 0;
                    });
                    self.session.on("ended", function (data) {
                        // console.log('incoming -> ended: ', data);
                        self.notify.add(data.cause);
                        self.endCall();
                    });
                    self.session.on("failed", function (data) {
                        // console.log('incoming -> failed: ', data);
                        self.notify.add(data.cause);
                        self.endCall();
                        self.incomingPlayer.pause();
                        self.incomingPlayer.currentTime = 0;
                    });
                }
            });

        }

        toggleDisplay() {
            this.state.isDisplay = !this.state.isDisplay;
        }

        _onClickClose(ev) {
            this.toggleDisplay();
        }

        _onClickKeypadButton(ev) {
            if (this.state.inCall) {
                this.session.sendDTMF(ev.target.textContent);
            } else {
                this.state.phone_number += ev.target.textContent;
            }
        }

        _onClickBackSpace(ev) {
            this.state.phone_number = this.state.phone_number.slice(0, -1);
        }

        _onSearchContact(ev) {
            this.state.search_query = ev.target.value;
            this.searchContact();
        }

        searchContact() {
            const search_query = this.state.search_query;
            let contacts = this.state.raw_contacts.filter(o => {
                return o.name.toLowerCase().includes(search_query.toLowerCase()) | (o.mobile ? o.mobile.includes(search_query.toLowerCase()) : false) | (o.phone ? o.phone.includes(search_query.toLowerCase()) : false)
            });
            this.state.contacts = contacts;
        }

        _onClickClearSearchContact(ev) {
            this.state.search_query = '';
            this.searchContact();
        }

        _onClickCall(ev) {
            if (this.state.phone_number) {
                this.startCall();
                this.makeCall(this.state.phone_number);
            } else {
                this.notify.add("The phonecall has no number");
            }
        }

        _onClickContactCall(ev) {
            this.startCall();
            this.makeCall(ev.target.attributes['contact-phone'].value);
        }

        _onClickContacts(ev) {
            this.state.isKeypad = !this.state.isKeypad;
            this.state.isContacts = !this.state.isContacts;
        }

        _onClickKeypad(ev) {
            this.state.isKeypad = !this.state.isKeypad;
        }

        _onClickTransfer(ev) {
            this.state.isTransfer = !this.state.isTransfer;
            this.state.isContacts = !this.state.isContacts;
            this.state.isKeypad = false;
        }

        _onClickMakeTransfer(ev) {
            this.endCall();
            this.session.refer(ev.target.attributes['contact-phone'].value);
        }

        _onClickMute(ev) {
            if (!this.state.isMute) {
                this.session.mute();
            } else {
                this.session.unmute();
            }
            this.state.isMute = !this.state.isMute;
        }

        _onClickEndCall(ev) {
            this.session.terminate();
            this.endCall()
        }

        _onClickAcceptIncoming(ev) {
            this.session.answer();
            this.state.inIncoming = false;
        }

        _onClickRejectIncoming(ev) {
            this.session.terminate();
            this.state.inIncoming = false;
            this.endCall();
        }

        makeCall(phone_number) {
            const self = this;
            self.get_partner(phone_number);

            self.eventHandlers = {
                'connecting': function (data) {
                    // console.log('connecting: ', data)
                    self.dialPlayer.play();
                    self.dialPlayer.loop = true;
                },
                'confirmed': function (data) {
                    // console.log('confirmed: ', data);
                },
                'accepted': function (data) {
                    // console.log('accepted: ', data)
                    self.dialPlayer.pause();
                    self.dialPlayer.currentTime = 0;
                },
                'ended': function (data) {
                    // console.log('ended: ', data);
                    self.notify.add(data.cause);
                    self.endCall();
                    self.dialPlayer.pause();
                    self.dialPlayer.currentTime = 0;
                },
                'failed': function (data) {
                    // console.log('failed: ', data);
                    self.notify.add(data.cause);
                    self.endCall();
                    self.dialPlayer.pause();
                    self.dialPlayer.currentTime = 0;
                }
            };

            var options = {
                'eventHandlers': self.eventHandlers,
                'mediaConstraints': {'audio': true, 'video': false}
            };
            self.session = self._userAgent.call(`sip:${phone_number}`, options);
        }

        startCall() {
            this.state.inCall = true;
            this.state.isDisplay = true;
            this.state.isKeypad = false;
            this.state.isContacts = false;
        }

        endCall() {
            this.state.inCall = false;
            this.state.inIncoming = false;
            this.state.isKeypad = true;
            this.state.isTransfer = false;
            this.state.isContacts = false;
            this.state.isMute = false;
            this.state.isPartner = false;
            this.state.phone_number = '';
        }

        async get_partner(phone_number) {
            const [partner] = await this.env.services.rpc({
                model: "res.partner",
                method: "search_read",
                domain: [
                    '|', ['phone', '=', phone_number], ['mobile', '=', phone_number],
                ],
                limit: 1,
            });
            if (partner) {
                this.state.isPartner = true;
                this.state.partnerAvatar = partner.image_128;
                this.state.partnerName = partner.display_name;
                this.state.partnerUrl = this.get_partner_url(partner.id);
            } else {
                this.state.isPartner = false;
            }
        }

        get_partner_url(partner_id) {
            return `${this.env.session.server}/web#id=${partner_id}&model=res.partner&view_type=form`;
        }

        async get_contacts() {
            const contacts = await this.env.services.rpc({
                model: "res.partner",
                method: "search_read",
                domain: [
                    '|', ['phone', '!=', ''], ['mobile', '!=', ''],
                ],
                fields: ['id', 'name', 'email', 'phone', 'mobile', 'image_128'],
            });
            this.state.contacts = contacts;
            this.state.raw_contacts = contacts;
        }
    }


    const SystrayButton = Widget.extend({
        name: 'asterisk_plus_web_phone_menu',
        template: 'asterisk_plus.web_phone_menu',
        events: {
            'click': '_onClick',
        },

        async willStart() {
            const _super = this._super.bind(this, ...arguments);
            const isEmployee = await session.user_has_group('base.group_user');
            if (!isEmployee) {
                return Promise.reject();
            }
            return _super();
        },

        _onClick(ev) {
            ev.preventDefault();
            bus.trigger("web_phone_toggle_display");
        },
    });

    class Notification extends Component {
        static template = xml`
    <div id="alert" style="position: absolute; top: 60px; right: 20px; z-index: 1000; overflow: unset">
      <t t-foreach="state.messages" t-as="message">
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" style="opacity: 1; background-color: #ffecb5; width: 350px; min-width: 350px">
          <div class="toast-header">
            <i aria-label="Toggle Web Phone" class="fa fa-fw fa-phone" role="img"></i>
            <strong class="mr-auto">Web Phone</strong>
          </div>
          <div class="toast-body">
            <t t-esc="message"/>
          </div>
        </div>
      </t>
    </div>
    `

        constructor() {
            super(...arguments);
            this.state = useState({
                messages: [],
            });
        }

        add(message) {
            this.state.messages.push(message)
            setTimeout(() => this.state.messages.shift(), 1000)
        }
    }

    ajax.rpc('/web/dataset/call_kw/asterisk_plus.settings', {
        "model": "asterisk_plus.settings",
        "method": "search_read",
        "args": [[], ['is_web_phone_enabled']],
        "kwargs": {'limit': 1},
    }).then(function ([res]) {
        if (res) {
            if (res.is_web_phone_enabled) {
                ajax.rpc('/web/dataset/call_kw', {
                    model: "res.users",
                    method: "search_read",
                    args: [[['id', '=', session.uid]], ['web_phone_sip_user', 'web_phone_sip_secret']],
                    kwargs: {'limit': 1},
                }).then(function ([web_phone_user_configs]) {
                    if (web_phone_user_configs.web_phone_sip_user && web_phone_user_configs.web_phone_sip_secret) {
                        owl.utils.whenReady().then(() => {
                            const app = new WebPhoneCore(this);
                            app.mount(document.body);
                        });

                        SystrayMenu.Items.push(SystrayButton);
                    } else {
                        console.error('Missing Web Phone settings!\nCheck User / Preferences!');
                    }
                });
            }
        }
    });

    return SystrayButton
});
