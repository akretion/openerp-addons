# encoding: utf-8
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from osv import osv, fields
from tools.translate import _
import decimal_precision as dp

class account_cashbox_line(osv.osv):

    """ Cash Box Details """

    _name = 'account.cashbox.line'
    _description = 'CashBox Line'

    def _sub_total(self, cr, uid, ids, name, arg, context=None):

        """ Calculates Sub total
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for obj in self.browse(cr, uid, ids):
            res[obj.id] = obj.pieces * obj.number
        return res

    def on_change_sub(self, cr, uid, ids, pieces, number, *a):

        """ Calculates Sub total on change of number
        @param pieces: Names of fields.
        @param number:
        """
        sub = pieces * number
        return {'value': {'subtotal': sub or 0.0}}

    _columns = {
        'pieces': fields.float('Values', digits_compute=dp.get_precision('Account')),
        'number': fields.integer('Number'),
        'subtotal': fields.function(_sub_total, method=True, string='Sub Total', type='float', digits_compute=dp.get_precision('Account')),
        'starting_id': fields.many2one('account.bank.statement', ondelete='cascade'),
        'ending_id': fields.many2one('account.bank.statement', ondelete='cascade'),
     }

account_cashbox_line()

class account_cash_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def _get_starting_balance(self, cr, uid, ids, context=None):

        """ Find starting balance
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for statement in self.browse(cr, uid, ids):
            amount_total = 0.0

            if statement.journal_id.type not in('cash'):
                continue

            for line in statement.starting_details_ids:
                amount_total+= line.pieces * line.number
            res[statement.id] = {
                'balance_start': amount_total
            }
        return res

    def _balance_end_cash(self, cr, uid, ids, name, arg, context=None):
        """ Find ending balance  "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res ={}
        for statement in self.browse(cr, uid, ids):
            amount_total = 0.0
            for line in statement.ending_details_ids:
                amount_total += line.pieces * line.number
            res[statement.id] = amount_total
        return res

    def _get_sum_entry_encoding(self, cr, uid, ids, name, arg, context=None):

        """ Find encoding total of statements "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res2={}
        for statement in self.browse(cr, uid, ids):
            encoding_total=0.0
            for line in statement.line_ids:
               encoding_total += line.amount
            res2[statement.id] = encoding_total
        return res2

    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        res = {}

        company_currency_id = res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id

        statements = self.browse(cursor, user, ids, context=context)
        for statement in statements:
            res[statement.id] = statement.balance_start
            currency_id = statement.currency.id
            for line in statement.move_line_ids:
                if line.debit > 0:
                    if line.account_id.id == \
                            statement.journal_id.default_debit_account_id.id:
                        res[statement.id] += res_currency_obj.compute(cursor,
                                user, company_currency_id, currency_id,
                                line.debit, context=context)
                else:
                    if line.account_id.id == \
                            statement.journal_id.default_credit_account_id.id:
                        res[statement.id] -= res_currency_obj.compute(cursor,
                                user, company_currency_id, currency_id,
                                line.credit, context=context)

            if statement.state in ('draft', 'open'):
                for line in statement.line_ids:
                    res[statement.id] += line.amount
        for r in res:
            res[r] = round(res[r], 2)
        return res

    def _get_company(self, cr, uid, context=None):
        user_pool = self.pool.get('res.users')
        company_pool = self.pool.get('res.company')
        user = user_pool.browse(cr, uid, uid, context=context)
        company_id = user.company_id
        if not company_id:
            company_id = company_pool.search(cr, uid, [])
        return company_id and company_id[0] or False

    def _get_cash_open_box_lines(self, cr, uid, context={}):
        res = []
        curr = [1, 2, 5, 10, 20, 50, 100, 500]
        for rs in curr:
            dct = {
                'pieces': rs,
                'number': 0
            }
            res.append(dct)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'cash')], context=context)
        if journal_ids:
            results = self.search(cr, uid, [('journal_id', 'in', journal_ids),('state', '=', 'confirm')], context=context)
            if results:
                cash_st = self.browse(cr, uid, results, context)[0]
                for cash_line in cash_st.ending_details_ids:
                    for r in res:
                        if cash_line.pieces == r['pieces']:
                            r['number'] = cash_line.number
        return res

    def _get_default_cash_close_box_lines(self, cr, uid, context={}):
        res = []
        curr = [1, 2, 5, 10, 20, 50, 100, 500]
        for rs in curr:
            dct = {
                'pieces': rs,
                'number': 0
            }
            res.append(dct)
        return res

    def _get_cash_close_box_lines(self, cr, uid, context={}):
        res = []
        curr = [1, 2, 5, 10, 20, 50, 100, 500]
        for rs in curr:
            dct = {
                'pieces': rs,
                'number': 0
            }
            res.append((0, 0, dct))
        return res

    def _get_cash_open_close_box_lines(self, cr, uid, context={}):
        res = {}
        start_l = []
        end_l = []
        starting_details = self._get_cash_open_box_lines(cr, uid, context)
        ending_details = self._get_default_cash_close_box_lines(cr, uid, context)
        for start in starting_details:
            start_l.append((0, 0, start))
        for end in ending_details:
            end_l.append((0, 0, end))
        res['start'] = start_l
        res['end'] = end_l
        return res

    _columns = {
        'balance_end_real': fields.float('Closing Balance', digits_compute=dp.get_precision('Account'), states={'confirm': [('readonly', True)]}, help="closing balance entered by the cashbox verifier"),
        'state': fields.selection(
            [('draft', 'Draft'),
            ('confirm', 'Closed'),
            ('open','Open')], 'State', required=True, states={'confirm': [('readonly', True)]}, readonly="1"),
        'total_entry_encoding': fields.function(_get_sum_entry_encoding, method=True, store=True, string="Cash Transaction", help="Total cash transactions"),
        'closing_date': fields.datetime("Closed On"),
        'balance_end': fields.function(_end_balance, method=True, store=True, string='Balance', help="Closing balance based on Starting Balance and Cash Transactions"),
        'balance_end_cash': fields.function(_balance_end_cash, method=True, store=True, string='Balance', help="Closing balance based on cashBox"),
        'starting_details_ids': fields.one2many('account.cashbox.line', 'starting_id', string='Opening Cashbox'),
        'ending_details_ids': fields.one2many('account.cashbox.line', 'ending_id', string='Closing Cashbox'),
        'name': fields.char('Name', size=64, required=True, states={'draft': [('readonly', False)]}, readonly=True, help='if you give the Name other then /, its created Accounting Entries Move will be with same name as statement name. This allows the statement entries to have the same references than the statement itself'),
        'user_id': fields.many2one('res.users', 'Responsible', required=False),
    }
    _defaults = {
        'state': 'draft',
        'date': time.strftime("%Y-%m-%d %H:%M:%S"),
        'user_id': lambda self, cr, uid, context=None: uid,
        'starting_details_ids': _get_cash_open_box_lines,
        'ending_details_ids': _get_default_cash_close_box_lines
     }

    def create(self, cr, uid, vals, context=None):
        sql = [
                ('journal_id', '=', vals.get('journal_id', False)),
                ('state', '=', 'open')
        ]
        open_jrnl = self.search(cr, uid, sql)
        if open_jrnl:
            raise osv.except_osv('Error', _('You can not have two open register for the same journal'))

        if self.pool.get('account.journal').browse(cr, uid, vals['journal_id']).type == 'cash':
            open_close = self._get_cash_open_close_box_lines(cr, uid, context)
            if vals.get('starting_details_ids', False):
                for start in vals.get('starting_details_ids'):
                    dict_val = start[2]
                    for end in open_close['end']:
                       if end[2]['pieces'] == dict_val['pieces']:
                           end[2]['number'] += dict_val['number']
            vals.update({
#                'ending_details_ids': open_close['start'],
                'starting_details_ids': open_close['end']
            })
        else:
            vals.update({
                'ending_details_ids': False,
                'starting_details_ids': False
            })
        res_id = super(account_cash_statement, self).create(cr, uid, vals, context=context)
        self.write(cr, uid, [res_id], {})
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        """
        Update redord(s) comes in {ids}, with new value comes as {vals}
        return True on success, False otherwise

        @param cr: cursor to database
        @param user: id of current user
        @param ids: list of record ids to be update
        @param vals: dict of new values to be set
        @param context: context arguments, like lang, time zone

        @return: True on success, False otherwise
        """

        super(account_cash_statement, self).write(cr, uid, ids, vals)
        res = self._get_starting_balance(cr, uid, ids)
        for rs in res:
            super(account_cash_statement, self).write(cr, uid, [rs], res.get(rs))
        return True

    def onchange_journal_id(self, cr, uid, statement_id, journal_id, context=None):
        """ Changes balance start and starting details if journal_id changes"
        @param statement_id: Changed statement_id
        @param journal_id: Changed journal_id
        @return:  Dictionary of changed values
        """
        res = {}
        balance_start = 0.0

        if not journal_id:
            res.update({
                'balance_start': balance_start
            })
            return res
        return super(account_cash_statement, self).onchange_journal_id(cr, uid, statement_id, journal_id, context=context)

    def _equal_balance(self, cr, uid, cash_id, context=None):
        statement = self.browse(cr, uid, cash_id, context=context)
        self.write(cr, uid, [cash_id], {'balance_end_real': statement.balance_end})
        statement.balance_end_real = statement.balance_end
        if statement.balance_end != statement.balance_end_cash:
            return False
        else:
            return True

    def _user_allow(self, cr, uid, statement_id, context=None):
        return True

    def button_open(self, cr, uid, ids, context=None):
        """ Changes statement state to Running.
        @return: True
        """
        if context is None:
            context = {}
        statement_pool = self.pool.get('account.bank.statement')
        for statement in statement_pool.browse(cr, uid, ids, context=context):
            vals = {}
            force_allow = context.get('force_allow',False)
            if not force_allow and not self._user_allow(cr, uid, statement.id, context=context):
                raise osv.except_osv(_('Error !'), _('User %s does not have rights to access %s journal !' % (statement.user_id.name, statement.journal_id.name)))

            if statement.name and statement.name == '/':
                number = self.pool.get('ir.sequence').get(cr, uid, 'account.cash.statement')
                vals.update({
                    'name': number
                })

            vals.update({
                'date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'state': 'open',

            })
            self.write(cr, uid, [statement.id], vals)
        return True

    def balance_check(self, cr, uid, cash_id, journal_type='bank', context=None):
        if journal_type == 'bank':
            return super(account_cash_statement, self).balance_check(cr, uid, cash_id, journal_type, context)
        if not self._equal_balance(cr, uid, cash_id, context):
            raise osv.except_osv(_('Error !'), _('CashBox Balance is not matching with Calculated Balance !'))
        return True

    def statement_close(self, cr, uid, ids, journal_type='bank', context=None):
        if journal_type == 'bank':
            return super(account_cash_statement, self).statement_close(cr, uid, ids, journal_type, context)
        vals = {
            'state':'confirm',
            'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return self.write(cr, uid, ids, vals, context=context)

    def check_status_condition(self, cr, uid, state, journal_type='bank'):
        if journal_type == 'bank':
            return super(account_cash_statement, self).check_status_condition(cr, uid, state, journal_type)
        return state=='open'

    def button_confirm_cash(self, cr, uid, ids, context=None):
        super(account_cash_statement, self).button_confirm_bank(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        cash_box_line_pool = self.pool.get('account.cashbox.line')
        super(account_cash_statement, self).button_cancel(cr, uid, ids, context=context)
        for st in self.browse(cr, uid, ids, context):
            for end in st.ending_details_ids:
                cash_box_line_pool.write(cr, uid, [end.id], {'number': 0})
        return True

account_cash_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
