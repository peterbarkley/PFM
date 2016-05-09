
import mysql.connector
import sys
from Airfield import Airfield
from datetime import date, timedelta
verbose = True


def main():
    config = {}
    execfile(sys.argv[1], config)
    con = mysql.connector.connect(host=config['host'],
                                  port=config['port'],
                                  user=config['user'],
                                  passwd=config['password'],
                                  db=config['database'])
    cur = con.cursor(dictionary=True)

    """ Loop over days from 4/25/2016 until 8/21/2016.
    Sundays are blank schedules. Block 1 starts 5/30. Block 2 starts 6/27. Block 3 starts 7/25. """
    start = date(2016, 4, 25)
    end = date(2016, 8, 21)
    blocks = {1: date(2016, 5, 30), 2: date(2016, 6, 27), 3: date(2016, 7, 25)}
    d = start
    block = 0
    training_day = 1
    kesn = Airfield(identifier='KESN',
                    latitude=38.8052205,
                    longitude=-76.0690164,
                    elevation=22,
                    time_zone='US/Eastern')

    while d <= end:
        insertSchedule(d, block, training_day, kesn.getSun(date=d, local=True), cur)
        d += timedelta(days=1)
        if d.weekday() != 6:
            training_day += 1
        if block < 3 and d == blocks[block + 1]:
            block += 1
            training_day = 1

    con.commit()
    con.close()


def insertSchedule(d, block, training_day, sun, cur):
    if verbose:
        print 'Inserting schedule for day %s, block %s, td %s, sunrise %s, sunset %s' % \
              (d, block, training_day, sun['sunrise'].time(), sun['sunset'].time())
    blank = 0
    if d.weekday() == 6:
        blank = 1
    row = {'day': d, 'block': block, 'blank': 0, 'year': d.year, 'sunset': sun['sunset'].time(), 'sunrise': sun['sunrise'].time(),
           'training_day': training_day}
    cur.execute('INSERT INTO schedule (day, block_ID, year, training_day, sunrise, sunset, blank) '
                'VALUES (%(day)s, %(block)s, %(year)s, %(training_day)s, %(sunrise)s, %(sunset)s, %(blank)s)', row)


if __name__ == '__main__':
    main()
