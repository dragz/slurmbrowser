import os
import sys
import csv
import StringIO
import datetime as dt
import urllib2
from urllib2 import urlopen
from pipes import quote
from ConfigParser import SafeConfigParser

# quick fix for locating install dir when running under apache
if not __name__ == "__main__":
    sys.path.append(os.path.dirname(__file__))
    os.chdir(os.path.dirname(__file__))
from bottle import route, run, static_file, request, response, default_app
from hostlist import expand_hostlist
from Metrics import Metrics, Filter


config = SafeConfigParser()
config.read('slurmbrowser.cfg')
serverurl = config.get('Ganglia', 'serverurl')
graphurl = config.get('Ganglia', 'graphurl')
user = config.get('Ganglia', 'user')
passwd = config.get('Ganglia', 'passwd')


# graphurlbase should rather be configurable than hardwired. 
# for stallo
#graphurlbase = 'http://stallo-adm.local/ganglia/graph.php?g=GRAPH_NAME&z=medium&c=Stallo&s=descending&hc=4&mc=2&h=HOSTNAME.local&r=custom&cs=STARTTIME&ce=ENDTIME'
# for fram
#graphurlbase = 'http://jump.cluster/ganglia/graph.php?g=GRAPH_NAME&z=medium&c=frontends&s=descending&hc=4&mc=2&h=HOSTNAME&r=custom&cs=STARTTIME&ce=ENDTIME'
# quick fix for auth on ganglia.
if user:
    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm = "Ganglia web UI", uri = serverurl,
                              user = user, passwd = passwd)
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)



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
    s = os.popen("scontrol show -d --oneliner node", 'r').readlines()
    nodeinfo = list()
    for l in s:
      nodedata = dict()
      for e in l.strip().split():
        k, v = e.split('=', 1)
        #down nodes need special treatment. The Reason= is the last field
        if k.startswith('Reason'):
          v = l[l.find('Reason=') + len('Reason='):].strip()
          nodedata.update({k : convert(v)})
          break
        nodedata.update({k : convert(v)})
      nodeinfo.append(nodedata)
    return {'nodeinfo' : nodeinfo}


def get_procs(nodelist):
    host = "stallo-adm.local"
    port = 8649

    #nodelist = map(lambda x: x+'.local', nodelist)
    psinfo = Metrics(host=host, port=port, filter=Filter("ps-").startswith,
                host_filter=Filter(hl=nodelist).hostlist)
    return psinfo.items()



@route('/data/job/<jobid:re:\d+_?\[?\d*\]?>')
def returnjobinfo(jobid):
    #print jobid
    s = os.popen("scontrol show -d --oneliner job " + str(jobid)).read().split()
    if s:
      j = dict()
      for x in s:
        y = x.split('=', 1)
        if len(y) == 2:
          j[y[0]] = y[1]
        
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
      j['procs'] = get_procs(j['expanded_nodelist'])
    else:
      #not an active job, fetch finished job stats
      #remark, these stats have a different format, leave it up to the client side
      #to fix it.
      yesterday = (dt.datetime.today() - dt.timedelta(1)).strftime("%Y-%m-%d")
      sacct = "sacct -X --format=jobid,jobname,user,account,state,elapsed,submit,start,end,nnodes,ncpus,reqnodes,reqcpus,nodelist --parsable2 -S %s --job %s"
      s = os.popen(sacct % (yesterday, jobid), 'r').read()
      t = StringIO.StringIO(s)
      reader = csv.reader(t, delimiter='|')
      headers = map(convert, reader.next())
      jobinfo = map(convert, reader.next())
      j = dict(zip(headers, jobinfo))
      j['expanded_nodelist'] = map(str.strip, expand_hostlist(j["NodeList"]))
      #print j
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
    global graphurl
    try:
      hostgraphurl = (graphurl.replace('GRAPH_NAME', request.query.name)
                           .replace('HOSTNAME',   request.query.hostname)
                           .replace('STARTTIME',  request.query.start)
                           .replace('ENDTIME',    request.query.end)
                  )
      #print hostgraphurl
      graph = urlopen(hostgraphurl)
      response.set_header('Content-type', 'image/png')
    except Exception as e:
      print e
      graph = None
    return graph

if __name__ == "__main__":
    run(host='localhost', port=8081, debug=True, reloader=True)
else:
    application = default_app()


