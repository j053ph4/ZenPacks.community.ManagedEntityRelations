import Globals
from Products.ZenModel.ZenPack import ZenPack as ZenPackBase
from Products.ZenUtils.Utils import *
from ZenPacks.community.ConstructionKit.ZenPackHelper import *
from ZenPacks.community.ConstructionKit.CustomComponent import CustomComponent
from Products.ZenModel.DeviceComponent import DeviceComponent

unused(Globals)

# zenpack to 
from RelationHelper import *
from FunctionHelper import *

# add relations between components and each other components and organizers, and between organizers and each other
mgr = RelationHelper()

''' 
    add productClass relation to all components, service classes, and process classes
'''
#mgr.add( 'productClass', ToOne, "Products.ZenModel.ProductClass", None, 'serviceClasses', ToMany, "Products.ZenModel.ServiceClass" , None)
#mgr.add( 'productClass', ToOne, "Products.ZenModel.ProductClass", None, 'processClasses', ToMany, "Products.ZenModel.OSProcessClass" , None)
mgr.add( 'productClass', ToOne, "Products.ZenModel.ProductClass", None, 'instances', ToMany, "Products.ZenModel.OSComponent" , None)

''' 
    between process and ipservice 
'''
mgr.add( 'osprocess', ToMany, 'Products.ZenModel.OSProcess', 'port', 'ipservice', ToMany, 'Products.ZenModel.IpService' , 'port')

''' 
    between ipservice and ipinterface 
'''
mgr.add( 'ipservice', ToMany, 'Products.ZenModel.IpService', 'iface', 'ipinterface', ToMany, 'Products.ZenModel.IpInterface' , 'ipaddresses')

''' 
    between osprocess and filesystem 
'''
mgr.add( 'osprocess', ToMany, 'Products.ZenModel.OSProcess', 'mount', 'filesystem', ToMany, 'Products.ZenModel.FileSystem' , 'mount')

'''
    between DBSrvrInst (if it exists) and ipservice
'''

#from ZenPacks.community.RDBMS.DBSrvInst import DBSrvInst
mgr.add( 'ipservice', ToMany, 'Products.ZenModel.IpService', 'port', 'softwaredbsrvinstances', ToMany, 'ZenPacks.community.RDBMS.DBSrvInst' , 'port')

'''
    set a basic "parent" metatype for each class.  This should be one that the class would be dependent on
'''

# # os
# mgr.add( 'parentObject', ToOne, 'Products.ZenModel.Device', None, 'childObjects', ToMany, 'Products.ZenModel.OperatingSystem' , None)
# # hw
# mgr.add( 'parentObject', ToOne, 'Products.ZenModel.Device', None, 'childObjects', ToMany, 'Products.ZenModel.DeviceHW' , None)
# 
# mgr.add( 'parentObject', ToOne, 'Products.ZenModel.OperatingSystem', None, 'childObjects', ToMany, 'Products.ZenModel.OSComponent' , None)
# mgr.add( 'parentObject', ToOne, 'Products.ZenModel.DeviceHW', None, 'childObjects', ToMany, 'Products.ZenModel.HWComponent' , None)
# 
# mgr.add( 'parentObject', ToOne, 'Products.ZenModel.OSProcess', None, 'childObjects', ToMany, 'Products.ZenModel.IpService' , None)
# 
# mgr.add( 'parentObject', ToOne, 'Products.ZenModel.HWComponent', None, 'childObjects', ToMany, 'Products.ZenModel.OperatingSystem' , None)



'''
    install all of the relations
'''
mgr.install()


OSComponent.parent_meta = 'OperatingSystem'


from ZenPacks.community.RDBMS.DBSrvInst import DBSrvInst
#def setIpService(ob, name=''): ob.setCustomRelation(ob.findDeviceComponent(ob.device(), 'IpService', 'port', ob.port), 'ipservice', 'softwaredbsrvinstances')
#DBSrvInst.setIpService = setIpService

def setProductKey2(ob, prodKey, manufacturer=None):
    '''Set the product class of this software by its productKey.
    '''
    if prodKey:
        # Store these so we can return the proper value from getProductKey
        ob._prodKey = prodKey
        ob._manufacturer = manufacturer
        if manufacturer is None: manufacturer = 'Unknown'
        manufs = ob.getDmdRoot("Manufacturers")
        prodobj = manufs.createSoftwareProduct(prodKey, manufacturer)
        ob.productClass.addRelation(prodobj)
        # set product class for associated components
        for a in ob.getAssociates():
            if a.meta_type in ['OSProcess','IpService','WinService']:  
                a.productClass.addRelation(prodobj)
    else:
        ob.productClass.removeRelation()
    ob.setIpService()

DBSrvInst.setProductKey = setProductKey2

# for each modeler plugin, set the productKey/ProductClass property
# separate UI page for adding relations between productClass to ServiceClass/OSProcessClass



###############################################################

''' 
functions for manipulating component productClass relationships
'''

DeviceComponent.setProduct = setProduct
DeviceComponent.updateDataMap = updateDataMap
DeviceComponent.setProductKey = setProductKey
DeviceComponent.setAssociatedProductKey = setAssociatedProductKey

###############################################################


''' 
functions for finding devices and components in catalogs
'''

DeviceComponent.findDevice = findDevice
DeviceComponent.findDeviceComponent = findDeviceComponent
DeviceComponent.findComponent = findComponent
DeviceComponent.findBrainsObject = findBrainsObject
DeviceComponent.closestMatch = closestMatch

''' 
functions for manipulating component relations
'''

DeviceComponent.unsetCustomRelation = unsetCustomRelation
DeviceComponent.setCustomRelation = setCustomRelation
DeviceComponent.removeCustomRelations = removeCustomRelations
DeviceComponent.updateCustomRelations = updateCustomRelations


'''
below are methods that can be used to synchronize monitor state between grouped components
'''

DeviceComponent.getAssociates = getAssociates
CustomComponent.getAssociates = getAssociates

DeviceComponent.monitorToggle = monitorToggle
DeviceComponent.monitorDefault = monitorDefault
DeviceComponent.syncMonitored = syncMonitored
DeviceComponent.syncAssociates = syncAssociates
DeviceComponent.resetAssocates = resetAssocates

OSComponent.updateDataMap = updateDataMap
CustomComponent.updateDataMap = updateDataMap

OSComponent.manage_deleteComponent = manage_deleteComponent
CustomComponent.manage_deleteComponent = manage_deleteComponent

OSComponent.manage_updateComponent = manage_updateComponent
CustomComponent.manage_updateComponent = manage_updateComponent

'''patch for Facade'''

from Products.Zuul.facades.devicefacade import *
DeviceFacade.setMonitor = setMonitor



class ZenPack(ZenPackBase):
    # All zProperties defined here will automatically be created when the
    # ZenPack is installed.
    def install(self, dmd):
        ZenPackBase.install(self, dmd)
        updateRelations(dmd, True)
        pass

    def remove(self, dmd, leaveObjects=False):
        if not leaveObjects: pass
        mgr.remove()
        updateRelations(dmd,True)
        #removeRelations(relmgr)
        ZenPackBase.remove(self, dmd, leaveObjects=leaveObjects)
        

