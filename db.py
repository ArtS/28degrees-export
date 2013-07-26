
import sqlite3
from datetime import datetime
import time


db = None


def init_db():

    global db
    db = sqlite3.connect('./export/transactions.db')
    db.execute('''
        create table if not exists transactions
              (
                id integer primary key autoincrement,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                date text,
                payer text,
                amount text,
                memo text,
                payee text

              )''')
    return db


def save_transaction(t):

    global db
    db.execute('insert into transactions (date, payer, amount, memo, payee) values (?, ?, ?, ?, ?)',
               (
                t.date,
                t.payer,
                t.amount,
                t.memo,
                t.payee
               )
              )
    db.commit()


def get_only_new_transactions(trans):

    res = []
    for t in trans:
        if not is_transaction_in_db(t):
            res.append(t)

    return res


def save_transactions(trans):

    for t in trans:
        save_transaction(t)


def is_transaction_in_db(t):

    global db
    cur = db.execute('''
                     select * from transactions where
                        date = ?
                        and payer = ?
                        and amount = ?
                        and memo = ?
                        and payee = ?
                     ''',
                     (t.date,
                      t.payer,
                      t.amount,
                      t.memo,
                      t.payee))

    row = cur.fetchall()
    if not row:
        return False

    return True
