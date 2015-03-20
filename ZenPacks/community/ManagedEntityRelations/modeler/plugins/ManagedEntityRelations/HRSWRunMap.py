import re
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin
from Products.DataCollector.plugins.CollectorPlugin import GetTableMap
from Products.ZenModel.OSProcessMatcher import buildObjectMapData
from Products.DataCollector.plugins.DataMaps import ObjectMap, MultiArgs


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
    
    procMaps = {}
    
    def _extractProcessText(self, proc, log):
        '''return string for zenoss process name'''
        path = proc.get('_procPath','').strip()
        if path and path.find('\\') == -1: name = path
        else: name = proc.get('_procName','').strip()
        if name: return (name + ' ' + proc.get('_parameters','').strip()).rstrip()
        else: log.warn("Skipping process with no name")
        return None
    
    def portToPidMap(self, porttable, pidtable, log):
        '''return map of PIDs to ports'''
        # process TCP/UDP Port data
        output = {}
        log.debug("===TCP Port information received ===")
        pidmap = {}
        try:
            for p in sorted(porttable.keys()):
                val = porttable[p]
                pid = int(val['_localPID'])
                if pid not in pidmap.keys():  pidmap[pid] = []
                port = p.split('.')[-1]
                pidmap[pid].append(port)
        except:  pass
        log.debug("=== Process information received ===")
        # associate the PID with open ports
        for p in sorted(pidtable.keys()):
            val = pidtable[p]
            if '_procPID' in val.keys():
                pid = int(val['_procPID'])
                if 'port' not in val.keys(): val['port'] = []
                if pid in pidmap.keys(): val['port'] = pidmap[pid]
            # this is for attempting to match process to a filesystem path
            if '_procPath' in val.keys(): val['mount'] = self.parsePath(val['_procPath'])
        return pidtable
    
    def parsePath(self, path):
        '''try to get the path to the filesystem'''
        output = '/'
        if path.startswith('/'):
            output = ('/').join(path.split('/')[:-1])
        return output
    
    def parseResults(self, device, porttable, pidtable, log):
        ''''''
        # update the dictionary
        pidtable = self.portToPidMap(porttable, pidtable, log)
        matchData = device.osProcessClassMatchData
        output = {}
        for x in pidtable.values():
            log.debug("X: %s" % x)
            cmd = self._extractProcessText(x, log)
            if cmd is None: continue
            data = buildObjectMapData(matchData, [cmd])
            # skip if there are no results
            if len(data) < 1: continue
            for d in data:
                id = d['id']
                if id not in output.keys():  output[id] = d
                if 'port' not in d.keys():  d['port'] = []
                d['port'] += x['port']
        return output
    
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
            log.error("Unable to get data for %s from hrSWRunEntry %s -- skipping model", HRSWRUNENTRY, device.id)
            return None
        if not pidtable.values():
            log.warning("No process information from hrSWRunEntry %s", HRSWRUNENTRY)
            return None
        
        rm = self.relMap()
        objects = self.parseResults(device, porttable, pidtable, log)
        for o in objects.values():
            om = self.objectMap(o)
            om.setIpservice = ''
            try:
                prodKey = o['setOSProcessClass'].split('/')[-1].lower().capitalize()
                om.setProductKey = MultiArgs(prodKey)
            except: pass
            log.debug(om)
            rm.append(om)
        return rm


