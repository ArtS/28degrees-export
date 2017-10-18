#!/usr/bin/env python

from getpass import getpass
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


def get_credentials():

    print('Enter your username: ')
    lines = []
    lines.append(raw_input())
    lines.append(getpass())

    return lines


creds = get_credentials()

driver = webdriver.Chrome()
driver.get('https://28degrees-online.latitudefinancial.com.au/')

user = driver.find_element_by_name('USER')
user.send_keys(creds[0])
user = driver.find_element_by_name('PASSWORD')
user.send_keys(creds[1])
btn = driver.find_element_by_name('SUBMIT')
btn.click()
