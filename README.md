# Export to QIF from 28degrees Master Card website


## Description

This utility logs into https://28degrees-online.gemoney.com.au website, using
your username and password, and simply grabs all your transactions from there,
saving them into QIF file.


## Installation

You will need some things for this tool to work:

    1. Python
    2. Mechanize
    3. PyQuery
    4. Git

As installation instructions for the things above vary for different platforms,
I assume you know how install them, otherwise please let me know and I'll
extend this section with detailed steps for your platform.

Also you'll need to supply the tool with your username/password for 28degrees
website. **THESE details will not be used for anything but logging into the
28degrees' website.**

To do that, create a file named `.credentials` in the same folder where `export.py`
sits. In that file add these three lines (replace `username`, `password`,
`account name` with your user name etc):

    username
    password
    account name

The third line, `account name`, is optional. By default `QIF Account` is used
as an account name when writing QIF file to disk.


## Usage

Simply start `export.py` in your shell of choice (cmd.exe, bash, zsh etc).
It will go throught several stages, printing some supplementary information
into your console. Do not worry about that, unless these are actually error
messages.

When it's done, you should see file named `export.qif` in the same folder.


## Errors / support

As this is a very first cut of the tool, errors to be expected - please **DO**
let me know of any issues you have with it.

Also please feel free to submit your ideas/improvement suggestions.


## Disclaimer

I am not affiliated in any way with this website, and this utility has not been
endorsed or banned by the company-operator of the website.

Please feel free to use it and report on any issues/bug/problems, yet you shall
agree beforehand that you are using this utility at your own risk - I accept
no liability whatsoever for anything what can possibly go wrong.
