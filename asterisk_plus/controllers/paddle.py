import logging
from odoo import http
from odoo.http import Response


logger = logging.getLogger(__name__)


class PaddleController(http.Controller):

    @http.route('/asterisk_plus_support/paddle', type='http', auth='none', csrf=False)
    def product_purchase(self, **kwargs):
        logger.info(kwargs)
        return Response('success', status=200)
