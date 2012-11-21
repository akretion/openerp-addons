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

from osv import osv,fields

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]")
    }

    def create(self, cr, uid, vals, context=None):
        order =  super(sale_order, self).create(cr, uid, vals, context=context)
        section_id = self.browse(cr, uid, order, context=context).section_id
        if section_id:
            followers = [follow.id for follow in section_id.message_follower_ids]
            self.message_subscribe(cr, uid, [order], followers, context=context)
        return order

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('section_id'):
            section_id = self.pool.get('crm.case.section').browse(cr, uid, vals.get('section_id'), context=context)
            if section_id:
                vals['message_follower_ids'] = [(4, follower.id) for follower in section_id.message_follower_ids]
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)

sale_order()

class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'default_section_id': fields.many2one('crm.case.section', 'Default Sales Team'),
    }

res_users()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

    _defaults = {
        'section_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).default_section_id.id,
    }

    def create(self, cr, uid, vals, context=None):
        section_id = vals.get('section_id', False)
        invoice_type = context.get('type', False)
        user_id = vals.get('user_id', False)
        user_obj = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
        user_default_section_id = user_obj.default_section_id.id or False
        if not section_id and invoice_type in ['out_invoice', 'out_refund'] and user_id:
            vals['section_id'] = user_default_section_id
        obj_id =  super(account_invoice, self).create(cr, uid, vals, context=context)
        return obj_id

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
