# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

{
    "name" : "Hr holidays evaluation",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Human Resources",
    "website" : "http://www.openerp.com",
    "depends" : ["hr_holidays", "hr_contract", "hr_attendance"],
    "demo_xml" : [],
    'init_xml': [],
    "update_xml" : ["hr_holidays_evaluation_view.xml",
                    "security/ir.model.access.csv"],
    "description" : "Computation of holidays for employee",
    "active" : False,
    "installable" : True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: