from Products.DataCollector.plugins.CollectorPlugin import CollectorPlugin
from Products.ZenUtils.Utils import zenPath
#from twisted.internet.utils import getProcessOutput
from Products.ZenUtils.ZenTales import talesCompile, getEngine
import re,os,time
from subprocess import *


NMAPDEFAULTS = "-p 1-10000 -sS -oG -"
class NmapIpServiceMap(CollectorPlugin):

    transport = "python"
    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = CollectorPlugin.deviceProperties + ('zNmapPortscanOptions','manageIp')

    def getExecOutput(self,args,log):
        ''''''
        timeout = 10 # timeout value
        timed_out = False
        output = Popen(args,stderr=STDOUT,stdout=PIPE)
        lines = []
        while (output.poll() is None and timeout > 0):
            time.sleep(1)
            timeout -= 1
        if not timeout > 0:
            try: output.terminate()
            except: pass
            timed_out = True
        else:
            timed_out = False
            lines = output.communicate()[0].split("\n")
        return lines

    def collect(self,device,log):
        ''''''
        args = [zenPath('libexec', 'nmap')]
        try: args += device.zNmapPortscanOptions.split(' ')
        except: args += NMAPDEFAULTS.split(' ')
        args.append(device.manageIp)
        return self.getExecOutput(args,log)
    
    def process(self, device, results, log):
        ''''''
        rm = self.relMap()
        log.info("The plugin %s returned %s results." % (self.name(), len(results)))
        for line in results:
            if 'Ports:' in line:
                goodpart = line.split('Ports: ')[1]
                ports = goodpart.split(',')
                for port in ports:
                    portnum = int(port.split('/')[0])
                    state = port.split('/')[1]
                    proto = port.split('/')[2]
                    om = self.objectMap()
                    om.id = 'tcp_%05d' % portnum
                    om.ipaddresses = [device.manageIp,]
                    om.protocol = proto
                    om.port = portnum
                    om.setServiceClass = {'protocol': 'tcp', 'port':portnum}
                    om.setIpinterface = ''
                    om.discoveryAgent = self.name()
                    rm.append(om)
        if len(rm.maps) == 0:
            log.warn("No services found, or nmap output wasn't processed properly.")
        return rm
