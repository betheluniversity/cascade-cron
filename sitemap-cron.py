__author__ = 'ejc84332'

#python
import time
import logging

#ext
import crython
#local
import sitemap


# @crython.job(second=range(0,60,10))
# def foo():
#     with open('/var/www/staging/public/_testing/jmo/cron.txt', 'a') as f:
#         f.write("%s -- Print info every 10 seconds to test supervisord\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
#         print 'test'


@crython.job(expr='@daily')
def sitemap_cron():
    sitemap.sitemap()
    logging.info("sitemap done")


if __name__ == '__main__':
    crython.tab.start()
    while True:
        ##If you put Python to sleep crthon will still run.
        ##Wake up every minute anyway?
        time.sleep(60)