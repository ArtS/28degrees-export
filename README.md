
# Export to QIF/CSV from 28degrees Master Card website


## Description

This utility logs into https://28degrees-online.gemoney.com.au website, using
your username and password, and simply grabs all your transactions from there,
saving them into QIF file.


## Installation

You will need some things for this tool to work:

1. Python
1. WebDriver
1. Selenium

On OS X, you can use `brew` to install N 2 & 3 by:

    `brew install chromedriver`
    `pip install selenium`

As installation instructions for the things above vary for different platforms,
I assume you know how install them, otherwise please let me know and I'll
extend this section with detailed steps for your platform.

## Usage

Simply start `export.py` in your shell of choice (cmd.exe, bash, zsh etc).
You will be prompted for your username & password. **THESE details will not be
used for anything but logging into the 28degrees' website.**

Then the tool will go through several stages, printing some supplementary information
into console. Do not worry about that unless these are actually error
messages.

When it's done, you should see file that looks like `YYYY.MM.DD-YYYY.MM.DD.qif` under
the 'export' folder, where YYYY.DD.MM are the dates for the first and last transactions
in the exported dataset. It will also create a transactions.db file (sqlite database) but
you can ignore this one - we simply need it to keep track of transactions that have already
been recorded.

If you want to re-start the process, just delete (or re-name, which is safer) transactions.db file.

Should you want a copy of all the statements on the website, add the `--statements` argument
when calling `export.py` and a PDF copy of each available statement will be saved after the
transactions process is complete. Statements will be saved as `28 Degrees Statement YYYY-MM-DD.pdf`
to the 'export' folder. After `export.py` has finished running you can safely copy the
files from the 'export' folder. However if you *move* the files subsequent runs of
`export.py` will result in the downloading of each statement again as the check to download
missing statements is based on the existence of PDFs in the 'export' folder.

## Errors / support

As this is a very first and rough cut of the tool, errors to be expected - please **DO**
let me know of any issues you have with it.

Also please feel free to submit your ideas/improvement suggestions.


## Disclaimer

I am not affiliated in any way with this website, and this utility has not been
endorsed or banned by the company-operator of the website.

Please feel free to use it and report on any issues/bug/problems, yet you shall
agree beforehand that you are using this utility at your own risk - I accept
no liability whatsoever for anything what can possibly go wrong.
