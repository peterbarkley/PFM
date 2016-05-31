from datetime import timedelta, datetime
import csv
import math
from Flyer import Flyer
from Device import Device
from vup import VUP
from Job import Job


def main():
    # Initialize squadron
    d = 30
    """createPilots(v)
    createTaccos(v)
    createOperators(v)"""
    personnel = importmanning('manning.csv')
    # scenario = 'mm7_manning2_2shiftduty'

    # MCE
    missions = {'number': 15,
                'between': 48}
    mce_duties = {('MCE_AC', 1, 0.5): {'AC', 'JAX'},
                  ('MCE_CP', 1, 0.5): {'CP', 'JAX'},
                  ('MCE_TC', 1, 1.0): {'TC', 'JAX'},
                  ('MCE_MPO', 2, 1.0): {'MPO', 'JAX'}}
    mce1 = Job(missions, start=17, shifts=[(3, 7), (0, 8), (1, 9)], duties=mce_duties)
    mce2 = Job(missions, start=17, shifts=[(3, 6), (0, 6), (0, 6), (0, 6)], duties=mce_duties)

    floater_duties = {('MCE_CP', 1, 0.33): {'CP', 'JAX'}}
    mce3_duties = {('MCE_AC', 1, 0.67): {'AC', 'JAX'},
                  ('MCE_TC', 1, 1.0): {'TC', 'JAX'},
                  ('MCE_MPO', 2, 1.0): {'MPO', 'JAX'}}

    mce3 = Job(missions, start=17, shifts=[(3, 6), (0, 6), (0, 6), (0, 6)], duties=mce3_duties)
    floater = Job(missions, start=20, shifts=[(0, 12), (0, 12)], duties=floater_duties)

    # Launch
    launch_duties = {('Launch', 2, 1.0): {'AC', 'GUAM'}}
    launch = Job(missions, start=16, shifts=[(8.5, 1.5), (12, 0), (8.5, 1.5)], duties=launch_duties)

    # Alert

    # Annuals
    n = math.ceil(len(personnel)*0.0896)
    annual_duties = {('Flight_Physical', n, 0.0): {'JAX'}}
    annual = Job(number=1, between=24*d, start=48, shifts=[(4, 0)], duties=annual_duties)

    # Watch
    watch_duties = {('Duty_SDO', 1, 0.0): {'JO', 'JAX'},
                    ('Duty_ASDO', 1, 0.0): {'MPO', 'JAX'}}
    watch4 = Job(number=d, between=24, start=12, shifts=[(6, 0), (6, 0), (6, 0), (6, 0)], duties=watch_duties)
    watch3 = Job(number=d, between=24, start=12, shifts=[(8, 0), (8, 0), (8, 0)], duties=watch_duties)
    watch2 = Job(number=d, between=24, start=12, shifts=[(12, 0), (12, 0)], duties=watch_duties)
    # Ops
    workday = {'number': d / 7,
               'between': 24*7,
               'start': 12,
               'shifts': [(8, 0), (8, 0), (8, 0), (8, 0), (8, 0)],
               'btshifts': 24}
    ops_duties = {('SkedsO', 1, 0.0): {'JO', 'OPS', 'JAX'},
                  ('SkedsE', 1, 0.0): {'MPO', 'OPS', 'JAX'}}
    ops = Job(workday, duties=ops_duties)

    # DH Duties
    dh_duties = {('DH_stuff', 2, 0.0): {'DH', 'JAX'}}
    dh = Job(workday, duties=dh_duties)

    # Training
    training_duties = {('Training_IP', 1, 0.0): {'JO', 'IP', 'JAX'},
                       ('Training_ITC', 1, 0.0): {'JO', 'ITC', 'JAX'},
                       ('Training_IMPO', 1, 0.0): {'IMPO', 'JAX'}}
    training = Job(workday, duties=training_duties)

    # Mission Planning
    mp_duties = {('MP_AC', 1, 0.0): {'AC', 'JAX'},
                 ('MP_TC', 1, 0.0): {'TC', 'JAX'},
                 ('MP_MPO', 2, 0.0): {'MPO', 'JAX'}}
    mp = Job(workday, duties=mp_duties)

    # Maintenance
    maint_duties = {('MO', 1, 0.0): {'DH', 'IP', 'MUGU'}}
    maint = Job(number=d, between=24, start=8, shifts=[(12,0)], duties=maint_duties)

    """for p in v.personnel:
        print p.id, ' '.join(p.tags)"""
    scenarios = {  # 'mm5': {annual, mce3, floater, watch4, training, ops, mp, dh},
                 # 'mm6': {annual, mce1, watch4, training, ops, mp, dh},
                 'mm5_3duty': {annual, mce3, floater, watch3, training, ops, mp, dh},
                 'mm5_2duty': {annual, mce3, floater, watch2, training, ops, mp, dh}}
    for scenario in scenarios:
        print "Running ", scenario
        v = VUP(days=d, start=datetime(year=2016, month=6, day=1))
        v.tags = ['JO', 'DH', 'MPO', 'TC', 'CP', 'AC', 'IMPO', 'ITC', 'IP', 'OPS', 'GUAM', 'MUGU', 'JAX']
        v.personnel = personnel
        v.jobs = scenarios[scenario]  # , maint}
        v.buildSorties()
        errors = v.writeSchedule()
        if not errors:
            createschedule(scenario, v)

def createschedule(scenario, v):
    with open(scenario+'.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)
        stats = ['ave_flight_hours', 'ave_total_hours', 'ave_training_days', 'ave_days_not_scheduled', 'ave_free_days']
        writer.writerow([scenario])
        writer.writerow([])
        writer.writerow(['group'] + stats)
        for group in v.summary:
            row = ['_'.join(group)]
            for stat in stats:
                row.append(v.summary[group][stat])
            writer.writerow(row)

        writer.writerow([])
        writer.writerow(['Start', 'Stop', 'Duty', 'Person', 'Length'])
        # writer.writerow(['Date', 'Start', 'Stop', 'Duty', 'Person', 'Requirements'])
        for line in v.schedule:
            # writer.writerow([line['start'].date(), line['start'].time(), line['stop'].time(), line['duty'], line['person'], line['tags']])
            length = line['stop'] - line['start']

            writer.writerow([line['start'], line['stop'], line['duty'], line['person'], length.seconds/3600])


def importmanning(name):
    personnel = set()
    with open(name, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            f = Flyer(id=row[0])
            tags = set()
            for i in range(1,6):
                if row[i] is not None:
                    tags.add(row[i])
            if 'IP' in tags:
                tags.add('AC')
            if 'AC' in tags:
                tags.add('CP')
            elif 'ITC' in tags:
                tags.add('TC')
            elif 'IMPO' in tags:
                tags.add('MPO')

            f.tags = tags
            personnel.add(f)
    return personnel

# Create Pilots
def createPilots(v):

    for i in range(1, 24):
        tags = {'CP', 'AC'}
        # IP
        if i < 4:
            tags.add('IP')
        elif i < 6:
            tags.add('OPS')

        if i < 20:
            tags.add('JO')
        else:
            tags.add('DH')
            if i == 20:
                tags.add('IP')

        if 10 < i < 15:
            tags.add('GUAM')
        elif i == 20:
            tags.add('MUGU')
        else:
            tags.add('JAX')

        n = 'P'+str(i)
        p = Flyer(id=n, squadron=v)
        p.tags = tags
        v.personnel.add(p)


# Create Taccos
def createTaccos(v):
    for i in range(1, 11):
        tags = {'TC', 'JAX'}
        n = 'TC'+str(i)
        if i < 3:
            tags.add('DH')
            if i == 1:
                tags.add('ITC')
        elif i < 5:
            tags.add('ITC')
            tags.add('JO')
        elif i < 7:
            tags.add('OPS')
            tags.add('JO')
        else:
            tags.add('JO')

        t = Flyer(id=n, squadron=v)
        t.tags = tags
        v.personnel.add(t)


# Create MPOs
def createOperators(v):
    for i in range(1, 20):
        tags = {'MPO', 'JAX'}
        if i < 5:
            tags.add('IMPO')
        elif i < 9:
            tags.add('OPS')

        n = 'MPO'+str(i)
        t = Flyer(id=n, squadron=v)
        t.tags = tags
        v.personnel.add(t)


if __name__ == '__main__':
    main()
