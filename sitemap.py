__author__ = 'ejc84332'

#python
import logging
#ext
import crython


logging.basicConfig(filename='/opt/cascade-cron/cascade-cron/logs/stdout.log', filemod='w', level=logging.INFO)

@crython.job(second=range(0,60,10))
def foo():
    logging.info("Print info every 10 seconds to test supervisord")
    logging.warning("Print warning every 10 seconds to test supervisord")


if __name__ == '__main__':
    crython.tab.start()