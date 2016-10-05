import os
import csv
import json
import StringIO
from bottle import route, run, static_file

@route('/<filename>')
def server_static(filename):
    return static_file(filename, root='/home/royd/projects/slurmbrowser')



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
    return {'squeue' : get_squeue_data()}


run(host='localhost', port=8080, debug=True, reloader=True)
