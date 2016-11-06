import os
import sys
import csv
import StringIO

# quick fix for locating install dir when running under apache
if not __name__ == "__main__":
  sys.path.append(os.path.dirname(__file__))
  os.chdir(os.path.dirname(__file__))
from bottle import route, run, static_file
import bottle
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
def returnsqueue():
    return get_sinfo_data()

@route('/data/job/<jobid:int>')
def returnjobinfo(jobid):
    s = os.popen("scontrol show -d --oneliner job " + str(jobid)).read().split()
    j = dict(x.split('=', 1) for x in s)
    cpu_mapping = list()
    h = ['Nodes', 'CPU_IDs', 'Mem']
    for i, n in enumerate(s):
        if n.startswith("Nodes="):
          cpu_mapping.append([s[i].replace('Nodes=',''),
                             s[i+1].replace('CPU_IDs=',''),
                             s[i+2].replace('Mem=','')])
    print cpu_mapping
    j['cpu_mapping'] = {'headers' : h, 'nodes' : cpu_mapping}
    return j

if __name__ == "__main__":
    run(host='localhost', port=8080, debug=True, reloader=True)
else:
    application = bottle.default_app()


