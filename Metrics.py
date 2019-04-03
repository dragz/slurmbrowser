from lxml import etree

def processinfo(s):
    """processinfo(string): Splits string with ps-X metrics into dict."""
    items = ClassDict()
    for val in s.split(','):
        k, v = val.split('=', 1)
        k = k.strip(); v = v.strip()
        if k in ['%cpu', '%mem']:
            v = float(v)
        elif v.isdigit():
            v = int(v)
        items[k] = v
    
    return items

class ClassDict(dict):
    """ClassDict: A dict that allows keys to be attributes
    
    > a = ClassDict()
    > a['b'] = 1
    > print a.b
    1
    > a.c = 2
    > print a['c']
    2
    Undefined attributes will return None"""
    def __init__(self, v=None):
        if v:
            self.update(v)
    def __setattr__(self, key, val):
        self[key] = val
    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            return None

class Metrics(dict):
    def __init__(self, host=None, port=None, infile=None, filter=None, host_filter=None):
        fileobject = None
        if host and port:
            import socket
            s = socket.create_connection((host,port))
            fileobject = s.makefile()
        elif infile:
            fileobject = infile
        
        if fileobject:
            self.getmetrics(fileobject, filter, host_filter=host_filter)
            
    def getmetrics(self, fileobject, filter=None, host_filter=None):
        if not host_filter:
            host_filter = lambda s: s
        hostname = None
        
        events = ("start", )
        context = etree.iterparse(fileobject, events=events)
        for a, ele in context:
            #print(a,  ele.attrib, ele.tag)
            tag = ele.tag
            if tag == 'HOST':
                hostname = host_filter(ele.attrib['NAME'])
                if hostname:
                    self[hostname] = ClassDict()
            elif hostname and tag == 'METRIC' and\
                (not filter or list(filter(ele.attrib['NAME']))):
                aname = ele.attrib['NAME']
                if ele.attrib['TYPE'] == "string" and aname.startswith('ps-'):
                    items = processinfo(ele.attrib['VAL'])
                elif ele.attrib['TYPE'].startswith("float") or \
                        ele.attrib['TYPE'].startswith("double"):
                    items = float(ele.attrib['VAL'])
                elif ele.attrib['TYPE'].startswith("int") or \
                        ele.attrib['TYPE'].startswith("uint"):
                    items = int(ele.attrib['VAL'])                    
                else:
                    items = ele.attrib['VAL']
                self[hostname][aname] = ClassDict({'val' : items, 
                                            'tn' : int(ele.attrib['TN']), 
                                            'units' : ele.attrib['UNITS'], 
                                            'tmax' : int(ele.attrib['TMAX']), 
                                            'dmax' : int(ele.attrib['DMAX']), 
                                            'slope' : int(ele.attrib['DMAX'])})
def filter_procs(s):
    return s.startswith('ps-')

def filter_no_procs(s):
    return not s.startswith('ps-')

def filter_memory(s):
    return s.startswith("mem")

def filter_cpu(s):
    return s.startswith("cpu")

class Filter:
    def __init__(self, s=None, hl=None):
        self.s = s
        self.hl = hl
    def startswith(self, s):
        return s.startswith(self.s)
    def contains(self, s):
        return self.s in s
    def checklist(self, h):
        for s in self.s:
            if h.startswith(s):
                return h
        return None
    def hostsubstr(self, h):
        if h.startswith(self.s):
            return h
    def hostlist(self, h):
        h = h.replace(".local", "")
        if h in self.hl:
            return h
        return None

def main():
    host = "stallo-adm.local"
    port = 8649
    m = Metrics(host=host, port=port, filter=Filter("cpu_system").startswith)

    import pprint
    pprint.pprint(m)

    def is_ok(d):
        if d:
            return 1
        else:
            return 0
    ok = sum(map(is_ok, list(m.values())))
    notok = len(list(m.values()))-ok
    print("reported %s hosts, missing %s hosts\n"%(ok, notok))
    for h, met in list(m.items()):
        if not met:
            print(h)
    
if __name__ == "__main__":
    main()
