##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """RouteMap

RouteMap gathers and stores routing information.

"""

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap

class RouteMap(SnmpPlugin):

    maptype = "RouteMap"
    relname = "routes"
    compname = "os"
    modname = "Products.ZenModel.IpRouteEntry"
    deviceProperties = \
                SnmpPlugin.deviceProperties + ('zRouteMapCollectOnlyLocal',
                                               'zRouteMapCollectOnlyIndirect',
                                               'zRouteMapMaxRoutes')
    columns = {
        '.1' : 'id',
        '.2': 'setInterfaceIndex',
        #'.3': 'metric1',
        #'.4': 'metric2',
        #'.5': 'metric3',
        #'.6': 'metric4',
        '.7': 'setNextHopIp',
        '.8': 'routetype',
        '.9': 'routeproto',
        #'.10' : 'routeage',
        '.11': 'routemask',
        #'.12': 'metric5',
    }

    columnsAlt = {
        '.1' : 'id',
        '.5': 'setInterfaceIndex',
        #'.11': 'metric1',
        '.4': 'setNextHopIp',
        '.6': 'routetype',
        '.7': 'routeproto',
        #'.8' : 'routeage',
        '.2': 'routemask',
    }
    
    snmpGetTableMaps = (
        GetTableMap('routetable', '.1.3.6.1.2.1.4.21.1', columns),
        GetTableMap('routetableAlt', '.1.3.6.1.2.1.4.24.4.1', columnsAlt),
    )



    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        routetable = tabledata.get("routetable")
        routetableAlt = tabledata.get("routetableAlt")
        localOnly = getattr(device, 'zRouteMapCollectOnlyLocal', False)
        indirectOnly = getattr(device, 'zRouteMapCollectOnlyIndirect', False)
        maxRoutes = getattr(device, 'zRouteMapMaxRoutes', 500)
        rm = self.relMap()
        routes = routetable.values()
        try:
            for value in routetableAlt.values():
                value['routemask'] = self.reverseNetmask(value['routemask'])
                if value not in routes:  routes.append(value)
        except:  pass
        for route in routes:
            log.debug(route)
            om = self.objectMap(route)
            if not hasattr(om, "id"): continue
            if not hasattr(om, "routemask"): continue
            om.routemask = self.maskToBits(om.routemask)
            # Workaround for existing but invalid netmasks
            if om.routemask is None: continue
            log.debug("NETMASK:%s %s" % (om.id,om.routemask))
            om.setTarget = om.id + "/" + str(om.routemask)
            om.id = om.id + "_" + str(om.routemask)
            if om.routemask == 32: continue
            routeproto = getattr(om, 'routeproto', 'other')
            om.routeproto = self.mapSnmpVal(routeproto, self.routeProtoMap)
            if localOnly and om.routeproto != 'local':
                continue
            if not hasattr(om, 'routetype'):
                continue
            om.routetype = self.mapSnmpVal(om.routetype, self.routeTypeMap)
            if indirectOnly and om.routetype != 'indirect':
                continue
            if len(rm.maps) > maxRoutes:
                log.error("Maximum number of routes (%d) exceeded", maxRoutes)
                return
            rm.append(om)
            log.debug(om)
        return rm
    
    def reverseNetmask(self, mask):
        ''''''
        dots = mask.split('.')
        dots.sort(reverse=True)
        return '.'.join(dots)
    
    def mapSnmpVal(self, value, map):
        if len(map)+1 >= value:
            value = map[value-1]
        return value
    
    routeTypeMap = ('other', 'invalid', 'direct', 'indirect')
    routeProtoMap = ('other', 'local', 'netmgmt', 'icmp',
            'egp', 'ggp', 'hello', 'rip', 'is-is', 'es-is',
            'ciscoIgrp', 'bbnSpfIgrp', 'ospf', 'bgp')

