#!/usr/bin/python
import os
import random
import time
from pipes import quote

# publish stats every 5 minutes
interval = 300

#wait a random time to avoid metric storms if we start in parallel
#through pdsh etc
random_wait = int(random.random() * interval)
print "Print sleeping for %s seconds" % (random_wait)
time.sleep(random_wait) 
print "Starting"

pscmd = 'ps -eo pid,user,state,pcpu,cputime,etime,pmem,vsize,rssize,comm --sort -pcpu'
gmetric = "/usr/bin/gmetric --name=%(NAME)s --type=string --dmax=600 --val=%(VAL)s"

while True:
    psout = os.popen(pscmd, 'r')
    headers = psout.next().strip().split()
    pcpuindex = headers.index('%CPU')

    psnum = 1
    sendmetric = os.popen('sh', 'w')
    for psline in psout:
        psinfo = zip(headers, psline.strip().split())
        if float(psinfo[pcpuindex][1]) < 0.1:
            break
        name = "ps-%i" % (psnum)
        val = ",".join(["=".join(pair) for pair in psinfo]) 
        gmetriccmd = gmetric % dict(NAME=name, VAL=quote(val))
        sendmetric.write(gmetriccmd + "\n")
        psnum = psnum + 1
    psout.close()
    sendmetric.close()
    print "Published %s records" % (psnum-1)
    print "Sleeping %s seconds" % (interval)
    time.sleep(interval)
