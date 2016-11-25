# SLURMBROWSER

A really thin web layer above SLURM

# REQUIREMENTS


bottle.py and access to the slurm commands scontrol, squeue and sacct.


# USE

python slurmdata.py

and point your browser to:

  http://localhost:8080/html/squeue.html. 

It will listen on localhost:8080 in dev mode. Or, put it under the wings of apache. See slurmbrowser.conf for an example config. It needs mod_wsgi.





# TODO


Make jobs clickable so the row will expand with more info. Something
like this https://datatables.net/examples/api/row_details.html

Add load graphs like the old torque jobbrowser. (done)

More global info

# IMPLEMENTATION NOTES

## Server side

The basic principle is to make all slurm commands produce csv-parsable
output and let bottle convert it to json upon client requests. The
server is only handing out json data and static html files (albeit
with lots of included javascript). The server
does not do any data layout rendering, that is all left to the client.

### API Guide

Not really an API

`/data/job/XXXX` Return the output of 
```
scontrol show -d --onliner job XXXX
```

`/data/nodeinfo` Return the output of 
```
scontrol show -d --oneline node
```

`/data/squeue` Return the output of 
```
squeue -o %all
```
Remark: This also creates an extra entry, FULL_NODELIST, containing an
expanded nodelist. c[1-4] -> c1,c2,c3,c4. Don`t know how to do this in
javascript yet...

`/data/jobhist/USER` Return the output of 
```
sacct -S YYYY-MM-DD -X --format=jobid,jobname,user,account,state,elapsed,start,end,nnodes,ncpus,nodelist --parsable2 -u USER
```





## Client side

The client side is based on async fetching of json data from the
server and all (or most) rendering of data is done by using the
DataTables library. The client is responsible to interpret and display
the data.
