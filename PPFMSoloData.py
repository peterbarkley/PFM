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

from gurobipy import *

book = xlrd.open_workbook("SampleData.xlsx")

back2back=True
sh = book.sheet_by_name("Multi")

numdays = 3
days = range(1,numdays+1)
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
#    i = i+1

sh = book.sheet_by_name("pavail")
planes = []
pavail = {}
planetype = {}
j=2
while True:
        try:
            plane = sh.cell_value(j,0)
            plane = plane.encode('utf8')
            planes.append(plane)
            planetype[plane] = sh.cell_value(j,1).encode('utf8')
            j = j+1
        except IndexError:
            break

for i in range(len(planes)):
    for d in range(len(days)):
        for j in range(len(waves)):
            pavail[planes[i],days[d],waves[j]]=int(sh.cell_value(i+2,5*d+j+2))

sh = book.sheet_by_name("inst")
insts = []
imax = {}
check = {}
iweight = {}
iqual = {}
itype = {}
i = 1
while True:
    try:
        inst = sh.cell_value(i, 0)
        inst = inst.encode('utf8')
        insts.append(inst)
        imax[inst]= int(sh.cell_value(i,1))
        check[inst]=int(sh.cell_value(i,2))
        iweight[inst]=int(sh.cell_value(i,3))
        itype[inst,'C-172-SP'] = int(sh.cell_value(i,4))
        itype[inst,'C-172-N'] = int(sh.cell_value(i,4))
        itype[inst,'PA-28'] = int(sh.cell_value(i,5))
        #pc = 4
        for p in planes:
            if itype[inst,planetype[p]]==1:
                iqual[inst,p] = 1
            else:
                iqual[inst,p] = 0
        #    pc = pc+1
        i = i + 1
    except IndexError:
        break

sh = book.sheet_by_name("stud")
studs = []
syll = {}
sweight = {}
squal = {}
sprior = {}
i = 1
while True:
    try:
        stud = sh.cell_value(i,0)
        stud = stud.encode('utf8')
        studs.append(stud)
        syll[stud]=int(sh.cell_value(i,1))
        sweight[stud]=int(sh.cell_value(i,2))
        stype = sh.cell_value(i,3)
        stype = stype.encode('utf8')
        sprior[stud] = int(sh.cell_value(i,4))
        #pc=3
        #print stud
        #print stype
        for p in planes:
            #print p
            if planetype[p]==stype:
                squal[stud,p] = 1
            else:
                squal[stud,p] = 0
        #    pc = pc+1
        i=i+1
    except IndexError:
        break

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
sh = book.sheet_by_name("onwing")
i = 1
while True:
    try:
        stud = sh.cell_value(i,0)
        stud=stud.encode('utf8')
        stud1.append(stud)
        pair = sh.cell_value(i,1)
        pair = pair.encode('utf8')
        onwingpair[stud]=pair
        t = sh.cell_value(i,2)
        t = t.encode('utf8')
        #squal[stud]=t
        #squal[pair]=t
        instructor = sh.cell_value(i,3)
        onwinginst[stud] = instructor.encode('utf8')
        onwinginst[pair] = instructor.encode('utf8')
        i=i+1
    except IndexError:
        break

istart = []
sstart = []
sh = book.sheet_by_name("start")
i=1
while True:
    try:
        wave = int(sh.cell_value(i,0))
        plane = sh.cell_value(i,4).encode('utf8')
        inst = sh.cell_value(i,6).encode('utf8')
        stud = sh.cell_value(i,7).encode('utf8')
        event = int(sh.cell_value(i,9))
        istart.append((inst,plane,wave))
        sstart.append((stud,plane,wave,event))
        i=i+1
    except IndexError:
        break

import PPFMsolo1
#for i in range(1,28):
#    days=range(1,i+1)
#    print i;
PPFMsolo1.solve(sprior, istart, sstart, icoeff, wcoeff, dcoeff, limitweight, maxweight, maxstuds, back2back, days, events, studs, insts, waves, planes, planetype, iavail, savail, pavail, syll, check, stud1, onwingpair, onwinginst, imax, iweight, sweight, iqual, squal)

os.system("start excel.exe \"C:\Users\pbarkley\Google Drive\PFP\output2.xlsx\"")