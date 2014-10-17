__author__ = 'ejc84332'

#python
import logging
#ext
import crython


@crython.job(second=range(0,60,10))
def foo():
    logging.info("Print stuff every 10 seconds to test supervisord")


if __name__ == '__main__':
    crython.tab.start()