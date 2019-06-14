all:
	@echo "make bootstrap to copy all files needed from the net"

bootstrap:
	wget https://pypi.python.org/packages/bd/99/04dc59ced52a8261ee0f965a8968717a255ea84a36013e527944dbf3468c/bottle-0.12.13.tar.gz
	tar zxf bottle-0.12.13.tar.gz bottle-0.12.13/bottle.py
	mv bottle-0.12.13/bottle.py .
	rmdir bottle-0.12.13/
	rm -f bottle-0.12.13.tar.gz

	wget https://craig.global.ssl.fastly.net/js/mousetrap/mousetrap.min.js

install:
	yum -y install httpd mod_wsgi mod_ssl python2-bottle python-lxml
	cp slurmdata.py Metrics.py squeue.html nodeinfo.html job.html jobhist.html hostlist.py /var/www/slurmbrowser/

clean:
	rm -f *~ *.tar.gz* *.pyc

distclean: clean
	rm -f bottle.py mousetrap.min.js

