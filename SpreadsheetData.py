#-------------------------------------------------------------------------------
# Name:        PPFMSoloData
# Purpose:     Import the data for PPFMSolo, call the optimization,
#               open the output file
# Author:      peter barkley
#
# Created:     24/05/2014
# Copyright:   (c) peter barkley 2014
# Licence:
#-------------------------------------------------------------------------------

import os
import xlrd
import sys
from datetime import date, datetime, time, timedelta
from Squadron import Squadron
from Schedule import Schedule
from Sniv import Sniv
from Flyer import Flyer
from Instructor import Instructor
from Student import Student
from Event import Event
from Sortie import Sortie
from StudentSortie import StudentSortie
from Plane import Plane

from gurobipy import *

def main():
    """This imports squadron data from a .xlsx spreadsheet and exports an optimized schedule to a .xlsx spreadsheet.
    The first argument is the data import spreadsheet.
    The second argument is the data export spreadsheet."""
    if(len(sys.argv)==1):
        print "Using Sample Data"
        importName = "SampleData.xlsx"
        outputName = "SampleOutput.xlsx"
    elif(len(sys.argv)==2):
        print "Printing to SampleOutput.xlsx"
        importName = sys.argv[1]
        outputName = "SampleOutput.xlsx"
    else:
        importName = sys.argv[1]
        outputName = sys.argv[2]

    vtna = Squadron() #Create a squadron object to hold the data
    load(vtna,importName) #Import data from a spreadsheet into the squadron class

    vtna.writeSchedules()

    print "Schedule written"
    #export(vtna,outputName)

def load(vtna,importName):

    book = xlrd.open_workbook(importName)
    sh = book.sheet_by_name("Multi")

    #vtna = Squadron() #Create a squadron object to hold the data

    dates = [date(2015,3,27),date(2015,3,28),date(2015,3,29)] #Dates to write schedules for. Should be passed via sys.argv Assume unlisted gap dates are blank schedules.
    #Dealing with blank schedules needs more work. Schedules need to know if crew rests constraints apply from the previous day
    i=1
    for day in dates:
        sked=Schedule(day)
        sked.flyDay = i
        vtna.schedules[i]=sked
        i=i+1
    vtna.totalFlightDays = len(dates)
    #Creates the events in the syllabus. Would be replaced by call to data if necessary.
    for i in range(-3,11):
        e = Event(i)
        if i > -3:
            vtna.syllabus[i-1].followingEvents.add(e)
            e.precedingEvents.add(vtna.syllabus[i-1])
        if i>0:
            e.flightHours=1.0
            if i != 5 and i !=9:
                e.onwing=True
        vtna.syllabus[i]=e

    vtna.syllabus[-3].initialEvent = True
    vtna.syllabus[5].offwing=True
    vtna.syllabus[9].offwing=True
    vtna.syllabus[9].check=True
    vtna.syllabus[10].followsImmediately=True
    #Could modify any schedule data for any day as necessary

    """days = range(1,numdays+1)
    events = range(-3,11)
    numwaves = int(sh.cell_value(0,1))
    waves = range(1,numwaves+1)
    maxstuds = int(sh.cell_value(3,1))
    maxweight = int(sh.cell_value(4,1))
    limitweight = int(sh.cell_value(5,2))
    dcoeff = {}
    wcoeff = {}
    icoeff = {}

    for d in days:
        dcoeff[d]=float(sh.cell_value(7+d,8))
    for w in waves:
        wcoeff[w]=float(sh.cell_value(7+w,5))
    #maxstuds = {}
    #i=8
    #for e in events:
    #    maxstuds[e] = int(sh.cell_value(i,2))
    #    i = i+1"""

    sh = book.sheet_by_name("pavail")
    """planes = []
    pavail = {}
    planetype = {}"""
    j=2
    while True:
            try:
                plane = sh.cell_value(j,0)
                plane = plane.encode('utf8')
                #planes.append(plane)
                p = Plane(plane)
                p.planetype = sh.cell_value(j,1).encode('utf8')
                vtna.planes[plane]=p
                j = j+1
            except IndexError:
                break

    print "Planes loaded"
    i=2
    for p in vtna.planes:
        plane = vtna.planes[p]
        d=0
        for day in vtna.schedules:
            plane._available[day]={}
            j=2
            for w in vtna.schedules[day].waves:
                wave = vtna.schedules[day].waves[w]
                if int(sh.cell_value(i,5*d+j)) == 1:
                    plane._available[day][wave]=True
                else:
                    plane._available[day][wave]=False
                j=j+1
            d=d+1
        i=i+1
                #pavail[planes[i],days[d],waves[j]]=int(sh.cell_value(i+2,5*d+j+2))
    print "Plane availability loaded"

    sh = book.sheet_by_name("inst")
    """insts = []
    imax = {}
    check = {}
    iweight = {}
    iqual = {}
    itype = {}"""
    i = 1
    while True:
        try:
            inst = sh.cell_value(i, 0)
            inst = inst.encode('utf8')
            #insts.append(inst)
            vtna.instructors[inst]=Instructor(inst)
            #imax[inst]= int(sh.cell_value(i,1))
            vtna.instructors[inst].maxEvents=int(sh.cell_value(i,1))
            #check[inst]=int(sh.cell_value(i,2))
            vtna.instructors[inst].check = int(sh.cell_value(i,2))
            #iweight[inst]=int(sh.cell_value(i,3))
            vtna.instructors[inst].weight = int(sh.cell_value(i,3))
            if (int(sh.cell_value(i,4))==1):
                vtna.instructors[inst].quals.append('C-172-N')
                vtna.instructors[inst].quals.append('C-172-SP')
                vtna.instructors[inst].quals.append('C-172')
            if (int(sh.cell_value(i,5))==1):
                vtna.instructors[inst].quals.append('PA-28')
            """
            itype[inst,'C-172-SP'] = int(sh.cell_value(i,4))
            itype[inst,'C-172-N'] = int(sh.cell_value(i,4))
            itype[inst,'PA-28'] = int(sh.cell_value(i,5))
            #pc = 4
            for p in planes:
                if itype[inst,planetype[p]]==1:
                    iqual[inst,p] = 1
                else:
                    iqual[inst,p] = 0
            #    pc = pc+1"""
            i = i + 1
        except IndexError:
            break

    print "Instructors loaded"
    sh = book.sheet_by_name("stud")
    """
    studs = []
    syll = {}
    sweight = {}
    squal = {}
    sprior = {}"""
    i = 1
    while True:
        try:
            stud = sh.cell_value(i,0)
            stud = stud.encode('utf8')
            #studs.append(stud)
            vtna.students[stud]=Student(stud,vtna)
            #syll[stud]=int(sh.cell_value(i,1))
            eventID = int(sh.cell_value(i,1))
            vtna.students[stud].nextEvent = vtna.syllabus[eventID]
            if eventID > -3:
                vtna.students[stud].scheduledEvents.add(vtna.syllabus[eventID-1])
            for x in range(-3,eventID-1):
                vtna.students[stud].completedEvents.add(vtna.syllabus[x])
            #sweight[stud]=int(sh.cell_value(i,2))
            vtna.students[stud].weight = int(sh.cell_value(i,2))
            vtna.students[stud].quals.append(sh.cell_value(i,3).encode('utf8'))
            """stype = sh.cell_value(i,3)
            stype = stype.encode('utf8')
            sprior[stud] = int(sh.cell_value(i,4))
            for p in planes:
                #print p
                if planetype[p]==stype:
                    squal[stud,p] = 1
                else:
                    squal[stud,p] = 0
            #    pc = pc+1"""
            i=i+1
        except IndexError:
            break

    print "Students loaded"

    """
    sh = book.sheet_by_name("iavail")
    iavail = {}
    for i in range(len(insts)):
        for d in range(len(days)):
            for w in range(len(waves)):
                iavail[insts[i],days[d],waves[w]] = int(sh.cell_value(i+2,5*d+w+1))



    sh = book.sheet_by_name("ipref")
    for i in range(len(insts)):
        for d in range(len(days)):
            for w in range(len(waves)):
                icoeff[insts[i],days[d],waves[w]] = int(sh.cell_value(i+2,5*d+w+1))

    sh = book.sheet_by_name("savail")
    savail = {}
    for s in range(len(studs)):
        for d in range(len(days)):
            for w in range(len(waves)):
                savail[studs[s], days[d], waves[w]]= int(sh.cell_value(s+2,5*d+w+1))


    stud1 = []
    onwingpair = {}
    onwinginst = {}
    """
    sh = book.sheet_by_name("onwing")
    i = 1
    while True:
        try:
            stud = sh.cell_value(i,0)
            stud=stud.encode('utf8')
            #stud1.append(stud)
            pair = sh.cell_value(i,1)
            pair = pair.encode('utf8')
            instructor = sh.cell_value(i,3).encode('utf8')
            #onwinginst[stud] = instructor
            #onwinginst[pair] = instructor
            vtna.students[stud].onwing = vtna.instructors[instructor]
            #onwingpair[stud]=pair
            if (pair != ''):
                vtna.students[stud].partner = vtna.students[pair]
                vtna.students[pair].partner = vtna.students[stud]
                vtna.students[pair].onwing = vtna.instructors[instructor]
            #t = sh.cell_value(i,2)
            #t = t.encode('utf8')
            #squal[stud]=t
            #squal[pair]=t
            i=i+1
        except IndexError:
            break

    #istart = []
    #sstart = []
    sh = book.sheet_by_name("start")
    i=0
    while True:
        try:
            wave = int(sh.cell_value(i,0))
            plane = sh.cell_value(i,4).encode('utf8')
            inst = sh.cell_value(i,6).encode('utf8')
            stud = sh.cell_value(i,7).encode('utf8')
            event = int(sh.cell_value(i,9))
            #istart.append((inst,plane,wave))
            #sstart.append((stud,plane,wave,event))
            vtna.students[stud].last['wave']=wave
            vtna.students[stud].last['plane']=plane
            vtna.instructors[inst].last['wave']=wave
            vtna.instructors[inst].last['plane']=plane
            s = Sortie()
            s.instructor = vtna.instructors[inst]
            s.plane = vtna.planes[plane] #Plane id
            s.wave = vtna.today.waves[wave] #Wave id
            ss = StudentSortie
            ss.student=vtna.students[stud]
            ss.event=event
            s.studentSorties.append(ss)
            vtna.today.sorties.append(s)
            i=i+1
        except IndexError:
            break

    print "Ending load"
    """
    #import PPFMsolo1
    #for i in range(1,28):
    #    days=range(1,i+1)
    #    print i;
    #PPFMsolo1.solve(sprior, istart, sstart, icoeff, wcoeff, dcoeff, limitweight, maxweight, maxstuds, back2back, days, events, studs, insts, waves, planes, planetype, iavail, savail, pavail, syll, check, stud1, onwingpair, onwinginst, imax, iweight, sweight, iqual, squal)
    """
def export(vtna, outputName):
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

    os.system("start excel.exe \"C:\Users\pbarkley\Google Drive\PFP\output2.xlsx\"")


if __name__ == "__main__":
    main()