import logging
from odoo import http
from odoo.http import request, Response


logger = logging.getLogger(__name__)


class PaddleController(http.Controller):

    @http.route('/asterisk_plus_support/paddle', type='http', auth='none', csrf=False)
    def paddle_alert(self, **kwargs):
        """Alerts from paddle."""
        if kwargs.get('alert_name') == 'payment_succeeded':
            logger.info('Paddle payment succeeded')
            self.create_user(kwargs)
        return Response('success', status=200)

    def create_user(self, kwargs):
        """Create portal user for a customer."""

        request.env['res.users'].with_context({'mail_create_nolog': True}).sudo().create({
                'name': kwargs.get('customer_name'),
                'login': kwargs.get('email'),
                'email': kwargs.get('email'),
                'password': 'portal',
                'company_ids': [request.env.ref('base.main_company').id],
                'company_id': request.env.ref('base.main_company').id,
                'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
            })

        logger.info('Portal user created. Name: {}, Email: {}'.format(
            kwargs.get('customer_name'), kwargs.get('email')))
