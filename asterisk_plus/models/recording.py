import base64
from datetime import datetime, timedelta
import io
import time
import wave
import logging
from odoo import models, fields, api, _
from .server import debug

logger = logging.getLogger(__name__)

try:
    import lameenc
    LAMEENC = True
except ImportError:
    logger.info('MP3 encoding not available. '
                'To enable pip3 install lameenc.')
    LAMEENC = False
try:
    import speech_recognition as sr
    SR = True
except ImportError:
    logger.error('Recording speech recognition not available. '
                 'To enable pip3 install SpeechRecognition.')
    SR = False


class Recording(models.Model):
    _name = 'asterisk_plus.recording'
    _inherit = 'mail.thread'
    _description = 'Recording'
    _rec_name = 'uniqueid'
    _order = 'id desc'

    uniqueid = fields.Char(size=64, index=True, readonly=True)
    call = fields.Many2one('asterisk_plus.call', ondelete='set null', readonly=True)
    channel = fields.Many2one('asterisk_plus.channel', ondelete='set null', readonly=True)
    partner = fields.Many2one('res.partner', ondelete='set null', readonly=True)
    calling_user = fields.Many2one('res.users', ondelete='set null', readonly=True)
    called_user = fields.Many2one('res.users', ondelete='set null', readonly=True)
    calling_number = fields.Char(index=True, readonly=True)
    calling_name = fields.Char(compute='_get_calling_name', readonly=True)
    called_number = fields.Char(index=True, readonly=True)
    answered = fields.Datetime(index=True, readonly=True)
    duration = fields.Integer(related='call.duration', store=True)
    duration_human = fields.Char(related='call.duration_human', store=True)
    recording_widget = fields.Char(compute='_get_recording_widget',
                                   string='Recording')
    recording_filename = fields.Char(readonly=True, index=True)
    recording_data = fields.Binary(attachment=False, readonly=True, string=_('Download'))
    recording_attachment = fields.Binary(attachment=True, readonly=True, string=_('Download'))
    transcript = fields.Text(string='Transcript')
    file_path = fields.Char(readonly=True)
    tags = fields.Many2many('asterisk_plus.tag',
                            relation='asterisk_plus_recording_tag',
                            column1='tag', column2='recording')
    keep_forever = fields.Selection([
        ('no', 'Archivable'),
        ('yes', 'Keep Forever')
    ], default='no', tracking=True)
    icon = fields.Html(compute='_get_icon', string='I')

    @api.model
    def create(self, vals):
        rec = super(Recording, self.with_context(
            mail_create_nosubscribe=True, mail_create_nolog=True)).create(vals)
        return rec

    def write(self, vals):
        if vals.get("tags"):
            # Get tags to be notified when attached to recording
            present_tags = self.tags.ids
            new_tags = vals.get("tags")
            tags_to_notify = set(new_tags[0][2]) - set(present_tags)
            msg = "Tag attached to recording {}".format(self.uniqueid)
            for tag in tags_to_notify:
                self.env['asterisk_plus.tag'].browse(
                    tag).sudo().message_post(
                        subject=_('Tag attached to recording'),
                        body=msg)
        return super(Recording, self).write(vals)

    def _get_recording_widget(self):
        for rec in self:
            recording_source = 'recording_data' if rec.recording_data else 'recording_attachment'
            rec.recording_widget = '<audio id="sound_file" preload="auto" ' \
                'controls="controls"> ' \
                '<source src="/web/content?model=asterisk_plus.recording&' \
                'id={recording_id}&filename={filename}&field={source}&' \
                'filename_field=recording_filename&download=True" />' \
                '</audio>'.format(
                    recording_id=rec.id,
                    filename=rec.recording_filename,
                    source=recording_source)

    @api.model
    def save_call_recording(self, channel):
        """Save call recording."""

        if not channel.recording_file_path:
            debug(self, 'File path not specified for channel {}'.format(channel.channel))
            return False
        if channel.cause != '16':
            debug(self,
                'Call Recording was activated but call was not answered'
                ' on {}'.format(channel.channel))
            return False
        debug(self, 'Save call recording for channel {}.'.format(channel.channel))
        # Transfer the file.
        channel.server.local_job(
            fun='asterisk.get_file',
            arg=channel.recording_file_path,
            res_model='asterisk_plus.recording',
            res_method='upload_recording',
            pass_back={'channel_id': channel.id}
        )
        return True

    @api.model
    def upload_recording(self, data, pass_back):
        """Upload call recording to Odoo."""

        if not isinstance(data, dict):
            debug(self, 'Upload recording error: {}'.format(data))
            return False

        channel_id = pass_back.get('channel_id')
        input_data = data.get('file_data')
        channel = self.env['asterisk_plus.channel'].browse(channel_id)
        debug(self, 'Call recording upload for channel {}'.format(
            channel.channel))
        mp3_encode = self.env['asterisk_plus.settings'].get_param(
            'use_mp3_encoder')
        transcipt_recording = self.env['asterisk_plus.settings'].get_param(
            'transcipt_recording')
        # Transcript
        transcript = None
        if SR and transcipt_recording:
            debug(self, 'Transcript call recording for channel {}'.format(
                channel.channel))
            key = self.env['asterisk_plus.settings'].get_param(
                'google_sr_api_key') or None
            lang = self.env['asterisk_plus.settings'].get_param(
                'recognition_lang')
            r = sr.Recognizer()
            decoded_input = base64.b64decode(input_data)
            audio_file = sr.AudioFile(io.BytesIO(decoded_input))
            with audio_file as src:
                r.adjust_for_ambient_noise(src, duration=0.5)
                audio = r.record(src)
            try:
                transcript = r.recognize_google(audio, key=key, language=lang)
            except Exception as e:
                logger.error('Speech Recognition error: {}'.format(e))
                transcript = ''
            transcript = transcript
        # Convert to mp3
        if LAMEENC and mp3_encode:
            bit_rate = int(self.env['asterisk_plus.settings'].get_param(
                'mp3_encoder_bitrate', default=96))
            quality = int(self.env['asterisk_plus.settings'].get_param(
                'mp3_encoder_quality', default=4))
            decoded_input = base64.b64decode(input_data)
            output_data = base64.b64encode(
                self._wav_to_mp3(io.BytesIO(decoded_input), bit_rate, quality))
            extension = 'mp3'
        else:
            output_data = input_data
            extension = 'wav'
        # Set filestore
        fs = {}
        if self.env['asterisk_plus.settings'].get_param(
                'recording_storage') == 'db':
            fs['recording_attachment'] = output_data
        else:
            fs['recording_data'] = output_data
        # Create a recording
        rec = self.create({
            'uniqueid': channel.uniqueid,
            **fs,
            'recording_filename': '{}.{}'.format(channel.uniqueid, extension),
            'call': channel.call.id,
            'channel': channel.id,
            'partner': channel.call.partner.id,
            'calling_user': channel.call.calling_user.id,
            'called_user': channel.call.called_user.id,
            'calling_number': channel.call.calling_number,
            'called_number': channel.call.called_number,
            'answered': channel.call.answered,
            'transcript': transcript,
            'file_path': channel.recording_file_path,
        })
        # Delete recording from the Asterisk server
        if self.env['asterisk_plus.settings'].get_param('delete_recordings'):
            debug(self, 'DELETE RECORDING {}'.format(rec.file_path))
            channel.server.local_job(
                fun='asterisk.delete_file',
                arg=rec.file_path)
        return True

    def _wav_to_mp3(self, file_data, bit_rate, quality):
        """Converts call recording from .wav to .mp3.
        """
        started = time.time()
        wav_data = wave.open(file_data)
        num_channels = wav_data.getnchannels()
        sample_rate = wav_data.getframerate()
        num_frames = wav_data.getnframes()
        pcm_data = wav_data.readframes(num_frames)
        debug(self,
              'Encoding Wave file. Number of channels: '
              '{}. Sample rate: {}, Number of frames: {}'.format(
                num_channels, sample_rate, num_frames))
        wav_data.close()

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bit_rate)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(num_channels)
        encoder.set_quality(quality)  # 2-highest, 7-fastest
        mp3_data = encoder.encode(pcm_data)
        mp3_data += encoder.flush()
        logger.info('Recording convert .wav -> .mp3 took %.2f seconds.',
                    time.time() - started)
        return mp3_data

    @api.model
    def delete_recordings(self):
        """Cron job to delete calls recordings.
        """
        days = self.env[
            'asterisk_plus.settings'].get_param('recordings_keep_days')
        expire_date = datetime.utcnow() - timedelta(days=int(days))
        expired_recordings = self.env['asterisk_plus.recording'].search([
            ('keep_forever', '=', 'no'),
            ('answered', '<=', expire_date.strftime('%Y-%m-%d %H:%M:%S'))
        ])
        logger.info('Expired {} recordings'.format(len(expired_recordings)))
        expired_recordings.unlink()

    def _get_icon(self):
        for rec in self:
            if rec.keep_forever == 'yes':
                rec.icon = '<span class="fa fa-floppy-o"></span>'
            else:
                rec.icon = ''
