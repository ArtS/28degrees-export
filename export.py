#!/usr/bin/env python

from __future__ import print_function
import os
from getpass import getpass
import re
from datetime import datetime
import argparse
import codecs

import mechanize
from mechanize import Browser
from pyquery import PyQuery
from collections import namedtuple

import db
from dateutil import format_tran_date_for_file, format_tran_date_for_qif,\
                     parse_tran_date


Transaction = namedtuple('Transaction',
                         ['date', 'payer', 'amount', 'memo', 'payee'])

export_path = './export'

def messages(before, after_ok, after_fail):

    def external_decorator(f):
        def wrapped(*args, **kwargs):
            print(before)
            r = f(*args, **kwargs)
            print(after_ok if r else after_fail)
            return r
        return wrapped

    return external_decorator


def get_credentials():

    print('Enter your username: ')
    lines = []
    lines.append(raw_input())
    lines.append(getpass())

    return lines


def get_node_text(node):
    return node.text if len(node.text) != 0 else None


"""
0-22 payee, 23-37 loc, 38-$ loc
PAYPAL *KOBO INC       XXXXXXXXXX    ON
WWW.THREADLESS.COM     XXXXXXXXXXX   IL
"""
def fetchTransactions(text):

    q = PyQuery(text)
    trans = []

    for row in q('div[name="transactionsHistory"] tr[name="DataContainer"]'):

        date = parse_tran_date(get_node_text(q('div[name="Transaction_TransactionDate"]', row)[0]))
        payer = get_node_text(q('div[name="Transaction_CardName"]', row)[0])
        desc_payee = get_node_text(q('div[name="Transaction_TransactionDescription"]', row)[0])
        amount = get_node_text(q('div[name="Transaction_Amount"]', row)[0])

        if len(desc_payee) >= 23:
            payee = desc_payee[:23]
            memo = desc_payee[23:]
        else:
            payee = desc_payee
            memo = ''

        # Clean up the data
        amount = amount.replace('$', '')
        payee = re.sub('\s+', ' ', payee)
        memo = re.sub('\s+', ' ', memo)

        trans.append(Transaction(date=date,
                                 payer=payer,
                                 amount=amount,
                                 memo=memo,
                                 payee=payee))

    return trans


"""See http://en.wikipedia.org/wiki/Quicken_Interchange_Format for more info."""
@messages('Writing QIF file...', 'OK', '')
def write_qif(trans, file_name):

    print(file_name)
    with codecs.open(file_name, 'w', encoding='utf-8') as f:

        # Write header
        print('!Account', file=f)
        print('NQIF Account', file=f)
        print('TCCard', file=f)
        print('^', file=f)
        print('!Type:CCard', file=f)

        for t in trans:
            print('C', file=f) # status - uncleared
            print('D' + format_tran_date_for_qif(t.date), file=f) # date
            print('T' + t.amount, file=f) # amount
            print('M' + t.payer, file=f)
            print('P' + t.payee + t.memo, file=f)
            print('^', file=f) # end of record


@messages('Writing CSV file...', 'OK', '')
def write_csv(trans, file_name):

    print(file_name)
    with codecs.open(file_name, 'w', encoding='utf-8') as f:
        print('Date,Amount,Payer,Payee', file=f)
        for t in trans:
            print('"%s","%s","%s","%s"' % (format_tran_date_for_qif(t.date), t.amount, t.payer, t.payee), file=f)


@messages('Logging in...', 'OK', 'Login failed')
def login(creds):

    br = Browser()

    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    #br.set_debug_http(True)
    #br.set_debug_redirects(True)
    #br.set_debug_responses(True)
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    br.addheaders = [('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'),
                     ('Referer', 'https://www.28degreescard.com.au/'),
                     ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')]

    br.open('https://28degrees-online.latitudefinancial.com.au/access/login')
    text = br.response().read()

    br.open('https://28degrees-online.latitudefinancial.com.au/wps/myportal/28degrees')
    text = br.response().read()

    br.open('https://28degrees-online.latitudefinancial.com.au/access/login')
    text = br.response().read()

    br.select_form(nr=0)
    text = br.response().read()
    br.form['USER'] = creds[0]
    br.form['PASSWORD'] = creds[1]
    br.submit()

    text = br.response().read()
    if "window.location = '/access/login';" in text:
        return None

    return br


@messages('Opening transactions page...', 'OK', 'Exiting...')
def open_transactions_page(br):

    text = br.response().read()
    qq = PyQuery(text)
    #log_file('1st-tran.html', text)

    transLink = qq('li[id="mobile.cardsonline.account.transactions"] a')
    if len(transLink) == 0:
        print('Unable to locate link to all transactions page')
        return None

    br.open(transLink[0].attrib['href'])
    text = br.response().read()
    qq = PyQuery(text)
    #log_file('2nd-tran.html', text)

    if 'To continue, please provide the answer to your secret question' in text:
        print('28degrees site requires you to validate this computer first.')
        print('Please log into the website from your browser on this computer and answer verification question when prompted.')
        return None

    if 'Have you received your new card?' in text:
        q = PyQuery(text)
        cancel_btn = q('input[name="cancelButton"]')

        if len(cancel_btn) == 0:
            print('No cancel button found on "New card required" page')
            return None

        cancel_link = cancel_btn[0].getparent().find('a')
        if cancel_link == None:
            print('No cancel link found.')
            return None

        # Cancel new card number submission
        br.open('https://28degrees-online.gemoney.com.au' + cancel_link.attrib['href'])
        br.open('https://28degrees-online.gemoney.com.au/wps/myportal/ge28degrees/public/account/transactions/')

    return br


def log_file(name, text):
    with open(name, 'w') as f:
        f.write(text)


def get_file_name(export_path, s_d, e_d, extension):
    i = 0
    while True:
        f_n = os.path.join(export_path, '%s-%s%s.%s' %
                           (format_tran_date_for_file(s_d),
                            format_tran_date_for_file(e_d),
                            '' if i == 0 else '-%s' % i,
                            extension))
        if not os.path.exists(f_n):
            return f_n

        i += 1


def export(csv, statements):

    if not os.path.exists(export_path):
        os.makedirs(export_path)

    t_db = db.init_db()
    if not t_db:
        print('Error initialising database')
        return

    creds = get_credentials()
    if not creds:
        return

    br = login(creds)
    if not br:
        return

    text = br.response().read()
    qq = PyQuery(text)
    statLink = qq('li[id="cardsonline.statements"] a')
    #log_file('login.html', text)

    br = open_transactions_page(br)
    if not br:
        return

    trans = []

    i = 1
    while True:
        text = br.response().read()

        #log_file('step%s.html' % i, text)
        #i += 1

        q = PyQuery(text)

        page_trans = fetchTransactions(text)
        trans += page_trans

        nextButton = q('div[name="transactionsPagingLinks"] a[name="nextButton"]')
        isNextVisible = len(nextButton) != 0
        if not isNextVisible:
            break

        page_count = len(page_trans)
        if page_count == 0:
            break;

        print('Got %s transactions, from %s to %s' % (page_count,
                                                      format_tran_date_for_qif(page_trans[0].date),
                                                      format_tran_date_for_qif(page_trans[-1].date)))
        print('Opening next page...')

        next_url = nextButton[0].attrib['href']
        br.open(next_url)

        #if len(trans) > 60:
        #    break

    new_trans = db.get_only_new_transactions(trans)
    print('Total of %s new transactions obtained' % len(new_trans))

    if len(new_trans) != 0:

        print('Saving transactions...')
        db.save_transactions(new_trans)

        s_d = reduce(lambda t1, t2: t1 if t1.date < t2.date else t2, new_trans).date
        e_d = reduce(lambda t1, t2: t1 if t1.date > t2.date else t2, new_trans).date

        if csv:
            file_name = get_file_name(export_path, s_d, e_d, 'csv')
            write_csv(new_trans, file_name)
        else:
            file_name = get_file_name(export_path, s_d, e_d, 'qif')
            write_qif(new_trans, file_name)

    if statements:

        if len(statLink) == 0:
            print('Unable to find link to statements page')
            return

        br.open(statLink[0].attrib['href'])
        text = br.response().read()
        q = PyQuery(text)

        for row in q('a[class="s_downloads"]'):
            statement_date = datetime.strptime(row.text, '%d %b %Y').strftime('%Y-%m-%d')
            statement_name = '28 Degrees Statement ' + statement_date + '.pdf'
            statement_path = os.path.join(export_path, statement_name)

            if not os.path.exists(statement_path):
                print('Retrieving statement ' + row.text + ' and saving to ' + statement_path)
                br.retrieve(row.attrib['href'], statement_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("""I load transactions from 28degrees-online.gemoney.com.au.
If no arguments specified, I will produce a nice QIF file for you
To get CSV, specify run me with --csv parameter""")
    parser.add_argument('--csv', action='store_true')
    parser.add_argument('--statements', action='store_true', default=False)
    args = parser.parse_args()
    export(**vars(args))
