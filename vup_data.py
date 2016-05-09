from datetime import timedelta, datetime
from Flyer import Flyer
from Device import Device
from vup import VUP
from Job import Job


def main():
    # Initialize squadron
    d = 30
    v = VUP(days=d)
    v.tags = ['JO', 'DH', 'MPO', 'TC', 'CP', 'AC', 'IMPO', 'ITC', 'IP', 'OPS', 'GUAM', 'MUGU', 'JAX']
    createPilots(v)
    createTaccos(v)
    createOperators(v)

    # MCE
    missions = {'number': 15,
                'between': 48}
    mce_duties = {('AC', 1): {'AC', 'JAX'},
                  ('CP', 1): {'CP', 'JAX'},
                  ('TC', 1): {'TC', 'JAX'},
                  ('MPO', 2): {'MPO', 'JAX'}}
    mce = Job(missions, start=17, shifts=[10, 8, 9], duties=mce_duties)

    # Launch
    launch_duties = {('Launch', 2): {'AC', 'GUAM'}}
    launch = Job(missions, start=16, shifts=[10, 12, 7], duties=launch_duties)

    # Alert

    # Recover
    # Watch
    watch_duties = {('SDO', 1): {'JO', 'JAX'},
                    ('ASDO', 1): {'MPO', 'JAX'}}
    watch = Job(number=d, between=24, start=12, shifts=[6, 6, 6, 6], duties=watch_duties)

    # Ops
    workday = {'number': d,
               'between': 24,
               'start': 12,
               'shifts': [8]}
    ops_duties = {('SkedsO', 1): {'JO', 'OPS', 'JAX'},
                  ('SkedsE', 1): {'MPO', 'OPS', 'JAX'}}
    ops = Job(workday, duties=ops_duties)

    # Training
    training_duties = {('PilotTraining', 1): {'JO', 'IP', 'JAX'},
                       ('NFOTraining', 1): {'JO', 'ITC', 'JAX'},
                       ('MPOTraining', 1): {'IMPO', 'JAX'}}
    training = Job(workday, duties=training_duties)

    # Mission Planning
    mp_duties = {('MP_AC', 1): {'AC', 'JAX'},
                 ('MP_TC', 1): {'TC', 'JAX'},
                 ('MP_MPO', 2): {'MPO', 'JAX'}}
    mp = Job(workday, duties=mp_duties)

    # Maintenance
    maint_duties = {('MO', 1): {'DH', 'IP', 'MUGU'}}
    maint = Job(number=d, between=24, start=8, shifts=[12], duties=maint_duties)

    v.jobs = {mce, launch, watch, training, ops, mp, maint}
    v.buildSorties()
    errors = v.writeSchedule()
    if not errors:
        v.outputModel()

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
            if i == 23:
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
