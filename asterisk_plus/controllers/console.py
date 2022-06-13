# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import logging
import uuid
from odoo import http, SUPERUSER_ID, api
import odoo.modules.registry

logger = logging.getLogger(__name__)


class ConsoleController(http.Controller):

    @http.route('/asterisk_plus/console/<db>/<int:server_id>/<token>',
                auth='none')
    def check_auth(self, db, server_id, token):
        registry = odoo.registry(db)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            server = env['asterisk_plus.server'].browse(server_id)
            console_auth_token = server.console_auth_token
            server.console_auth_token = None
            if console_auth_token == token:
                return 'ok'
            else:
                return 'failed'

    @http.route('/asterisk_plus/console/<int:server_id>', auth='user')
    def spawn_terminal(self, server_id):
        user = http.request.env['res.users'].browse(http.request.env.uid)
        if not user.has_group('asterisk_plus.group_asterisk_admin'):
            return 'You must be admin to use console.'
        server = http.request.env['asterisk_plus.server'].browse(server_id)
        auth_token = uuid.uuid4().hex
        # Cache the token for short period so that terminado can check it.
        server.console_auth_token = auth_token
        page = """<!doctype html>
            <html>
            <head>
              <link rel="stylesheet" href="/asterisk_plus/static/lib/xterm/dist/xterm.css" />
              <script src="/asterisk_plus/static/lib/xterm/dist/xterm.js"></script>
              <script src="/asterisk_plus/static/lib/xterm/dist/addons/terminado/terminado.js"></script>
              <script src="/asterisk_plus/static/lib/xterm/dist/addons/fit/fit.js"></script>
            </head>
            <body>
              <div id="terminal"></div>
              <script>
                terminado.apply(Terminal);
                fit.apply(Terminal);
                var term = new Terminal({
                  cols: 120,
                  rows: 48,
                  convertEol: true,
                  fontFamily: `'Fira Mono', monospace`,
                  fontSize: 12,
                  rendererType: 'dom', // default is canvas
                });
                term.setOption('theme', { background: '#000000',  foreground: '#ffffff'})
                var sock = new WebSocket('%s');
                sock.addEventListener('open', function () {
                  term.terminadoAttach(sock);
                });
                term.open(document.getElementById('terminal'), focus=true);
                term.fit()
              </script>
            </body>
            </html>""" % '{}?server={}&auth={}&db={}'.format(
            server.console_url, server_id, auth_token,
            http.request.env.cr.dbname)
        return http.Response(page)
