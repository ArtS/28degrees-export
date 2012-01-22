#!/usr/bin/env python

from mechanize import Browser
from pyquery import PyQuery
from collections import namedtuple

Transaction = namedtuple('Transaction', ['date', 'name', 'desc', 'amount'])


def getCredentials():
    try:
        with open('.credentials', 'r') as f:
            lines = f.read().split('\n')

            if len(lines) < 2:
                print '.credentials files should have username on first line, password on second'
                return None

            return lines

    except Exception as e:
        print 'Error opening credentials file.'
        print e
        return None


def fetchTransactions(text):
    q = PyQuery(text)
    trans = []

    for row in q('tr[name="DataContainer"]'):
        date = q('span[name="Transaction_TransactionDate"]', row)
        name = q('span[name="Transaction_CardName"]', row)
        desc = q('span[name="Transaction_TransactionDescription"]', row)
        amount = q('span[name="Transaction_Amount"]', row)

        trans.append(Transaction(date=date[0].text if len(date) != 0 else None,
                                 name=name[0].text if len(name) != 0 else None,
                                 desc=desc[0].text if len(desc) != 0 else None,
                                 amount=amount[0].text if len(amount) != 0 else None))
    return trans


def export():

    creds = getCredentials()
    if not creds:
        return

    br = Browser()

    br.open('https://28degrees-online.gemoney.com.au/')
    print br.geturl()

    br.open('https://28degrees-online.gemoney.com.au/access/login')
    print br.geturl()

    br.select_form(nr=0)
    br.form['USER'] = creds[0]
    br.form['PASSWORD'] = creds[1]
    br.submit()

    print br.geturl()

    text = br.response().read()
    if "window.location = '/access/login';" in text:
        print 'Login error'
        return

    br.open('https://28degrees-online.gemoney.com.au/wps/myportal/ge28degrees/public/account/transactions/')
    print br.geturl()

    trans = []
    text = br.response().read()
    trans += fetchTransactions(text)

    print trans



if __name__ == "__main__":
    export()
