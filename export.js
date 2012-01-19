#!/usr/bin/env node

var z = require('zombie')
  , fs = require('fs')

function error(e) {
    console.log(e)
}

function getCredentials(next) {

    fs.readFile('.credentials', function(err, data) {

        if (err) {
            next(err)
            return
        }

        var pair = data.toString('ascii').split('\n')

        if (pair.length < 2) {
            next('Wrong credentials file.')
            return
        }

        next(null, {username: pair[0], password: pair[1]})
    })
}

function logBrowserErrors(br) {

    if (br.errors.length === 0)
        return

    console.log('Browser errors for URL: ' + br.location._url.href)
    for (var i = 0; i < br.errors.length; i++) {
        console.dir(br.errors[i])
    }

}

function openLoginPage(next) {

    (new z()).visit('https://28degrees-online.gemoney.com.au/', function(e, br) {

        if (e) {
            next(e)
            return
        }

        logBrowserErrors(br)

        console.log(br.location._url)
        console.log(br.html())

        br.visit('https://28degrees-online.gemoney.com.au/access/login', function(e, br) {

            if (e) {
                next(e)
                return
            }

            logBrowserErrors(br)

            console.log(br.location._url)
            console.log(br.html())

            br.document.getElementById('AccessToken_Username').value = creds.username
            br.document.getElementById('AccessToken_Password').value = creds.password


            br.pressButton('[name|="SUBMIT"]', function(err, br) {
                if (err) {
                    next(err)
                    return
                }

                logBrowserErrors(br)

                console.log(br.location._url.href)
                console.log(br.html())

                if (br.html().indexOf('/access/login') !== -1) {
                    next('Error logging in, wrong credentials.')
                    return
                }

                console.log('Great success!')
            })

        })


    })
}

var creds = null

getCredentials(function(err, data) {

    if (err) {
        error(err)
        return
    }

    creds = data
    openLoginPage(function(err) {
        console.log(err)
    })
})
