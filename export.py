#!/usr/bin/env python

from __future__ import print_function
import os
from getpass import getpass
import re
from datetime import datetime
import argparse
import codecs
import time
import random
from collections import namedtuple

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

import db
from dateutil import format_tran_date_for_file, format_tran_date_for_qif,\
                     parse_tran_date

random.seed()
BASE_URL = 'https://28degrees-online.latitudefinancial.com.au/';
WAIT_DELAY = 3

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

    print('Enter your username:')
    lines = []
    lines.append(raw_input())
    lines.append(getpass())

    return lines


def get_next_btn(browser):
    return browser.find_element_by_name('nextButton')


def login(creds):

    driver = webdriver.Chrome()
    driver.get(BASE_URL)

    time.sleep(WAIT_DELAY)

    user = driver.find_element_by_name('USER')
    user.send_keys(creds[0])
    user = driver.find_element_by_name('PASSWORD')
    user.send_keys(creds[1])
    btn = driver.find_element_by_name('SUBMIT')
    btn.click()

    time.sleep(WAIT_DELAY)

    tranLink = driver.find_element_by_xpath(u'//a[text()="View Transactions"]')
    tranLink.click()

    # Check we're logged in
    testHeader = driver.find_element_by_name('Header2Text')
    if not testHeader:
      return None

    return driver


def fetch_transactions(driver):

    trans = []
    rows = driver.find_elements_by_css_selector('div[name="transactionsHistory"] tr[name="DataContainer"]')

    for row in rows:

        dateText = row.find_element_by_css_selector('div[name="Transaction_TransactionDate"]').text
        date = parse_tran_date(dateText)
        payer = row.find_element_by_css_selector('div[name="Transaction_CardName"]').text
        desc_payee = row.find_element_by_css_selector('div[name="Transaction_TransactionDescription"]').text
        amount = row.find_element_by_css_selector('div[name="Transaction_Amount"]').text

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


def export(csv, slow):

    print('Use "export.py --help" to see all command line options')
    if slow:
        WAIT_DELAY = 25

    if not os.path.exists(export_path):
        os.makedirs(export_path)

    t_db = db.init_db()
    if not t_db:
        print('Error initialising database')
        return

    creds = get_credentials()
    driver = login(creds)
    if not driver:
      print('Error logging in')
      return

    trans = []

    i = 1
    while True:

        page_trans = fetch_transactions(driver)
        trans += page_trans

        page_count = len(page_trans)
        if page_count == 0:
            break;

        print('Got %s transactions, from %s to %s' % (page_count,
                                                      format_tran_date_for_qif(page_trans[0].date),
                                                      format_tran_date_for_qif(page_trans[-1].date)))
        print('Opening next page...')

        try:
            nextButton = get_next_btn(driver)
            if not nextButton.is_displayed():
                break
            nextButton.click()
            time.sleep(WAIT_DELAY);
        except NoSuchElementException, err:
            break

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

    """
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

    """

if __name__ == "__main__":
    parser = argparse.ArgumentParser("""I load transactions from 28degrees-online.gemoney.com.au.
If no arguments specified, I will produce a nice QIF file for you
To get CSV, specify run me with --csv parameter""")
    parser.add_argument('--csv', action='store_true', help='Write CSV instead of QIF')
    parser.add_argument('--slow', action='store_true', help='Increase wait delay between actions. Use on slow internet connections or when 28degrees is acting up.')
    #parser.add_argument('--statements', action='store_true', default=False)
    args = parser.parse_args()
    export(**vars(args))
