__author__ = 'ejc84332'

#python

#ext
import crython


@crython.job(second=range(0,60,10))
def foo():
    print "Print stuff every 10 seconds to test supervisord"


if __name__ == '__main__':
    crython.tab.start()