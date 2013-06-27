#!/usr/bin/env python

from __future__ import print_function
from getpass import getpass
import re

from mechanize import Browser
from pyquery import PyQuery
from collections import namedtuple


Transaction = namedtuple('Transaction', ['date', 'amount', 'memo', 'payee'])


def get_credentials():

    print('Enter your username and password: ')
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

    for row in q('tr[name="DataContainer"]'):

        date = get_node_text(q('span[name="Transaction_TransactionDate"]', row)[0])
        name = get_node_text(q('span[name="Transaction_CardName"]', row)[0])
        desc_payee = get_node_text(q('span[name="Transaction_TransactionDescription"]', row)[0])
        amount = get_node_text(q('span[name="Transaction_Amount"]', row)[0])

        if len(desc_payee) >= 23:
            payee = desc_payee[:23]
            desc = desc_payee[23:]
        else:
            payee = desc_payee
            desc = ''

        # Clean up the data
        amount = amount.replace('$', '')
        payee = re.sub('\s+', ' ', payee)
        memo = re.sub('\s+', ' ', name + ' ' + desc)

        trans.append(Transaction(date=date, amount=amount, memo=memo, payee=payee))

    return trans


"""See http://en.wikipedia.org/wiki/Quicken_Interchange_Format for more info."""
def writeQIF(trans, creds):

    accName = creds[2] if len(creds) > 2 else 'QIF Account'

    with open('export.qif', 'w') as f:

        # Write header
        print('!Account', file=f)
        print('N' + accName, file=f)
        print('TCCard', file=f)
        print('^', file=f)
        print('!Type:CCard', file=f)

        for t in trans:
            print('C', file=f) # status - uncleared
            print('D' + t.date, file=f) # date
            print('T' + t.amount, file=f) # amount
            print('M' + t.memo, file=f) # memo
            print('P' + t.payee, file=f) # payee
            print('^', file=f) # end of record


def export():

    creds = get_credentials()
    if not creds:
        return

    br = Browser()

    br.open('https://28degrees-online.gemoney.com.au/')
    print(br.geturl())

    br.open('https://28degrees-online.gemoney.com.au/access/login')
    print(br.geturl())

    br.select_form(nr=0)
    br.form['USER'] = creds[0]
    br.form['PASSWORD'] = creds[1]
    br.submit()

    print(br.geturl())


    text = br.response().read()
    if "window.location = '/access/login';" in text:
        print('Login error')
        return

    br.open('https://28degrees-online.gemoney.com.au/wps/myportal/ge28degrees/public/account/transactions/')
    text = br.response().read()
    if 'New card number required' in text:
        q = PyQuery(text)
        cancel_btn = q('input[name="cancelButton"]')
        if len(cancel_btn) == 0:
            print('No cancel button found')
            return
        cancel_btn = cancel_btn[0]

        matches = re.match('location\.href="(.*)"', cancel_btn.attrib['onclick'])

        if len(matches.groups()) == 0:
            print('No onclick event in cancel button found')
            return

        # Cancel new card number submission
        br.open('https://28degrees-online.gemoney.com.au' + matches.groups()[0])
        br.open('https://28degrees-online.gemoney.com.au/wps/myportal/ge28degrees/public/account/transactions/')


    print(br.geturl())

    trans = []

    while True:
        text = br.response().read()

        q = PyQuery(text)
        trans += fetchTransactions(text)

        nextButton = q('a[name="nextButton"]')
        isNextVisible = len(nextButton) != 0
        if not isNextVisible:
            break
        br.open(nextButton[0].attrib['href'])
        print(br.geturl())

    writeQIF(trans, creds)


if __name__ == "__main__":
    export()
