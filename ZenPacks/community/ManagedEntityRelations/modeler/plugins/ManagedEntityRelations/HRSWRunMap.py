import re
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin
from Products.DataCollector.plugins.CollectorPlugin import GetTableMap
from Products.ZenModel.OSProcessMatcher import buildObjectMapData

__doc__ = """HRSWRunMap

HRSWRunMap models a relation between modeled processes and associated ipservcies

"""

HRSWRUNENTRY = '.1.3.6.1.2.1.25.4.2.1'
TCPLISTENERENTRY = '.1.3.6.1.2.1.6.20.1'

class HRSWRunMap(SnmpPlugin):
    ''''''
    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    deviceProperties = SnmpPlugin.deviceProperties + ('osProcessClassMatchData',)
    
    columns = {
               '.1': '_procPID',
               '.2': '_procName',
               '.4': '_procPath',
               '.5': '_parameters',
               }
    
    TCPcolumns = {
         '.1': '_localAddrType',
         '.2': '_localAddr',
         '.3': '_localPort',
         '.4': '_localPID',
         }
    
    snmpGetTableMaps = ( 
                        GetTableMap('hrSWRunEntry', HRSWRUNENTRY, columns),
                        GetTableMap('tcpListenerEntry', TCPLISTENERENTRY, TCPcolumns),
                     )
    
    def _extractProcessText(self, proc, log):
        ''''''
        path = proc.get('_procPath','').strip()
        if path and path.find('\\') == -1: name = path
        else: name = proc.get('_procName','').strip()
        if name: return (name + ' ' + proc.get('_parameters','').strip()).rstrip()
        else: log.warn("Skipping process with no name")
        return None
    
    def process(self, device, results, log):
        """
        Process the SNMP information returned from a device
        """
        log.info("The plugin %s returned %s results." % (self.name(), len(results)))
        getdata, tabledata = results
        # get the SNMP TCP Listener data
        porttable = tabledata.get("tcpListenerEntry")
        # get the SNMP process data
        pidtable = tabledata.get("hrSWRunEntry")
        if pidtable is None:
            log.error("Unable to get data for %s from hrSWRunEntry %s"
                          " -- skipping model", HRSWRUNENTRY, device.id)
            return None
        if not pidtable.values():
            log.warning("No process information from hrSWRunEntry %s", HRSWRUNENTRY)
            return None
        
        # process TCP/UDP Port data
        log.debug("===TCP Port information received ===")
        pidmap = {}
        try:
            for p in sorted(porttable.keys()):
                log.debug("snmpidx: %s\tport: %s" % (p, porttable[p]))
                port = p.split('.')[-1]
                pid = int(porttable[p]['_localPID'])
                if pid not in pidmap.keys():  pidmap[pid] = []
                pidmap[pid].append(port)
            log.debug("pidmap: %s" % pidmap)
        except:  pass
        log.debug("=== Process information received ===")
        # associate the PID with open ports
        for p in sorted(pidtable.keys()):
            # get the pid
            try: 
                ppid = int(pidtable[p]['_procPID'])
                log.debug("processing PID: %s" % ppid)
            except: pass
            try: pidtable[p]['port'] = pidmap[ppid]
            except: pidtable[p]['port'] = []
            # path name
            # this is for attempting to match process to filesystem
            try: pidtable[p]['mount'] = pidtable[p]['_procPath'].replace(pidtable[p]['_procName'],'')
            except: pidtable[p]['mount'] = ''
            log.debug("snmpidx: %s\tprocess: %s" % (p, pidtable[p]))
        
        rm = self.relMap()
        matchData = device.osProcessClassMatchData
        
        #objects = []
        objects = {}
        for x in pidtable.values():
            cmd = self._extractProcessText(x, log)
            if cmd is None: continue
            data = buildObjectMapData(matchData, [cmd])
            if len(data) <= 0: continue
            for d in data:
                if 'port' not in d.keys():  d['port'] = []
                if d['id'] not in objects.keys():  objects[d['id']] = d
                d['port'] += x['port']
                #if d not in objects:  objects.append(d)
        for o in objects.values():
            om = self.objectMap(o)
            om.setIpservice = ''
            log.debug(om)
            rm.append(om)
        return rm

