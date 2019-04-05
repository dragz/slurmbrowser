import os
import sys
import csv
import io
import time
import datetime as dt
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from urllib.request import urlopen
from pipes import quote
from configparser import SafeConfigParser

# quick fix for locating install dir when running under apache
if not __name__ == "__main__":
    sys.path.append(os.path.dirname(__file__))
    os.chdir(os.path.dirname(__file__))
from bottle import route, run, static_file, request, response, default_app
from hostlist import expand_hostlist

GANGLIA = 1
GANGLIA_PROC = 1
config = SafeConfigParser()
config.read('slurmbrowser.cfg')
GANGLIA = int(config.get('MAIN', 'ganglia'))
GANGLIA_PROC = int(config.get('MAIN', 'ganglia_proc'))

if GANGLIA:
    serverurl = config.get('Ganglia', 'serverurl')
    graphurl = config.get('Ganglia', 'graphurl')
    user = config.get('Ganglia', 'user')
    passwd = config.get('Ganglia', 'passwd')

    if user:
        auth_handler = urllib.request.HTTPBasicAuthHandler()
        auth_handler.add_password(realm = "Ganglia web UI", uri = serverurl,
                                  user = user, passwd = passwd)
        opener = urllib.request.build_opener(auth_handler)
        urllib.request.install_opener(opener)

    try:
        from Metrics import Metrics, Filter
    except ImportError:
        print("No ganglia interface, disabling ganglia graph and proc support.")
        GANGLIA = 0
        GANGLIA_PROC = 0


#
# This section of code is only used when producing screencasts
# all it does is hide the real usernames 
#
OBFUSCATED_USERNAMES=0

def obfuscated_usernames():
    usernames = os.popen("squeue -h -o %u","r").readlines()
    uu = set(map(str.strip, usernames))
    a = ord('a')
    z = ord('z')
    ou = [ chr(s)+chr(t)+"user" for s in range(ord('a'), ord('z')+1) for t in range(ord('a'), ord('z')+1)]
    usermap = list(zip(uu, ou))
    return usermap

def hide_usernames(t):
    """hide usernames when producing images or videos"""
    global OBFUSCATED_USERNAMES
    if OBFUSCATED_USERNAMES:
        um = obfuscated_usernames()
        for u, o in um:
            t = t.replace(u,o)
    return t

def reverse_hidden_user(user):
    """reverse lookup hidden usernames when producing images or videos"""
    global OBFUSCATED_USERNAMES
    if OBFUSCATED_USERNAMES:
        usermap = obfuscated_usernames()
        for u, o in usermap:
            if o == user:
                return u
    return user
#
#
#

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
    t0 = time.time()
    squeue = os.popen("squeue -o %all", 'r').read()
    squeue = hide_usernames(squeue)
    queuedata = io.StringIO(squeue)
    print("fetching quedata took ", time.time() - t0)
    reader = csv.reader(queuedata, delimiter='|')
    headers = list(map(convert, next(reader)))
    hl_idx = headers.index("NODELIST(REASON)")
    rows = list()
    for row in reader:
        rows.append(list(map(convert, row)))
    print("total squeue", time.time() - t0)

    return {'headers' : headers, 'jobs': rows}

@route('/data/squeue')
def returnsqueue():
    return get_squeue_data()

def get_sinfo_data():
    t0 = time.time()
    queuedata = io.StringIO(os.popen("sinfo -o %all", 'r').read())
    reader = csv.reader(queuedata, delimiter='|')
    nodelist = set()
    headers = list(map(convert, next(reader)))
    hostnameIdx = headers.index("HOSTNAMES")
    rows = list()
    for row in reader:
        if not row[hostnameIdx] in nodelist:
            rows.append(list(map(convert, row)))
            nodelist.add(row[hostnameIdx])
    print("sinfo", time.time() - t0)
    return {'headers' : headers, 'nodes' : rows }

@route('/data/sinfo')
def returnsinfo():
    return get_sinfo_data()

@route('/data/nodeinfo')
def returnnodeinfo():
    t0 = time.time()
    s = os.popen("scontrol show -d --oneliner node", 'r').readlines()
    nodeinfo = list()
    for l in s:
      nodedata = dict()
      for e in l.strip().split(None,1):
        k, v = e.split('=', 1)
        #down nodes need special treatment. The Reason= is the last field
        if k.startswith('Reason'):
          v = l[l.find('Reason=') + len('Reason='):].strip()
          nodedata.update({k : convert(v)})
          break
        nodedata.update({k : convert(v)})
      nodeinfo.append(nodedata)
    print("nodeinfo ", time.time() - t0)
    return {'nodeinfo' : nodeinfo}


def get_procs(nodelist):
    import socket
    host = "jump.cluster"
    port = 8652
    print(nodelist)
    #nodelist = map(lambda x: x+'.local', nodelist)
    psinfo = Metrics()
    for node in nodelist:
        host_filter = Filter(hl=[node]).hostlist
        s = socket.create_connection((host,port))
        s.sendall(("/frontends/%s/\n" % node).encode('utf-8'))         # beware, if the nodename isn't recognized gmetad will dump the whole database on you.
        fileobject = s.makefile('b',encoding='utf-8')
        node_psinfo = Metrics(infile=fileobject, filter=Filter("ps-").startswith,
                        host_filter=host_filter) 
        print(node_psinfo)
        psinfo.update(node_psinfo)
    return list(psinfo.items())



@route('/data/job/<jobid:re:\d+_?\[?\d*\]?>')
def returnjobinfo(jobid):
    global GANGLIA, GANGLIA_PROC
    t0 = time.time()
    #print jobid
    s = hide_usernames(os.popen("scontrol show -d --oneliner job " + str(jobid)).read()).split()
    print("slurm response took ", time.time() - t0)
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
      j['expanded_nodelist'] = list(map(str.strip, expand_hostlist(nodelist)))
      if GANGLIA == 1 and GANGLIA_PROC == 1:
          print(j['expanded_nodelist'])
          t_procs0 = time.time()
          j['procs'] = get_procs(j['expanded_nodelist'])
          print("get procs took", time.time() - t_procs0)
    else:
      #not an active job, fetch finished job stats
      #remark, these stats have a different format, leave it up to the client side
      #to fix it.
      yesterday = (dt.datetime.today() - dt.timedelta(1)).strftime("%Y-%m-%d")
      sacct = "sacct -X --format=jobid,jobname,user,account,state,elapsed,submit,start,end,nnodes,ncpus,reqnodes,reqcpus,nodelist --parsable2 -S %s --job %s"
      s = hide_usernames(os.popen(sacct % (yesterday, jobid), 'r').read())
      t = io.StringIO(s)
      reader = csv.reader(t, delimiter='|')
      headers = list(map(convert, next(reader)))
      jobinfo = list(map(convert, next(reader)))
      j = dict(list(zip(headers, jobinfo)))
      j['expanded_nodelist'] = list(map(str.strip, expand_hostlist(j["NodeList"])))
    j['GANGLIA'] = GANGLIA
    #print j
    print("jobinfo", time.time() - t0)
    return j

@route('/data/jobhist/<user>')
def returnjobhist(user):
    user = reverse_hidden_user(user)
    t0 = time.time()
    yesterday = (dt.datetime.today() - dt.timedelta(1)).strftime("%Y-%m-%d")
    sacct = "sacct -S %s -X --format=jobid,jobname,user,account,state,elapsed,start,end,nnodes,ncpus,nodelist --parsable2 -u %s" % (yesterday, quote(user))
    s = hide_usernames(os.popen(sacct, 'r').read())
    t = io.StringIO(s)
    reader = csv.reader(t, delimiter='|')
    headers = list(map(convert, next(reader)))
    jobs = list()
    for row in reader:
        jobs.append(list(map(convert, row)))
    print("jobhist", time.time() - t0)
    return dict(headers=headers, jobs=jobs)

#
# Proxy requests for graphs to backend so we do not have to expose it
#
@route('/graph/')
def fetchgraph():
    global graphurl
    try:
        hostgraphurl = (graphurl.replace('GRAPH_NAME', request.query.name)
                           .replace('STARTTIME',  request.query.start)
                           .replace('ENDTIME',    request.query.end)
                  )
        if request.query.hostname:
            hostgraphurl = hostgraphurl.replace('HOSTNAME', request.query.hostname)
        if request.query.hl:
            hostgraphurl += "&glegend=hide&gtype=line&z=large&line_width=0"
            hostgraphurl += "&aggregate=1&hreg[]=" + urllib.parse.quote("|".join([ h + "\\b" for h in request.query.hl.split(',')]))
            hostgraphurl += "&mreg[]=^" + request.query.mreg
            hostgraphurl += "&title=" + request.query.mreg
        print(hostgraphurl)
        graph = urlopen(hostgraphurl)
        response.set_header('Content-type', 'image/png')
    except Exception as e:
        print(e)
        graph = None
    return graph

if __name__ == "__main__":
    run(host='localhost', port=9080, debug=True, reloader=True)
else:
    application = default_app()


