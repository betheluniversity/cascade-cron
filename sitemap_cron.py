# python
import time
import logging
import requests

# ext
import crython

# local
import sitemap
import config
from raven import Client
from github_connection import GH, template

# @crython.job(second=range(0,60,10))
# def foo():
#     with open('/var/www/staging/public/_testing/jmo/cron.txt', 'a') as f:
#         f.write("%s -- Print info every 10 seconds to test supervisord\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
#         print 'test'


client = Client(config.SENTRY_URL)

@crython.job(expr='@daily')
def sitemap_cron():
    try:
        sitemap.sitemap()
    except:
        client.captureException()


@crython.job(expr='@daily')
def load_humans_txt():

    gh = GH(config.GH_LOGIN)
    txt = gh.get_humans_text()

    with open(config.HUMANS_STAGING_FILE, "w") as text_file:
        text_file.write(txt)

    with open(config.HUMANS_PRODUCTION_FILE, "w") as text_file:
        text_file.write(txt)

if __name__ == '__main__':
    crython.tab.start()
    while True:
        # If you put Python to sleep crthon will still run.
        # Wake up every minute anyway?
        time.sleep(60)
