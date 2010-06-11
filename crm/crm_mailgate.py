# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import re
import os

import binascii
import mx.DateTime
import base64

from tools.translate import _

import tools
from osv import fields,osv,orm
from osv.orm import except_orm
import collections

from tools import command_re

class mailgate_thread(osv.osv):
    """ mailgate_thread """

    _name = "mailgate.thread"
    _inherit = "mailgate.thread"    

    def message_new(self, cr, uid, msg, context):
        """
        Automatically calls when new email message arrives
        
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        """

        mailgate_pool = self.pool.get('email.server.tools')

        subject = msg.get('subject')
        body = msg.get('body')
        msg_from = msg.get('from')
        priority = msg.get('priority')
        
        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg.get('cc'),
            'description': body,
            'user_id': False,
        }
        if msg.get('priority', False):
            vals['priority'] = priority
        
        res = mailgate_pool.get_partner(cr, uid, msg.get('from'))
        if res:
            vals.update(res)
        res = self.create(cr, uid, vals, context)
        cases = self.browse(cr, uid, [res])
        self._history(cr, uid, cases, _('Receive'), history=True, details=body, email_from=msg_from, message_id=msg.get('id'))
        
        attachents = msg.get('attachments', [])
        for attactment in attachents or []:
            data_attach = {
                'name': attactment,
                'datas':binascii.b2a_base64(str(attachents.get(attactment))),
                'datas_fname': attactment,
                'description': 'Mail attachment',
                'res_model': self._name,
                'res_id': res,
            }
            self.pool.get('ir.attachment').create(cr, uid, data_attach)

        return res

    def message_update(self, cr, uid, ids, vals={}, msg="", default_act='pending', context={}):
        """ 
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of update mail’s IDs 
        """
        
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        
        msg_from = msg['from']
        vals.update({
            'description': msg['body']
        })
        if msg.get('priority', False):
            vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = { }
        for line in msg['body'].split('\n'):
            line = line.strip()
            res = command_re.match(line)
            if res and maps.get(res.group(1).lower(), False):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()
        
        vals.update(vls)
        res = self.write(cr, uid, ids, vals)
        cases = self.browse(cr, uid, ids)
        message_id = context.get('references_id', False)
        self._history(cr, uid, cases, _('Receive'), history=True, details=msg['body'], email_from=msg_from, message_id=message_id)        
        #getattr(self, act)(cr, uid, select)
        return res

    def emails_get(self, cr, uid, ids, context=None):

        """ 
        Get Emails
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of email’s IDs
        @param context: A standard dictionary for contextual values
        """
        res = {}

        if isinstance(ids, (str, int, long)):
            select = [long(ids)]
        else:
            select = ids

        for thread in self.browse(cr, uid, select, context=context):
            values = collections.defaultdict(set)

            for message in thread.message_ids:
                user_email = (message.user_id and message.user_id.address_id and message.user_id.address_id.email) or False
                values['user_email'].add(user_email)
                values['email_from'].add(message.email_from)
                values['email_cc'].add(message.email_cc or False)

            res[str(thread.id)] = dict((key,list(values[key])) for key, value in values.iteritems())

        return res

    def msg_send(self, cr, uid, id, *args, **argv):

        """ Send The Message
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of email’s IDs
            @param *args: Return Tuple Value
            @param **args: Return Dictionary of Keyword Value
        """
        return True

mailgate_thread()
