__author__ = 'ejc84332'

#python
import logging
#ext
import crython


logging.basicConfig(filename='/opt/cascade-cron/cascade-cron/logs/stdout.log', filemod='w', level=logging.INFO)


@crython.job(second=range(0,60,10))
def foo():
    with open('/var/www/staging/public/_testing/jmo/cron.txt', 'w') as f:
        f.write("Print info every 10 seconds to test supervisord")


if __name__ == '__main__':
    crython.tab.start()