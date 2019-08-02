# SLURMBROWSER

A really thin web layer above SLURM

Current home is https://github.com/dragz/slurmbrowser/

## REQUIREMENTS

bottle.py and access to the slurm commands scontrol, squeue and sacct.

```
yum -y install python2-bottle
```

## USE

### Testing

For a quick test run
```
python slurmdata.py
```

and point your browser to:

  http://localhost:9080/html/squeue.html

It will listen on localhost:9080 in dev mode.

### Production

Put it under the wings of apache. See `apache_wsgi/` for example configs.

`mod_wsgi` is needed
```
yum -y install mod_wsgi
```

## GANGLIA

It is possible to fetch graphs from ganglia which gives a very nice interface
for the user to check the status of their jobs both live and in retrospect. See
`slurmbrowser.cfg` for hints on how to enable this (off by default as more work
is needed on describing this integration).


## TODO

Make jobs clickable so the row will expand with more info. Something
like this https://datatables.net/examples/api/row_details.html

Add load graphs like the old torque jobbrowser. (done)

More global info

## IMPLEMENTATION NOTES

### Server side

The basic principle is to make all slurm commands produce csv-parsable
output and let bottle convert it to json upon client requests. The
server is only handing out json data and static html files (albeit
with lots of included javascript). The server
does not do any data layout rendering, that is all left to the client.

#### API Guide

Not really an API

`/data/job/XXXX` Return the output of

```sh
scontrol show -d --onliner job XXXX
```

`/data/nodeinfo` Return the output of

```sh
scontrol show -d --oneline node
```

`/data/squeue` Return the output of

```sh
squeue -o %all
```

Remark: This also creates an extra entry, FULL_NODELIST, containing an
expanded nodelist. c[1-4] -> c1,c2,c3,c4. Don`t know how to do this in
javascript yet...

`/data/jobhist/USER` Return the output of

```sh
sacct -S YYYY-MM-DD -X --format=jobid,jobname,user,account,state,elapsed,start,end,nnodes,ncpus,nodelist --parsable2 -u USER
```

### Client side

The client side is based on async fetching of json data from the
server and all (or most) rendering of data is done by using the
DataTables library. The client is responsible to interpret and display
the data.
