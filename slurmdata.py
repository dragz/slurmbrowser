import os
import sys
import csv
import StringIO
import datetime as dt
from urllib2 import urlopen
from pipes import quote

# quick fix for locating install dir when running under apache
if not __name__ == "__main__":
  sys.path.append(os.path.dirname(__file__))
  os.chdir(os.path.dirname(__file__))
from bottle import route, run, static_file, request, response, default_app
from hostlist import expand_hostlist



@route('/html/<filename>')
def server_static(filename):
    return static_file(filename, root='.')

def convert(a):
    b = a.strip()
    if b.isdigit():
        return int(b)
    try:
        return float(b)
    except ValueError:
        return b

def get_squeue_data():
    queuedata = StringIO.StringIO(os.popen("squeue -o %all", 'r').read())
    reader = csv.reader(queuedata, delimiter='|')
    headers = map(convert, reader.next())
    hl_idx = headers.index("NODELIST(REASON)")
    headers.append("FULL_NODELIST")
    rows = list()
    for row in reader:
        full_hostlist = map(str.strip, expand_hostlist(row[hl_idx]))
        row.append(str(',').join(full_hostlist))
        rows.append(map(convert, row))

    return {'headers' : headers, 'jobs': rows}

@route('/data/squeue')
def returnsqueue():
    return get_squeue_data()

def get_sinfo_data():
    queuedata = StringIO.StringIO(os.popen("sinfo -o %all", 'r').read())
    reader = csv.reader(queuedata, delimiter='|')
    nodelist = set()
    headers = map(convert, reader.next())
    hostnameIdx = headers.index("HOSTNAMES")
    rows = list()
    for row in reader:
        if not row[hostnameIdx] in nodelist:
            rows.append(map(convert, row))
            nodelist.add(row[hostnameIdx])
    return {'headers' : headers, 'nodes' : rows }

@route('/data/sinfo')
def returnsinfo():
    return get_sinfo_data()

@route('/data/nodeinfo')
def returnnodeinfo():
    s = StringIO.StringIO(os.popen("scontrol show -d --oneliner node", 'r').read())
    r = csv.reader(s, delimiter=" ")
    firstrow = r.next()
    del firstrow[-1]
    headers = [ convert(c.split('=', 1)[0]) for c in firstrow]
    nodeinfo = [[ convert(c.split('=', 1)[1]) for c in firstrow]]
    for row in r:
      nl = [ convert(c.split('=', 1)[1]) for c in row[:-2]]
      nodeinfo.append(nl)
    return dict(headers=headers, nodeinfo=nodeinfo)

@route('/data/job/<jobid:re:\d+_?\[?\d*\]?>')
def returnjobinfo(jobid):
    print jobid
    s = os.popen("scontrol show -d --oneliner job " + str(jobid)).read().split()
    if s:
      j = dict(x.split('=', 1) for x in s)
      cpu_mapping = list()
      h = ['Nodes', 'CPU_IDs', 'Mem']
      nodelist = ""
      for i, n in enumerate(s):
        if n.startswith("Nodes="):
          cpu_mapping.append([s[i].replace('Nodes=',''),
                             s[i+1].replace('CPU_IDs=',''),
                             s[i+2].replace('Mem=','')])
        if n.startswith("NodeList="):
          nodelist = n.replace("NodeList=", "")
      j['cpu_mapping'] = {'headers' : h, 'nodes' : cpu_mapping}
      j['expanded_nodelist'] = map(str.strip, expand_hostlist(nodelist))
    else:
      #not an active job, fetch finished job stats
      #remark, these stats have a different format, leave it up to the client side
      #to fix it.
      yesterday = (dt.datetime.today() - dt.timedelta(1)).strftime("%Y-%m-%d")
      sacct = "sacct -X --format=jobid,jobname,user,account,state,elapsed,submit,start,end,nnodes,ncpus,nodelist --parsable2 -S %s --job %s"
      s = os.popen(sacct % (yesterday, jobid), 'r').read()
      t = StringIO.StringIO(s)
      reader = csv.reader(t, delimiter='|')
      headers = map(convert, reader.next())
      jobinfo = map(convert, reader.next())
      j = dict(zip(headers, jobinfo))
      j['expanded_nodelist'] = map(str.strip, expand_hostlist(j["NodeList"]))
      print j
    return j

@route('/data/jobhist/<user>')
def returnjobhist(user):
    yesterday = (dt.datetime.today() - dt.timedelta(1)).strftime("%Y-%m-%d")
    sacct = "sacct -S %s -X --format=jobid,jobname,user,account,state,elapsed,start,end,nnodes,ncpus,nodelist --parsable2 -u %s" % (yesterday, quote(user))
    s = os.popen(sacct, 'r').read()
    t = StringIO.StringIO(s)
    reader = csv.reader(t, delimiter='|')
    headers = map(convert, reader.next())
    jobs = list()
    for row in reader:
        jobs.append(map(convert, row))
    return dict(headers=headers, jobs=jobs)

#
# Proxy requests for graphs to backend so we do not have to expose it
#
@route('/graph/')
def fetchgraph():
    # graphurlbase should rather be configurable than hardwired. 
    graphurlbase = 'http://stallo-adm.local/ganglia/graph.php?g=GRAPH_NAME&z=medium&c=Stallo&s=descending&hc=4&mc=2&h=HOSTNAME.local&r=custom&cs=STARTTIME&ce=ENDTIME'
    try:
      # quick fix for hostname renaming until steinar gets the c100 nodes installed with new slurm-acceptable hostname.
      # c[fb]100-[1-9] is already OK.
      fixedhosts = [ "cf100-%s"%i for i in range(1,10)] + [ "cb100-%s"%i for i in range(1,10)]
      hostname = request.query.hostname
      if not hostname in fixedhosts:
        if "100-" in hostname:
          # transform c[fb]100-X to c100-X[fb]
          fb = hostname[1]
          hostname = hostname.replace(fb, "") + fb
      graphurl = (graphurlbase.replace('GRAPH_NAME', request.query.name)
                              .replace('HOSTNAME',   hostname)
                              .replace('STARTTIME',  request.query.start)
                              .replace('ENDTIME',    request.query.end)
                  )
      
      graph = urlopen(graphurl)
      response.set_header('Content-type', 'image/png')
    except Exception as e:
      print e
      graph = None
    return graph

if __name__ == "__main__":
    run(host='localhost', port=8080, debug=True, reloader=True)
else:
    application = default_app()


