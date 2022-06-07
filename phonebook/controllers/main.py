# -*- coding: utf-8 -*-
from collections import namedtuple
import logging
import socket, struct
from odoo import http, registry, api, SUPERUSER_ID
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

Partner = namedtuple('Partner', 'name phone mobile job company title')


def _get_partners(env, domain=[], limit=None):
    def format_phone(number):
        get = env['ir.config_parameter'].sudo().get_param
        if get('phonebook_strip_plus') == 'True':
            number = number.replace('+', '')
        if get('phonebook_add_plus') == 'True' and not number.startswith('+'):
            number = '+{}'.format(number)
        if get('phonebook_strip_formatting') == 'True':
            number = number.replace(' ', '').replace('(', '').replace(
                ')', '').replace('-', '')
        return number

    partners = []
    manual_include_enabled = True if env[
        'ir.config_parameter'].sudo().get_param(
        'phonebook_manual_partner_select') == 'True' else False
    partner_objs = env['res.partner'].sudo().search(domain, order='name',
                                                    limit=limit)
    if manual_include_enabled:
        partner_objs = partner_objs.filtered(
            lambda r: r.phonebook_include is True)
    for partner in partner_objs:
        if not (partner.phone or partner.mobile):
            # Do not supply contacts without phones
            continue
        p = Partner(
            name=partner.name,
            phone=partner.phone and format_phone(partner.phone),
            mobile=partner.mobile and format_phone(partner.mobile),
            job=partner.function,
            company=partner.parent_id.name,
            title=partner.title,
        )
        partners.append(p)
    return partners


def _check_ip_acl(env):
    def addr_in_net(addr, net):
        ipaddr = struct.unpack('!L',socket.inet_aton(addr))[0]
        netaddr,bits = net.split('/')
        netaddr = struct.unpack('!L',socket.inet_aton(netaddr))[0]
        netmask = ((1<<(32-int(bits))) - 1)^0xffffffff
        return ipaddr & netmask == netaddr & netmask
    # Get settings
    ip_acl = env['ir.config_parameter'].sudo()._get_param('phonebook_ip_acl')
    if not ip_acl:
        return
    # IP ACL enabled
    ipaddr = http.request.httprequest.headers.get(
                        'X_FORWARD_FOR', http.request.httprequest.remote_addr)
    for net in ip_acl.split(','):
        net = net.strip(' ')
        if not net:
            continue
        if addr_in_net(ipaddr, net):
            break
    else:
        raise BadRequest('IP access to {} is denied!'.format(ipaddr))


def _check_basic_auth(env, phone_model):
    if phone_model == 'gs':
        if env['ir.config_parameter'].sudo()._get_param(
                                    'phonebook_gs_auth_enabled') == 'True':
            auth = http.request.httprequest.authorization
            username = env['ir.config_parameter'].sudo()._get_param(
                                            'phonebook_auth_basic_username')
            password = env['ir.config_parameter'].sudo()._get_param(
                                            'phonebook_auth_basic_password')
            if not auth or auth.get('username') != username or \
                                        auth.get('password') != password:
                raise BadRequest('Bad auth!')


def _render_phonebook(db, phone_model):
    template_name = 'phonebook.phonebook_' + phone_model
    response = ''
    if db:
        with registry(db).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            _check_basic_auth(env, phone_model)
            _check_ip_acl(env)
            partners = _get_partners(env)
            response = env.ref(template_name).render(
                                {'partners': partners}, engine='ir.qweb')
    else:
        try:
            partners = _get_partners(http.request.env)
            _check_basic_auth(http.request.env, phone_model)
            _check_ip_acl(http.request.env)            
            response = http.request.env.ref(template_name).render(
                {'partners': partners}, engine='ir.qweb')
        except Exception as e:
            if 'request not bound to a database' in str(e):
                return BadRequest('You must specify db or use db_filter!')
    return http.request.make_response(response,
                                      headers=[('Content-Type', 'text/xml')])


class Phonebook(http.Controller):
    @http.route(['/phonebook/<phone_model>/phonebook.xml',
                 '/phonebook/<phone_model>/phonebook',
                 '/phonebook/<db>/<phone_model>/phonebook.xml',
                 ], auth='none', csrf=False)
    def phonebook_gs(self, db=None, phone_model=None):
        return _render_phonebook(db, phone_model)

    # Special view for Aastra phones to return CSV list
    @http.route(['/phonebook/<phone_model>/phonebook.csv',
                 '/phonebook/<db>/<phone_model>/phonebook.csv',
                 ], auth='none', csrf=False)
    def phonebook_csv(self, db=None, phone_model=None):
        partners = []
        if db:
            with registry(db).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                _check_ip_acl(env)
                partners = _get_partners(env)
        else:
            try:
                _check_ip_acl(http.request.env)
                partners = _get_partners(http.request.env)
            except Exception as e:
                if 'request not bound to a database' in str(e):
                    return BadRequest('You must specify db or use db_filter!')
        response = ''
        for p in partners:
            # First name, Last name, Company, Title, Work, Home, Mobile
            if phone_model == 'aastra':
                response += ',{},{},{},{},,{}\n'.format(
                    p.name, p.company, p.title, p.phone, p.mobile)
            elif phone_model == 'audiocodes':
                response += '{},{},,{}\n'.format(
                    p.name, p.phone, p.mobile)
            else:
                raise BadRequest('Model not supported!')
        return http.request.make_response(
            response, headers=[('Content-Type', 'text/csv')])

    @http.route(['/phonebook/panasonic/contacts.xml',
                 '/phonebook/<db>/panasonic/contacts.xml',
                 ], auth='none', csrf=False)
    def phonebook_panasonic(self, db=None, name=None):
        template_name = 'phonebook.phonebook_panasonic'
        if name:
            domain = [('name', 'ilike', name)]
        else:
            domain = []
        if db:
            with registry(db).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                _check_ip_acl(env)
                partners = _get_partners(env, domain=domain, limit=20)
                response = env.ref(template_name).render(
                                    {'partners': partners}, engine='ir.qweb')
        else:
            try:
                _check_ip_acl(http.request.env)                            
                partners = _get_partners(http.request.env,
                                         domain=domain, limit=20)
                response = http.request.env.ref(template_name).render(
                    {'partners': partners}, engine='ir.qweb')
            except Exception as e:
                if 'request not bound to a database' in str(e):
                    return BadRequest('You must specify db or use db_filter!')
        return http.request.make_response(response,
                                          headers=[('Content-Type', 'text/xml')])

