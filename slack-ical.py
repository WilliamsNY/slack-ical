#!/usr/bin/python

import os
from icalendar import Calendar
import icalendar
from datetime import datetime
from datetime  import timedelta
import logging
import json

# Import requests and set it up to use cache
import requests
from httpcache import CachingHTTPAdapter
s = requests.Session()
s.mount('http://', CachingHTTPAdapter())
s.mount('https://', CachingHTTPAdapter())
###

cachefile='/tmp/slackical.cache'

slackwebhookurl=os.environ.get('SLACK_WEBHOOKURL', 'https://hooks.slack.com/services/[YOUR]/[URL]/[HERE]')

channelFeeds = [
    {
        'botName': os.environ.get('SLACK_BOTNAME', 'Slack Bot'),
        'botEmoji': os.environ.get('SLACK_BOTEMOJI', ':medal:'),
        'calFeed': os.environ.get('SLACK_CALFEED', 'http://[YOUR_ICAL_URL]'),
        'channel': os.environ.get('SLACK_CHANNEL', '#yourchannel_or_@privatemessage')
    }
]

def getFeed(calFeed):
    message = ""
    date = ""
    headers = {
        'Cache-Control':    'no-cache',
        'Pragma':           'no-cache',
    }

    requests.packages.urllib3.disable_warnings()
    r = requests.get(calFeed, headers=headers)

    if r.status_code == 304:
        # read from cached file
        cf=open(cachefile, 'r')
        caldata=cf.read()
    else:
        caldata=r.content
        cf=open(cachefile, 'w')
        cf.write(caldata)
        cf.close()

    todayDates=[]
    tomorrowDates=[]
    thisWeekDates=[]

    cal = Calendar.from_ical(caldata)
    for event in cal.walk('VEVENT'):
        message=event.get('SUMMARY')
        date=event.get('DTSTART').dt
        if date == datetime.today().date():
            todayDates.append({'Line': message, 'Date': date})
        elif date == datetime.today().date() + timedelta(days=1):
            tomorrowDates.append({'Line': message, 'Date': date})
        elif date <= datetime.today().date() + timedelta(days=7):
            thisWeekDates.append({'Line': message, 'Date': date})
    return [ todayDates, tomorrowDates, thisWeekDates ]

def getSlackMessage (todayDates, tomorrowDates, thisWeekDates):
    message="*Today* (" + datetime.today().strftime("%A") + "):\n"
    if len(todayDates) > 0:
        for line in todayDates:
            message = message + "    " + line['Line']  + "\n"
    else:
        message = message + "    " + "_-none-_\n"

    message = message + "\n*Tomorrow:*\n"
    if len(tomorrowDates) > 0:
        for line in tomorrowDates:
            message = message + "    " + line['Line'] + "\n"
    else:
        message = message + "    " + "_-none-_\n"

    message = message + "\n*This Week:*\n"
    if len(thisWeekDates) > 0:
        for line in thisWeekDates:
            message = message + "    " + line['Line'] + " _(" + line['Date'].strftime("%A %B %-d, %Y") + ")_\n"
    else:
        message = message + "    " + "_-none-_\n"

    return message

### Begin main

for feed in channelFeeds:
    todayDates, tomorrowDates, thisWeekDates = getFeed(feed['calFeed'])
    message = getSlackMessage(todayDates, tomorrowDates, thisWeekDates)

    slackMessage = {
        'username':   feed['botName'],
        'icon_emoji': feed['botEmoji'],
        'channel':    feed['channel'],
        'text':       message,
    }

    r = requests.post(slackwebhookurl, data=json.dumps(slackMessage))
