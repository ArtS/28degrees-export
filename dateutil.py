from datetime import datetime


def parse_tran_date(dateStr):
    f_str = '%d %b %Y'
    return datetime.strptime(dateStr, f_str)


def format_tran_date_for_qif(date):
    out_str = '%d/%m/%Y'
    return date.strftime(out_str)


def format_tran_date_for_file(date):
    out_str = '%Y.%m.%d'
    return date.strftime(out_str)

def format_tran_date_for_db(date):
    out_str = '%d/%m/%Y'
    return date.strftime(out_str)
