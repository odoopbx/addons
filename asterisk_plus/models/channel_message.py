from datetime import datetime, timedelta
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .server import debug

logger = logging.getLogger(__name__)


class ChannelMessage(models.Model):
    _name = 'asterisk_plus.channel_message'
    _rec_name = 'uniqueid'
    _order = 'id desc'
    _description = 'Channel Message'

    channel_id = fields.Many2one('asterisk_plus.channel', ondelete='cascade',
                                 string='Channel ID')
    event = fields.Char(index=True, size=64)
    privilege = fields.Char(size=256)
    channel = fields.Char(index=True, size=256)
    uniqueid = fields.Char(size=150, index=True, string='Unique ID')
    linkedid = fields.Char(size=150, index=True, string='Linked ID')
    context = fields.Char(size=80)
    exten = fields.Char(size=32)
    callerid_num = fields.Char(size=32, string='CallerID number')
    callerid_name = fields.Char(size=32, string='CallerID name')
    system_name = fields.Char(size=128)
    message = fields.Text()

    @api.model
    def create_from_event(self, channel, event):
        data = {
            'channel_id': channel.id,
            'event': event.get('Event'),
            'channel': event.get('Channel'),
            'callerid_num': event.get('CallerIDNum'),
            'callerid_name': event.get('CallerIDName'),
            'context': event.get('Context'),
            'exten': event.get('Exten'),
            'uniqueid': event.get('Uniqueid'),
            # All AMI events have linkedid? Better try to get...
            'uniqueid': event.get('Uniqueid'),
            'message': json.dumps(event, indent=2),

        }
        self.create(data)

    @api.model
    def vacuum(self, hours):
        """Cron job to delete channel messages.
        """
        expire_date = datetime.utcnow() - timedelta(hours=hours)
        channel_msgs = self.env['asterisk_plus.channel_message'].search([
            ('create_date', '<=', expire_date.strftime('%Y-%m-%d %H:%M:%S'))
        ])
        channel_msgs.unlink()
