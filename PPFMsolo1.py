#-------------------------------------------------------------------------------
# Name:        PPFMSolo
# Purpose:      Optimize the flight schedule, allowing C10 to be sched same day
#               as C990
# Author:      pbarkley
#
# Created:     24/05/2014
# Copyright:   (c) pbarkley 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from gurobipy import *
from datetime import date, datetime, time, timedelta

def solve(sprior, istart, sstart, icoeff, wcoeff, dcoeff, limitweight, maxweight, maxstuds, back2back, days, events, studs, insts, waves, planes, planetype, iavail, savail, pavail, syll, checks, stud1,onWingPairs,onWingInst, imax, iweight, sweight, iqual, squal):
    m = Model()
    #
    sevents ={}
    esd ={}
    for s in studs:
        for p in planes:
            if squal[s,p]==1:
                for d in days:
                    esd[s,d]=[]
                    for w in waves:
                        if pavail[p,d,w]==1:
                            for e in events:
                                if e>=syll[s]:
                                    if e<syll[s]+d:
                                        esd[s,d].append(e)
                                        sevents[s,p,d,w,e]=m.addVar(vtype=GRB.BINARY,name='sevent_'+ str(d) + '_' + str(w) +'_'+ p +'_'+ s + '_' + str(e)) #+1 to obj should be implied
                                    else:
                                        if e==10 and e==syll[s]+d:
                                            esd[s,d].append(e)
                                            sevents[s,p,d,w,e]=m.addVar(vtype=GRB.BINARY,name='sevent_'+ str(d) + '_' + str(w) +'_'+ p +'_'+ s + '_' + str(e))



    ievents = {}
    for i in insts:
        for p in planes:
            if iqual[i,p]==1:
                for d in days:
                    for w in waves:
                        if(pavail[p,d,w]==1):
                            ievents[i,p,d,w]=m.addVar(vtype=GRB.BINARY,name='ievent_'+ str(d) + '_' + str(w) +'_'+ p +'_'+ i)

    m.update()

    for (i,p,w) in istart:
        if pavail[p,1,w]:
            ievents[i,p,1,w].start = 1.0

    for (s,p,w,e) in sstart:
        if pavail[p,1,w]:
            if e>=syll[s] and e<syll[s]+1:
                sevents[s,p,1,w,e].start = 1.0 #e same?

    m.update()

    #Objective function: maximize # of student events less .01*(# of instructors scheduled)
    studexpr = LinExpr()
    instexpr = LinExpr()
    scoeff = {}

    scoeff[1]=5
    scoeff[2]=4
    scoeff[3]=3

    for d in days:
        for w in waves:
            for p in planes:
                if pavail[p,d,w,]==1:
                    for s in studs:
                        if squal[s,p]==1:
                            for e in events:
                                if e>=syll[s]:
                                    if e<syll[s]+d:
                                        studexpr.add(dcoeff[d]*wcoeff[w]*sprior[s]*sevents[s,p,d,w,e])
                                    else:
                                        if e==10 and e==syll[s]+d:
                                            studexpr.add(dcoeff[d]*wcoeff[w]*sprior[s]*sevents[s,p,d,w,e])
                    for i in insts:
                        if iqual[i,p]==1:
                            instexpr.add(icoeff[i,d,w]*ievents[i,p,d,w])
    m.setObjective(studexpr-0.1*instexpr,GRB.MAXIMIZE)

    #Back to back waves, but not three in a row
    if back2back:
        for i in insts:
            for d in days:
                for w in [1,2,3]:
                    expr = LinExpr()
                    for p in planes:
                        if iqual[i,p]==1 and pavail[p,d,w]==1:
                            expr.add(ievents[i,p,d,w])
                            if pavail[p,d,w+1]==1:
                                expr.add(ievents[i,p,d,w+1])
                                if pavail[p,d,w+2]==1:
                                    expr.add(ievents[i,p,d,w+2])
                    m.addConstr(expr<=2, 'noTriples_%s_%d_%d' % (i,d,w))
                for w in[1,2,3,4]:
                    for p in planes:
                        if iqual[i,p]==1 and pavail[p,d,w]==1:
                            expr = LinExpr()
                            for otherp in planes:
                                if iqual[i,otherp]==1 and pavail[otherp,d,w+1]==1 and otherp!=p:
                                    expr.add(ievents[i,otherp,d,w+1])
                            m.addConstr(ievents[i,p,d,w]+expr<=1,'samePlane_%s_%s_%d_%d' % (i,p,d,w))
                for w in waves:
                    expr = LinExpr()
                    for p in planes:
                        if iqual[i,p]==1 and pavail[p,d,w]==1:
                            expr.add(ievents[i,p,d,w])
                    m.addConstr(expr<=1,'onePlanePerWave_%s_%d_%d'%(i,d,w))



    #Each instructor gets scheduled for <= one plane for each set of adjacent waves in wavepairs
    if not back2back:
        wavepairs = [1,2,3,4]
    else:
        wavepairs = [2]

    for i in insts:
        for d in days:
            for w in wavepairs:
                expr = LinExpr()
                for p in planes:
                    if iqual[i,p]==1 and pavail[p,d,w]==1:
                        expr.add(ievents[i,p,d,w])
                        if pavail[p,d,w+1]==1:
                            expr.add(ievents[i,p,d,w+1])
                m.addConstr(expr <=1, 'Inst_No_Consecutive_Wave_%s_%d_%d' % (i,d,w))

    #Each plane get only 1 instructor per wave
    for p in planes:
        for d in days:
            for w in waves:
                if pavail[p,d,w]==1:
                    expr = LinExpr()
                    for i in insts:
                        if iqual[i,p]==1:
                            expr.add(ievents[i,p,d,w])
                    m.addConstr(expr <= 1, 'oneInstperPlane_%s_%d_%d' % (p,d,w))

    #Each student gets scheduled <= once each day for G1 to C8
    for s in studs:
        for d in days:
            expr = LinExpr()
            for p in planes:
                if squal[s,p]==1:
                    for w in waves:
                        for e in range(-3,10):
                            if pavail[p,d,w]==1 and e>=syll[s]:
                                if e<syll[s]+d:
                                    expr.add(sevents[s,p,d,w,e])
            m.addConstr(expr <= 1, 'onlyOneEvent_%s_%d' % (s,d))

    #If studs is scheduled for an on wing event (C1-C4, C6-C8, C10), schedule them with their on wing
    withonwing = [1, 2, 3, 4, 6, 7, 8, 10]
    eventname = {}
    eventname[5]="C590"
    eventname[9]="C990"
    eventname[0]="G490"
    eventname[-1]="G3"
    eventname[-2]="G2"
    eventname[-3]="G1"
    for s in studs:
        for e in withonwing:
            eventname[e]="C"+str(e)
            for d in days:
                if e>=syll[s]:
                    for p in planes:
                        if squal[s,p]==1:
                            for w in waves:
                                if pavail[p,d,w]==1:
                                    if e<syll[s]+d:
                                        m.addConstr(sevents[s,p,d,w,e] <= ievents[onWingInst[s],p,d,w],'withOnWing_%s_%s_%s__%d_%d_%d'%(s, onWingInst[s], p, d, w, e))
                                    else:
                                        if e==10 and e==syll[s]+d:
                                            m.addConstr(sevents[s,p,d,w,e] <= ievents[onWingInst[s],p,d,w],'withOnWing_%s_%s_%s__%d_%d_%d'%(s, onWingInst[s], p, d, w, e))

    for s in studs:
        for p in planes:
            if squal[s,p]==1:
                for d in days:
                    for w in waves:
                        if pavail[p,d,w]==1:
                            expr = LinExpr()
                            for e in esd[s,d]:
                                if e in withonwing:
                                    #print s, p, d, w, e
                                    expr.add(sevents[s,p,d,w,e])
                            #m.addConstr(expr<=ievents[onWingInst[s],p,d,w],'withOnWinge_%s_%s_%s__%d_%d'%(s, onWingInst[s], p, d, w))


    #C5 with off wing
    for s in studs:
        for p in planes:
            if squal[s,p]==1:
                for d in days:
                    for w in waves:
                        for e in events:
                            if e == 5 and e>=syll[s] and e<syll[s]+d and pavail[p,d,w] == 1:
                            #print('%s %s %s %s %s %s'% (s, i, p, w, syll[s], onWingInst[s,i]))
                                m.addConstr(sevents[s,p,d,w,e] <= quicksum(ievents[i,p,d,w] for i in insts if i != onWingInst[s] and iqual[i,p]==1),'C5_%s_%s_%d_%d'%(s,p,d,w))

    #Ground events with anyone
    withanyone = [-3, -2, -1, 0]
    for s in studs:
        for p in planes:
            if squal[s,p]==1:
                for d in days:
                    for w in waves:
                        for e in events:
                            if (e in withanyone)  and e>=syll[s] and e<syll[s]+d and pavail[p,d,w] == 1:
                                m.addConstr(sevents[s,p,d,w,e] - quicksum(ievents[i,p,d,w] for i in insts if iqual[i,p]==1) <= 0,'FlyWithInst_%s_%s_%d_%d'%(s,p,d,w))

    #C990 with non-onwing Check Instructor
    for s in studs:
        for p in planes:
            if squal[s,p]==1:
                for d in days:
                    for w in waves:
                        e = 9
                        if e>=syll[s] and e<syll[s]+d and pavail[p,d,w] == 1:
                                m.addConstr(sevents[s,p,d,w,e] - quicksum(ievents[i,p,d,w] for i in insts if iqual[i,p]==1 and checks[i]==1 and i!=onWingInst[s]) <= 0,
                                'C990_%s_%s_%d_%d'%(s,p,d,w))


    #If on wing student pair is scheduled for the same event, schedule them together
    for s1 in stud1:

            if(onWingPairs[s1]!='' and syll[s1]==syll[onWingPairs[s1]]):
                for p in planes:
                    if squal[s1,p]==1:
                        for d in days:
                            for w in waves:
                                for e in events:
                                    if e>=syll[s1] and pavail[p,d,w]==1:
                                        if e<syll[s1]+d:
                                            m.addConstr(sevents[s1,p,d,w,e]-sevents[onWingPairs[s1],p,d,w,e]==0,
                                            'OnWingsTogether_%s_%s_%s_%d_%d_%d'% (s1,onWingPairs[s1],p,d,w,e))
                                        else:
                                            if e==10 and e==syll[s1]+d:
                                                m.addConstr(sevents[s1,p,d,w,e]-sevents[onWingPairs[s1],p,d,w,e]==0,
                                                'OnWingsTogether_%s_%s_%s_%d_%d_%d'% (s1,onWingPairs[s1],p,d,w,e))


    #Each plane should have <= 2 students per block

    for p in planes:
        for d in days:
            for w in waves:
                if pavail[p,d,w]==1:
                    expr = LinExpr()
                    for s in studs:
                        if squal[s,p]==1:
                            for e in events:
                                if e >= syll[s]:
                                    if e<syll[s]+d:
                                        expr.add(sevents[s,p,d,w,e])
                                    else:
                                        if e==10 and e==syll[s]+d:
                                            expr.add(sevents[s,p,d,w,e])
                    m.addConstr(expr <= maxstuds,
                    'MaxStuds_%s_%d_%d' % (p,d,w))


    #Instructor availability constraint
    for i in insts:
        for d in days:
            for w in waves:
                if iavail[i,d,w]==0:
                    expr = LinExpr()
                    for p in planes:
                        if iqual[i,p]==1 and pavail[p,d,w]==1:
                            expr.add(ievents[i,p,d,w])
                    m.addConstr(expr==0,'instrNonAvailability_%s_%s_%d_%d' % (i,p,d,w))

    #Student availability constraint
    for s in studs:
        for d in days:
            for w in waves:
                if savail[s,d,w]==0:
                    expr = LinExpr()
                    for p in planes:
                        if squal[s,p]==1 and pavail[p,d,w]==1:
                            for e in events:
                                if e>=syll[s]:
                                    if e<syll[s]+d:
                                        expr.add(sevents[s,p,d,w,e])
                                    else:
                                        if e==10 and e==syll[s]+d:
                                            expr.add(sevents[s,p,d,w,e])
                    m.addConstr(expr==0,'studNonAvailability_%s_%s_%d_%d' % (s,p,d,w))

    #Don't schedule an instructor without a student
    for p in planes:
        for d in days:
            for w in waves:
                for i in insts:
                    if iqual[i,p]==1 and pavail[p,d,w]==1:
                        expr = LinExpr()
                        for s in studs:
                            if squal[s,p]==1:
                                for e in events:
                                    if e>=syll[s]:
                                        if e<syll[s]+d:
                                            expr.add(sevents[s,p,d,w,e])
                                        else:
                                            if e==10 and e==syll[s]+d:
                                                expr.add(sevents[s,p,d,w,e])
                        m.addConstr(ievents[i,p,d,w]<= expr, 'NoSoloInsts_%s_%s_%d_%d'%(i,p,d,w))

    #Don't Schedule nonactive students
    for s in studs:
        if syll[s] not in events:
            expr = LinExpr()
            for p in planes:
                if squal[s,p]:
                    for d in days:
                        for w in waves:
                            if pavail[p,d,w]:
                                for e in events:
                                    if e>=syll[s]:
                                        if e<syll[s]+d:
                                            expr.add(sevents[s,p,d,w,e])
                                        else:
                                            if e==10 and e==syll[s]+d:
                                                expr.add(sevents[s,p,d,w,e])
            m.addConstr(expr==0,'NonActive_Stud_%s'%(s))


    #Don't schedule an instructor for more than their max number of daily events
    for i in insts:
        for d in days:
            expr = LinExpr()
            for p in planes:
                if iqual[i,p]==1:
                    for w in waves:
                        if pavail[p,d,w]==1:
                            expr.add(ievents[i,p,d,w])
            m.addConstr(expr<= imax[i],'InstMaxEvents_%s_%d'%(i,d))

    #No fourth or fifth to first or second wave
    daypairs = days[:]
    del daypairs[-1]
    for s in studs:
        for d in daypairs:
            expr = LinExpr()
            for p in planes:
                if squal[s,p]==1:
                    for e in events:
                        if e>=syll[s] and e<syll[s]+d:
                            for w in [4,5]:
                                if pavail[p,d,w]:
                                    expr.add(sevents[s,p,d,w,e])
                            for w in [1,2]:
                                if pavail[p,d+1,w]:
                                    expr.add(sevents[s,p,d+1,w,e])
                        if e == syll[s]+d:
                            for w in[1,2]:
                                if pavail[p,d+1,w]:
                                    expr.add(sevents[s,p,d+1,w,e])
            m.addConstr(expr<=1,'ConsecutiveDays_%s_%d'%(s,d))

    #Each event is only scheduled once
    for s in studs:
        for e in events:
            if e >= syll[s]:
                expr = LinExpr()
                for d in days:
                    if e<syll[s]+d:
                        for w in waves:
                            for p in planes:
                                if squal[s,p]==1 and pavail[p,d,w]==1:
                                    expr.add(sevents[s,p,d,w,e])
                    else:
                        if e==10 and e==syll[s]+d:
                            for w in waves:
                                for p in planes:
                                    if squal[s,p]==1 and pavail[p,d,w]==1:
                                        expr.add(sevents[s,p,d,w,e])
                m.addConstr(expr<=1,'eventsScheduledOnce_%s_%d'%(s,e))

    #Events G1-C990 must be sequentially scheduled at least the day before
    eventpairs = events[:]
    del eventpairs[-1]
    del eventpairs[-1]
    for s in studs:
        for e in eventpairs:
            for d in daypairs:
                if e>=syll[s] and e<syll[s]+d:
                    expr1 = LinExpr()
                    expr2 = LinExpr()
                    for p in planes:
                        if squal[s,p]==1:
                            for d1 in range(1,d):
                                if d1>e-syll[s]:
                                    for w in waves:
                                        if pavail[p,d1,w]:
                                            expr1.add(sevents[s,p,d1,w,e])
                            for w in waves:
                                if pavail[p,d+1,w]:
                                    expr2.add(sevents[s,p,d+1,w,e+1])
                    #m.addConstr(expr1-expr2>=0,'sequentialEvents_%s_event_%d_day_%d'%(s,e,d))
                    m.addConstr(quicksum(sevents[s,p,d1,w,e] for p in planes for d1 in days for w in waves if squal[s,p]==1 and d1<=d and d1>e-syll[s] and pavail[p,d1,w])-quicksum(sevents[s,p,d+1,w,e+1] for p in planes for w in waves if squal[s,p]==1 and pavail[p,d+1,w])>=0,                                'sequentialEvents_%s_event_%d_day_%d'%(s,e,d))

    #C990 in a wave before C10
    e = 9
    for s in studs:
        for d in days:
            if e>=syll[s] and e<syll[s]+d:
                for w in [1,2,3,4,5]:
                    expr = LinExpr()
                    for d1 in range(1,d+1):
                        if e>=syll[s] and e<syll[s]+d1:
                            if d1==d:
                                for w1 in range(1,w):
                                    for p in planes:
                                        if squal[s,p]==1 and pavail[p,d1,w1]:
                                            expr.add(sevents[s,p,d1,w1,e])
                            else:
                                for w1 in waves:
                                    for p in planes:
                                        if squal[s,p]==1 and pavail[p,d1,w1]:
                                            expr.add(sevents[s,p,d1,w1,e])
                    soloexpr = LinExpr()
                    for p in planes:
                        if squal[s,p]==1 and pavail[p,d,w]:
                            soloexpr.add(sevents[s,p,d,w,e+1])
                    m.addConstr(expr-soloexpr>=0,'c990beforec10_%s_%d_%d'%(s,d,w))


    #Max plane weight
    #maxweight = 600
    if limitweight:
        for p in planes:
            for d in days:
                for w in waves:
                    if pavail[p,d,w]:
                        expr = LinExpr()
                        for s in studs:
                            if squal[s,p]==1:
                                for e in events:
                                    if e>=syll[s]:
                                        if e<syll[s]+d:
                                            expr.add(sweight[s]*sevents[s,p,d,w,e])
                                        else:
                                            if e==10 and e==syll[s]+d:
                                                expr.add(sweight[s]*sevents[s,p,d,w,e])
                        for i in insts:
                            if iqual[i,p]==1:
                                expr.add(iweight[i]*ievents[i,p,d,w])
                        m.addConstr(expr<=maxweight,'maxWeight_%s_%d_%d' % (p,d,w))




    m.params.timeLimit = 25

    m.update()
    m.params.simplexPricing = 3
    m.params.varBranch = 1
    m.params.cutPasses = 3
    #m.params.tuneResults = 1
    # Tune the model
    #m.tune()
    #if m.tuneResultCount > 0:
        # Load the best tuned parameters into the model
        #m.getTuneResult(0)
        # Write tuned parameters to a file
        #m.write('tune.prm')

    # Solve the model using the tuned parameters
    m.optimize()

    import xlsxwriter
    workbook = xlsxwriter.Workbook('output2.xlsx')
    worksheet = workbook.add_worksheet()


    planeoffsets = {}
    cumoffset = timedelta()
    takeoff = {}
    firsttakeoff = datetime.combine(date.today(),time(07,00))
    eventlength = timedelta(hours=2,minutes=30)
    brieflength = timedelta(hours=1)
    o=5
    maxoffsets=7
    for w in range(len(waves)):
        takeoff[waves[w]]=firsttakeoff+w*eventlength


    j=1
    worksheet.write(j,0,"Day")
    worksheet.write(j,1,"Wave")
    worksheet.write(j,2,"Brief")
    worksheet.write(j,3,"Takeoff")
    worksheet.write(j,4,"Land")
    worksheet.write(j,5,"Plane")
    worksheet.write(j,6,"Type")
    worksheet.write(j,7,"Instructor")
    worksheet.write(j,8,"Student")
    worksheet.write(j,9,"Event")
    worksheet.write(j,10,"Weight")
    for d in days:
        for w in waves:
            for p in planes:
                for i in insts:
                    if pavail[p,d,w]==1 and iqual[i,p]==1 and ievents[i,p,d,w].x==1:
                        k=1
                        eweight = iweight[i]
                        if w==1 or pavail[p,d,w-1]==0 or ievents[i,p,d,w-1].x==0:
                            for s in studs:
                                if squal[s,p]==1:
                                    for e in events:
                                        if (e>=syll[s] and e<syll[s]+d and sevents[s,p,d,w,e].x==1) or (e==10 and e==syll[s]+d and sevents[s,p,d,w,e].x==1):
                                            k=k+1
                                            eweight = eweight + sweight[s]
                                            worksheet.write(1+j,0,d)
                                            worksheet.write(1+j,1,w)
                                            if p not in planeoffsets:
                                                planeoffsets[p]=cumoffset
                                                cumoffset = timedelta(minutes=o)+cumoffset
                                                if cumoffset == timedelta(minutes=(o*maxoffsets)):
                                                    cumoffset = timedelta()
                                            thistakeoff=takeoff[w]+planeoffsets[p]
                                            brief = thistakeoff-brieflength
                                            thisland = thistakeoff+eventlength
                                            worksheet.write(1+j,2,brief.strftime("%H%M"))
                                            worksheet.write(1+j,3,thistakeoff.strftime("%H%M"))
                                            worksheet.write(1+j,4,thisland.strftime("%H%M"))
                                            worksheet.write(1+j,5,p)
                                            worksheet.write(1+j,6,planetype[p])
                                            worksheet.write(1+j,7,i)
                                            worksheet.write(1+j,8,s)
                                            worksheet.write(1+j,9,eventname[e])
                                            if k==3:
                                                worksheet.write(1+j,10,eweight)

                                            j=j+1
                        if w!=5 and pavail[p,d,w+1] and ievents[i,p,d,w+1].x==1:
                            k=1
                            eweight = iweight[i]
                            for s in studs:
                                if squal[s,p]==1:
                                    for e in events:
                                        if (e>=syll[s] and e<syll[s]+d and sevents[s,p,d,w+1,e].x==1) or (e==10 and e==syll[s]+d and sevents[s,p,d,w+1,e].x==1):
                                            k=k+1
                                            eweight = eweight + sweight[s]
                                            worksheet.write(1+j,0,d)
                                            worksheet.write(1+j,1,w+1)
                                            if p not in planeoffsets:
                                                planeoffsets[p]=cumoffset
                                                cumoffset = timedelta(minutes=o)+cumoffset
                                                if cumoffset == timedelta(minutes=(o*maxoffsets)):
                                                    cumoffset = timedelta()
                                            thistakeoff=takeoff[w+1]+planeoffsets[p]
                                            thisland = thistakeoff+eventlength
                                            worksheet.write(1+j,2,brief.strftime("%H%M"))
                                            worksheet.write(1+j,3,thistakeoff.strftime("%H%M"))
                                            worksheet.write(1+j,4,thisland.strftime("%H%M"))
                                            worksheet.write(1+j,5,p)
                                            worksheet.write(1+j,6,planetype[p])
                                            worksheet.write(1+j,7,i)
                                            worksheet.write(1+j,8,s)
                                            worksheet.write(1+j,9,eventname[e])
                                            if k==3:
                                                worksheet.write(1+j,10,eweight)
                                            j=j+1
    j=j+2
    for p in planes:
        if p in planeoffsets:
            worksheet.write(j,1,p)
            worksheet.write(j,2,str(planeoffsets[p]))
            j=j+1


    #m.printAttr('x')
    #m.printAttr('Slack')

