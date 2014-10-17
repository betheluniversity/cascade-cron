__author__ = 'ejc84332'

#python
import sys
import time

#ext
import crython

##sitemap is in Tinker until the Cascade tols are more modular. Add it to the sys path so we can import
sys.path.append('/opt/tinker')



@crython.job(second=range(0,60,10))
def foo():
    with open('/var/www/staging/public/_testing/jmo/cron.txt', 'a') as f:
        f.write("%s -- Print info every 10 seconds to test supervisord\n" % time.strftime("%Y-%m-%d %H:%M:%S"))


@crython.job(expr='@minutely')
def sitemap():
    import sitemap
    print "import done"

if __name__ == '__main__':
    crython.tab.start()
    while True:
        ##If you put Python to sleep crthon will still run.
        ##Wake up every minute anyway?
        time.sleep(60)