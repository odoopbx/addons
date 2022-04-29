odoo.define('support_button', function () {
    "use strict";
    /**
     * @todo: add configs
     * @support_sip_user
     * @support_sip_secret
     * @support_exten
     * @support_sip_proxy
     * @support_sip_protocol
     * @support_websocket
     */
    const support_sip_user = '';
    const support_sip_secret = '';
    const support_exten = '';
    const support_sip_proxy = '';
    const support_sip_protocol = '';
    const support_websocket = '';

    let soundPlayer = document.createElement("audio");
    soundPlayer.volume = 1;
    soundPlayer.setAttribute("src", "/asterisk_plus/static/src/sounds/outgoing-call2.mp3");

    var callSession = null;
    var supportPhone = null;
    var options = null;
    var initTalkButtonText = null;

    let init = false;

    document.callSupport = function () {
        var support_button = document.getElementById('support_button');


        if (!init) {
            init = true;

            initTalkButtonText = support_button.innerText;
            var socket = null;
            try {
                socket = new JsSIP.WebSocketInterface(`${support_websocket}`);
            } catch (e) {
                console.error(e);
                return;
            }

            socket.via_transport = support_sip_protocol;
            var configuration = {
                sockets: [socket],
                ws_servers: `${support_websocket}`,
                realm: 'OdooPBX',
                display_name: `${support_sip_user}`,
                uri: `sip:${support_sip_user}@${support_sip_proxy}`,
                password: `${support_sip_secret}`,
                contact_uri: `sip:${support_sip_user}@${support_sip_proxy}`,
                register: false,
            };
            supportPhone = new JsSIP.UA(configuration);
            // JsSIP.debug.enable('JsSIP:*');
            // JsSIP.debug.disable('JsSIP:*');
            supportPhone.start();

            supportPhone.on("newRTCSession", function ({session}) {
                if (session.direction === "outgoing") {
                    session.connection.addEventListener("track", (e) => {
                        const remoteAudio = document.createElement('audio');
                        remoteAudio.srcObject = e.streams[0];
                        remoteAudio.play();
                    });
                }
            });

            var eventHandlers = {
                'connecting': function (data) {
                    support_button.classList.add('btn-warning');
                    support_button.innerText = 'Calling ...';
                    soundPlayer.play();
                    soundPlayer.loop = true;

                },
                'confirmed': function (data) {
                    support_button.classList.add('btn-danger');
                    support_button.innerText = 'Hangup';
                },
                'accepted': function (data) {
                    soundPlayer.pause();
                    soundPlayer.currentTime = 0;
                },
                'ended': function (data) {
                    support_button.classList.remove('btn-danger', 'btn-warning');
                    support_button.innerText = initTalkButtonText;
                    soundPlayer.pause();
                    soundPlayer.currentTime = 0;
                },
                'failed': function (data) {
                    support_button.classList.remove('btn-danger', 'btn-warning');
                    support_button.innerText = initTalkButtonText;
                    soundPlayer.pause();
                    soundPlayer.currentTime = 0;
                }
            };

            options = {
                'eventHandlers': eventHandlers,
                'mediaConstraints': {'audio': true, 'video': false}
            };

            supportPhone.on('connected', function (e) {
                console.log('SIP Connected');
                callSession = supportPhone.call(`sip:${support_exten}`, options);
            });

        } else {
            if (support_button.classList.contains('btn-danger') || support_button.classList.contains('btn-warning')) {
                callSession.terminate();
            } else {
                callSession = supportPhone.call(`sip:${support_exten}`, options);
            }
        }
    }
});