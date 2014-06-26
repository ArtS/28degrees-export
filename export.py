#!/usr/bin/env python

from __future__ import print_function
import os
from getpass import getpass
import re
from datetime import datetime
import argparse

from mechanize import Browser
from pyquery import PyQuery
from collections import namedtuple

import db


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
    qq = q
    trans = []

    for row in q('div[name="transactionsHistory"] tr[name="DataContainer"]'):

        date = get_node_text(q('span[name="Transaction_TransactionDate"]', row)[0])
        payer = get_node_text(q('span[name="Transaction_CardName"]', row)[0])
        desc_payee = get_node_text(q('span[name="Transaction_TransactionDescription"]', row)[0])
        amount = get_node_text(q('span[name="Transaction_Amount"]', row)[0])

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
    with open(file_name, 'w') as f:

        # Write header
        print('!Account', file=f)
        print('NQIF Account', file=f)
        print('TCCard', file=f)
        print('^', file=f)
        print('!Type:CCard', file=f)

        for t in trans:
            print('C', file=f) # status - uncleared
            print('D' + t.date, file=f) # date
            print('T' + t.amount, file=f) # amount
            print('M' + t.payer, file=f)
            print('P' + t.payee + t.memo, file=f)
            print('^', file=f) # end of record


@messages('Writing CSV file...', 'OK', '')
def write_csv(trans, file_name):

    print(file_name)
    with open(file_name, 'w') as f:
        print('Date,Amount,Payer,Payee', file=f)
        for t in trans:
            print('"%s","%s","%s","%s"' % (t.date, t.amount, t.payer, t.payee), file=f)


@messages('Logging in...', 'OK', 'Login failed')
def login(creds):

    br = Browser()

    br.open('https://28degrees-online.gemoney.com.au/')
    br.open('https://28degrees-online.gemoney.com.au/access/login')

    br.select_form(nr=0)
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

    portalLink = qq('a')
    if len(portalLink) == 0:
        print('Unable to locate link to main page')
        return None

    br.open(portalLink[0].attrib['href'])
    text = br.response().read()
    qq = PyQuery(text)

    transLink = qq('#home-transactions-desktop #view-all-transactions-link')
    if len(transLink) == 0:
        print('Unable to locate link to transactions page')
        return None

    link = transLink[0].attrib['href']
    br.open(link)
    text = br.response().read()

    if 'New card number required' in text:
        q = PyQuery(text)
        cancel_btn = q('input[name="cancelButton"]')

        if len(cancel_btn) == 0:
            print('No cancel button found on "New card required" page')
            return None

        cancel_btn = cancel_btn[0]
        matches = re.match('location\.href="(.*)"', cancel_btn.attrib['onclick'])

        if len(matches.groups()) == 0:
            print('No onclick event in cancel button found')
            return None

        # Cancel new card number submission
        br.open('https://28degrees-online.gemoney.com.au' + matches.groups()[0])
        br.open('https://28degrees-online.gemoney.com.au/wps/myportal/ge28degrees/public/account/transactions/')

    return br


def export(csv):

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

    br = open_transactions_page(br)
    if not br:
        return

    trans = []

    #i = 1
    while True:
        text = br.response().read()

        #with open('step%s.html' % i, 'w') as f:
        #    f.write(text)
        #i += 1

        q = PyQuery(text)

        page_trans = fetchTransactions(text)
        trans += page_trans

        nextButton = q('div[name="transactionsPagingLinks"] a[name="nextButton"]')
        isNextVisible = len(nextButton) != 0
        if not isNextVisible:
            break

        page_count = len(page_trans)
        print('Got %s transactions, from %s to %s' % (page_count,
                                                      page_trans[0].date,
                                                      page_trans[-1].date))
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

        f_str = '%d/%m/%Y'
        s_d = datetime.strptime(reduce(lambda t1, t2: t1 if datetime.strptime(t1.date, f_str) <
                                                      datetime.strptime(t2.date, f_str) else t2,
                                       new_trans).date, f_str)
        e_d = datetime.strptime(reduce(lambda t1, t2: t1 if datetime.strptime(t1.date, f_str) >
                                                      datetime.strptime(t2.date, f_str) else t2,
                                       new_trans).date, f_str)
        out_str = '%Y.%m.%d'

        if csv:
            file_name = os.path.join(export_path, '%s-%s.csv' % (s_d.strftime(out_str), e_d.strftime(out_str)))
            write_csv(new_trans, file_name)
        else:
            file_name = os.path.join(export_path, '%s-%s.qif' % (s_d.strftime(out_str), e_d.strftime(out_str)))
            write_qif(new_trans, file_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("""I load transactions from 28degrees-online.gemoney.com.au.
If no arguments specified, I will produce a nice QIF file for you
To get CSV, specify run me with --csv parameter""")
    parser.add_argument('--csv', action='store_true')
    args = parser.parse_args()
    export(**vars(args))
