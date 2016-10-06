import os
import csv
import StringIO
from bottle import route, run, static_file

@route('/<filename>')
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
    return [map(convert, row) for row in reader]

@route('/data/squeue')
def returnsqueue():
    return {'jobs' : get_squeue_data()}

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


run(host='localhost', port=8080, debug=True, reloader=True)
