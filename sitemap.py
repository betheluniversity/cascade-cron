__author__ = 'ejc84332'

#python
import logging
import time

#ext
import crython


@crython.job(second=range(0,60,10))
def foo():
    with open('/var/www/staging/public/_testing/jmo/cron.txt', 'a') as f:
        f.write("%s -- Print info every 10 seconds to test supervisord\n" % time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == '__main__':
    crython.tab.start()
    while True:
        time.sleep(60)