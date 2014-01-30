# -*- coding: utf-8 -*-
import logging
import simplejson
import os
import io
import base64
import openerp
import time
import random
import math
import openerp.addons.hw_proxy.controllers.main as hw_proxy
import subprocess
from threading import Thread
from Queue import Queue, Empty

try:
    import usb.core
except ImportError:
    usb = None

from openerp.tools.translate import _
from .. import escpos
from ..escpos import printer
from ..escpos import supported_devices
from PIL import Image

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template

_logger = logging.getLogger(__name__)

class EscposDriver(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.queue = Queue()
        self.status = {'status':'connecting', 'messages':[]}

    def connected_usb_devices(self):
        connected = []
        for device in supported_devices.device_list:
            if usb.core.find(idVendor=device['vendor'], idProduct=device['product']) != None:
                connected.append(device)
        return connected
    
    def get_escpos_printer(self):
        try:
            printers = self.connected_usb_devices()
            if len(printers) > 0:
                self.set_status('connected','Connected to '+printers[0]['name'])
                return escpos.printer.Usb(printers[0]['vendor'], printers[0]['product'])
            else:
                self.set_status('disconnected','Printer Not Found')
                return None
        except Exception as e:
            self.set_status('error',str(e))
            return None

    def get_status(self):
        self.push_task('status')
        return self.status

    def open_cashbox(printer):
        printer.cashdraw(2)
        printer.cashdraw(5)

    def set_status(self, status, message = None):
        if status == self.status['status']:
            if message != None and message != self.status['messages'][-1]:
                self.status['messages'].append(message)
        else:
            self.status['status'] = status
            if message:
                self.status['messages'] = [message]
            else:
                self.status['messages'] = []

        if status == 'error' and message:
            _logger.error('ESC/POS Error: '+message)
        elif status == 'disconnected' and message:
            _logger.warning('ESC/POS Device Disconnected: '+message)

    def run(self):
        self.queue = Queue()
        while True:
            try:
                timestamp, task, data = self.queue.get(True)

                printer = self.get_escpos_printer()

                if printer == None:
                    if task != 'status':
                        self.queue.put((timestamp,task,data))
                    time.sleep(5)
                    continue
                elif task == 'receipt': 
                    if timestamp >= time.time() - 1 * 60 * 60:
                        self.print_receipt_body(printer,data)
                        printer.cut()
                elif task == 'cashbox':
                    if timestamp >= time.time() * 12:
                        self.open_cashbox(printer)
                elif task == 'status':
                    pass

            except Exception as e:
                self.set_status('error', str(e))
                _logger.error(e);

    def push_task(self,task, data = None):
        if not self.isAlive():
            self.start()
        self.queue.put((time.time(),task,data))

    def print_receipt_body(self,eprint,receipt):

        def check(string):
            return string != True and bool(string) and string.strip()
        
        def price(amount):
            return ("{0:."+str(receipt['precision']['price'])+"f}").format(amount)
        
        def money(amount):
            return ("{0:."+str(receipt['precision']['money'])+"f}").format(amount)

        def quantity(amount):
            if math.floor(amount) != amount:
                return ("{0:."+str(receipt['precision']['quantity'])+"f}").format(amount)
            else:
                return str(amount)


        def printline(left, right='', width=40, ratio=0.5, indent=0):
            lwidth = int(width * ratio) 
            rwidth = width - lwidth 
            lwidth = lwidth - indent
            
            left = left[:lwidth]
            if len(left) != lwidth:
                left = left + ' ' * (lwidth - len(left))

            right = right[-rwidth:]
            if len(right) != rwidth:
                right = ' ' * (rwidth - len(right)) + right

            return ' ' * indent + left + right + '\n'
        
        def print_taxes():
            taxes = receipt['tax_details']
            for tax in taxes:
                eprint.text(printline(tax['tax']['name'],price(tax['amount']), width=40,ratio=0.6))

        logo = None

        if receipt['company']['logo']:
            img = receipt['company']['logo']
            img = img[img.find(',')+1:]
            f = io.BytesIO('img')
            f.write(base64.decodestring(img))
            f.seek(0)
            logo_rgba = Image.open(f)
            logo = Image.new('RGB', logo_rgba.size, (255,255,255))
            logo.paste(logo_rgba, mask=logo_rgba.split()[3]) 
            width = 300
            wfac  = width/float(logo_rgba.size[0])
            height = int(logo_rgba.size[1]*wfac)
            logo   = logo.resize((width,height), Image.ANTIALIAS)

        # Receipt Header
        if logo:
            eprint._convert_image(logo)
            eprint.text('\n')
        else:
            eprint.set(align='center',type='b',height=2,width=2)
            eprint.text(receipt['company']['name'] + '\n')

        eprint.set(align='center',type='b')
        if check(receipt['shop']['name']):
            eprint.text(receipt['shop']['name'] + '\n')
        if check(receipt['company']['contact_address']):
            eprint.text(receipt['company']['contact address'] + '\n')
        if check(receipt['company']['phone']):
            eprint.text('Tel:' + receipt['company']['phone'] + '\n')
        if check(receipt['company']['vat']):
            eprint.text('VAT:' + receipt['company']['vat'] + '\n')
        if check(receipt['company']['email']):
            eprint.text(receipt['company']['email'] + '\n')
        if check(receipt['company']['website']):
            eprint.text(receipt['company']['website'] + '\n')
        if check(receipt['header']):
            eprint.text(receipt['header']+'\n')
        if check(receipt['cashier']):
            eprint.text('-'*32+'\n')
            eprint.text('Served by '+receipt['cashier']+'\n')

        # Orderlines
        eprint.text('\n\n')
        eprint.set(align='center')
        for line in receipt['orderlines']:
            pricestr = price(line['price_display'])
            if line['discount'] == 0 and line['unit_name'] == 'Unit(s)' and line['quantity'] == 1:
                eprint.text(printline(line['product_name'],pricestr,ratio=0.6))
            else:
                eprint.text(printline(line['product_name'],ratio=0.6))
                if line['discount'] != 0:
                    eprint.text(printline('Discount: '+str(line['discount'])+'%', ratio=0.6, indent=2))
                if line['unit_name'] == 'Unit(s)':
                    eprint.text( printline( quantity(line['quantity']) + ' x ' + price(line['price']), pricestr, ratio=0.6, indent=2))
                else:
                    eprint.text( printline( quantity(line['quantity']) + line['unit_name'] + ' x ' + price(line['price']), pricestr, ratio=0.6, indent=2))

        # Subtotal if the taxes are not included
        taxincluded = True
        if money(receipt['subtotal']) != money(receipt['total_with_tax']):
            eprint.text(printline('','-------'));
            eprint.text(printline(_('Subtotal'),money(receipt['subtotal']),width=40, ratio=0.6))
            print_taxes()
            #eprint.text(printline(_('Taxes'),money(receipt['total_tax']),width=40, ratio=0.6))
            taxincluded = False


        # Total
        eprint.text(printline('','-------'));
        eprint.set(align='center',height=2)
        eprint.text(printline(_('         TOTAL'),money(receipt['total_with_tax']),width=40, ratio=0.6))
        eprint.text('\n\n');
        
        # Paymentlines
        eprint.set(align='center')
        for line in receipt['paymentlines']:
            eprint.text(printline(line['journal'], money(line['amount']), ratio=0.6))

        eprint.text('\n');
        eprint.set(align='center',height=2)
        eprint.text(printline(_('        CHANGE'),money(receipt['change']),width=40, ratio=0.6))
        eprint.set(align='center')
        eprint.text('\n');

        # Extra Payment info
        if receipt['total_discount'] != 0:
            eprint.text(printline(_('Discounts'),money(receipt['total_discount']),width=40, ratio=0.6))
        if taxincluded:
            print_taxes()
            #eprint.text(printline(_('Taxes'),money(receipt['total_tax']),width=40, ratio=0.6))

        # Footer
        if check(receipt['footer']):
            eprint.text('\n'+receipt['footer']+'\n\n')
        eprint.text(receipt['name']+'\n')
        eprint.text(      str(receipt['date']['date']).zfill(2)
                    +'/'+ str(receipt['date']['month']+1).zfill(2)
                    +'/'+ str(receipt['date']['year']).zfill(4)
                    +' '+ str(receipt['date']['hour']).zfill(2)
                    +':'+ str(receipt['date']['minute']).zfill(2) )

driver = EscposDriver()

hw_proxy.drivers['escpos'] = driver
        
class EscposProxy(hw_proxy.Proxy):
    
    @http.route('/hw_proxy/open_cashbox', type='json', auth='none', cors='*')
    def open_cashbox(self):
        _logger.info('ESC/POS: OPEN CASHBOX') 
        driver.push_task('cashbox')
        
    @http.route('/hw_proxy/print_receipt', type='json', auth='none', cors='*')
    def print_receipt(self, receipt):
        _logger.info('ESC/POS: PRINT RECEIPT') 
        driver.push_task('receipt',receipt)
    
