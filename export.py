#!/usr/bin/env python

from mechanize import Browser
from pyquery import PyQuery
from collections import namedtuple
import re


Transaction = namedtuple('Transaction', ['date', 'name', 'desc', 'amount'])


def getCredentials():

    try:
        with open('.credentials', 'r') as f:
            lines = f.read().split('\n')

            if len(lines) < 2:
                print '.credentials file should have username on first line, password on second'
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


"""See http://en.wikipedia.org/wiki/Quicken_Interchange_Format for more info."""
def writeQIF(trans, creds):

    accName = creds[2] if len(creds) > 2 else 'QIF Account'

    with open('export.qif', 'w') as f:

        # Write header
        f.write('!Account\n')
        f.write('N' + accName +'\n')
        f.write('TCCard\n')
        f.write('^\n')
        f.write('!Type:CCard\n')

        for t in trans:
            f.write('C\n') # status - uncleared
            f.write('D' + t.date + '\n') # date
            f.write('T' + t.amount.replace('$', '') + '\n') # amount
            f.write('M' + re.sub('\s+', ' ', t.name + ' ' + t.desc) + '\n') # memo
            #f.write('P' + t.desc.replace('\t', ' ') + '\n') # payee
            f.write('^\n') # end of record


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
