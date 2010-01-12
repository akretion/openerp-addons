# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import tools
from osv import fields, osv
import os
import pooler
import netsvc
from tools.translate import _

AVAILABLE_PRIORITIES = [
    ('5','Lowest'),
    ('4','Low'),
    ('3','Normal'),
    ('2','High'),
    ('1','Highest')
]

def _links_get(self, cr, uid, context={}):
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]

class crm_claim_categ(osv.osv):
    _name = "crm.claim.categ"
    _description = "Claim Categories"
    _columns = {
            'name': fields.char('Category Name', size=64, required=True),
            'probability': fields.float('Probability (%)', required=True),
            'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
    _defaults = {
        'probability': lambda *args: 0.0
    }
crm_claim_categ()

class crm_claim(osv.osv):
    _name = "crm.claim"
    _description = "Claim Cases"
    _order = "id desc"
    _inherit = 'crm.case'
    _columns = {
        'date_closed': fields.datetime('Closed', readonly=True),
        'ref' : fields.reference('Reference', selection=_links_get, size=128),
        'ref2' : fields.reference('Reference 2', selection=_links_get, size=128),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                        " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
        'planned_revenue': fields.float('Planned Revenue'),
        'planned_cost': fields.float('Planned Costs'),
        'som': fields.many2one('res.partner.som', 'State of Mind', help="The minds states allow to define a value scale which represents" \
                                                                       "the partner mentality in relation to our services.The scale has" \
                                                                       "to be created with a factor for each level from 0 (Very dissatisfied) to 10 (Extremely satisfied)."),
        'categ_id': fields.many2one('crm.claim.categ','Category', domain="[('section_id','=',section_id)]"),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
        'category2_id': fields.many2one('crm.case.category2', 'Category Name', domain="[('section_id','=',section_id)]"),
        
        'partner_name': fields.char("Employee's Name", size=64),
        'partner_mobile': fields.char('Mobile', size=32),
        'partner_phone': fields.char('Phone', size=32),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id)]"),
        'case_id': fields.many2one('crm.case', 'Related Claim'),
    }
    
    _defaults = {
                 'priority': lambda *a: AVAILABLE_PRIORITIES[2][0],
    }

    def msg_new(self, cr, uid, msg):
        mailgate_obj = self.pool.get('mail.gateway')
        msg_body = mailgate_obj.msg_body_get(msg)
        data = {
            'name': msg['Subject'],
            'email_from': msg['From'],
            'email_cc': msg['Cc'],
            'user_id': False,
            'description': msg_body['body'],
            'history_line': [(0, 0, {'description': msg_body['body'], 'email': msg['From'] })],
        }
        res = mailgate_obj.partner_get(cr, uid, msg['From'])
        if res:
            data.update(res)
        res = self.create(cr, uid, data)
        return res

crm_claim()


