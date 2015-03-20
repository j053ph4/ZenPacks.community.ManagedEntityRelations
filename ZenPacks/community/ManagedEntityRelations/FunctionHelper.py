import Globals
from Products.ZenUtils.Utils import *
from RelationHelper import *
import difflib
unused(Globals)

def setProduct(ob, productName,  manufacturer="Unknown",
                newProductName="", REQUEST=None, **kwargs):
    """Set the product class of this software.
    """
    if not manufacturer: manufacturer = "Unknown"
    if newProductName: productName = newProductName
    prodobj = ob.getDmdRoot("Manufacturers").createSoftwareProduct(
                                productName, manufacturer, **kwargs)
    ob.productClass.addRelation(prodobj)
    if REQUEST:
        messaging.IMessageSender(ob).sendToBrowser(
            'Product Set',
            ("Set Manufacturer %s and Product %s."
                                % (manufacturer, productName))
        )
        return ob.callZenScreen(REQUEST)
    
def setProductKey(ob, prodKey, manufacturer=None):
    """Set the product class of this software by its productKey.
    """
    log.debug("setProductKey on %s" % (ob.id))
    if prodKey:
        # Store these so we can return the proper value from getProductKey
        ob._prodKey = prodKey
        ob._manufacturer = manufacturer
        if manufacturer is None:
            manufacturer = 'Unknown'
        manufs = ob.getDmdRoot("Manufacturers")
        prodobj = manufs.createSoftwareProduct(prodKey, manufacturer)
        ob.productClass.addRelation(prodobj)
        # set product class for associated components
        for a in ob.getAssociates():
            if a.meta_type in ['OSProcess','IpService','WinService']:  
                try:
                    log.debug("setting associate relation on %s" % a.id)
                    a.productClass.addRelation(prodobj)
                except:  pass
    else:
        ob.productClass.removeRelation()
        
def setAssociatedProductKey(ob):
    """ Set the productClass relation for associated OSProcess, 
        IpService, and WinService components
    """
    product = ob.getProductKey()
    for a in ob.getAssociates():
        if a.meta_type in ['OSProcess','IpService','WinService']:  a.setProductKey(product)

###############################################################


''' 
functions for finding devices and components in catalogs
'''
def findDevice(ob, match, attribute='manageIp'):
    ''' find Zenoss device matching provided attribute and match'''
    log.debug('findDevice on %s matching %s: %s' % (ob.id, attribute, match))
    brains = ob.getDmd().Devices.deviceSearch()
    return ob.findBrainsObject(brains, attribute, match, .95)

def findDeviceComponent(ob, device, metatype, attribute, match):
    ''' find Zenoss component matching provided attribute and match'''
    if device is not None:
        log.debug('findDeviceComponent on %s matching %s: %s: %s: %s' % (ob.id, device.id, metatype, attribute, match))
        brains = device.componentSearch(meta_type=metatype)
        # process list matches one at a time
        if type(match) == list:
            output = []
            for m in match: output.append(ob.findBrainsObject(brains, attribute, m))
            return output
        else:
            return ob.findBrainsObject(brains, attribute, match)
    return None

def findComponent(ob, metatype, attribute, match):
    ''' find Zenoss component matching provided attribute and match'''
    log.debug('findComponent on %s for %s matching %s: %s' % (ob.id, metatype, attribute, match))
    brains = ob.getDmd().global_catalog(meta_type=metatype)
    return ob.findBrainsObject(brains, attribute, match)

def findBrainsObject(ob, brains, attribute, match, cutoff=.8):
    '''find an object in the given catalog (brains) with matching attribute'''
    log.debug('findBrainsObject on %s matching %s: %s' % (ob.id, attribute, match))
    # build a dictionary of match attributes
    if attribute is not None and match is not None:
        matchers = {}
        for b in brains:
            ob = b.getObject()
            matcher = getattr(ob, attribute)
            #log.debug("got matcher %s for ob: %s" % (matcher, ob.id))
            # testing to see if the matcher attribute is itself a relationship
            if hasattr(matcher,'meta_type'):
                log.debug("matcher meta_type: %s" % matcher.meta_type)
                if "Relationship" in matcher.meta_type:  matcher = matcher()
            # if the matcher is a list property, then convert it to a space-delimited string
            if type(matcher) == list:  
                log.debug("matcher: %s is list" % matcher)
                try:
                    # try using the id property if the objects are not strings
                    matchstring = ''
                    for x in matcher: matchstring += ' %s' % x.id
                    matcher = matchstring
                # otherwise assume they are strings
                except:  matcher = ' '.join(matcher)
            matchers[str(matcher)] = ob
        # find the closest matching attribute (by score) in the list of them
        bestMatch = ob.closestMatch(str(match), matchers.keys(), cutoff)
        # look for a substring match if the scored match finds nothing
        if bestMatch is None:
            for k,v in matchers.items():
                if str(match) in str(k): 
                    log.debug("returning direct match: %s" % v.id)
                    return v
        elif bestMatch in matchers.keys():
            log.debug("returning best score: %s" % matchers[bestMatch].id)
            return matchers[bestMatch]
        else: 
            log.debug("returning none")
            return None

def closestMatch(ob, match, matchlist, cutoff=.8):
    '''return the closest matching string given a list of strings'''
    score = 0
    best = None
    for m in matchlist:
        r = difflib.SequenceMatcher(None, match, m).ratio()
        if r > score:
            score = r
            best = m
    if score > cutoff: return best
    else: return None

''' 
functions for manipulating component relations
'''

def unsetCustomRelation(ob, relation):
    '''remove custom relation from this component '''
    log.debug('unsetCustomRelation %s on %s' % (ob.id, relation))
    try:
        rel = getattr(ob, relation)
        rel._remoteRemove()
        rel._remove()
    except:  log.warn("problem unsetting relation %s on %s" % (relation, ob.id))

def setCustomRelation(ob, object, torelation, fromrelation):
    ''' add custom relation to this component '''
    if object is not None:
        log.debug('setCustomRelation from %s (%s) to: %s (%s)' % (ob.id, torelation, object.id, fromrelation))
        try:
            torel = getattr(ob, torelation)
            fromrel = getattr(object, fromrelation)
            torel._add(object)                
            fromrel._add(ob)
        except RelationshipExistsError:  
            log.warn("relation exists...resetting relation on %s:%s from %s to %s" % (ob.id, object.id, fromrelation, torelation))
            #ob.unsetCustomRelation(torelation)
            torel = getattr(ob, torelation)
            fromrel = getattr(object, fromrelation)
            try: torel._remove(object) 
            except:  
                log.warn("error removing torel")
                pass
            try: fromrel._remove(ob)
            except:  
                log.warn("error removing fromrel")
                pass
            try: ob.setCustomRelation(object, torelation, fromrelation)
            except: log.warn("problem resetting relation on %s:%s from %s to %s" % (ob.id, object.id, fromrelation, torelation))
        except: log.warn("problem setting relation on %s:%s from %s to %s" % (ob.id, object.id, fromrelation, torelation))

def removeCustomRelations(ob):
    ''' remove custom component relations '''
    log.debug('removeCustomRelations on %s' % ob.id)
    try: compname = ob.compname
    except: compname = 'os'
    diffs = [x for x in ob._relations if (x not in OSComponent._relations and x[0] != compname)]
    for d in diffs: 
        log.debug("REMOVING RELATION %s" % d[0])
        print "REMOVING RELATION %s" % d[0]
        ob.unsetCustomRelation(d[0])

def updateCustomRelations(ob):
    ''' update component relations based on setter methods in _properties '''
    log.debug('updateCustomRelations on %s' % ob.id)
    ignoreKeys = ['productionState','preMWProductionState','eventClass',]
    ob.removeCustomRelations()
    for data in ob._properties:
        if data['id'] in ignoreKeys:  continue
        if 'setter' in data.keys():
            action = getattr(ob, data['setter'])
            action()
    #ob.setFixedPasswords()



'''
below are methods that can be used to synchronize monitor state between grouped components
'''

def getAssociates(ob):
    ''' find objects associated with this one '''
    
    def isOSComponent(obj):
        '''determine if object is a descendant of OSComponent class'''
        import inspect
        klass = obj.__class__
        for b in inspect.getmro(klass):
            if b.__name__ == 'OSComponent': return True
        return False
    
    associates = []
    for rel in ob.getRelationshipNames():
        try: target = getattr(ob, rel)()
        except: target = None
        if target is not None: 
            if type(target) == list:
                for t in target:  
                    if isOSComponent(t) is True: associates.append(t)
            else:
                if isOSComponent(target) is True: associates.append(target)
    return associates

def monitorToggle(ob, enabled=True):
    '''toggle component monitored state'''
    log.debug("monitorToggle on %s" % ob.id)
    try: ob.setAqProperty("zMonitor", enabled, "boolean")
    except:  ob.monitor = enabled

def monitorDefault(ob): 
    '''reset to default'''
    log.debug("monitorDefault on %s" % ob.id)
    try: ob.deleteZenProperty('zMonitor')
    except:  pass

def syncMonitored(ob, associate):
    '''set associated component to same monitored state'''
    log.debug("syncMonitored from %s to %s" % (ob.id, associate.id))
    associate.monitorToggle(ob.monitored())

def syncAssociates(ob):
    '''set associated components to same monitored state as this one'''
    log.debug("syncAssociates on %s" % ob.id)
    target = ob.monitored()
    for associate in ob.getAssociates():
        log.debug("setting %s associate: %s zMonitor to %s" % (ob.id, associate.id, target))
        associate.monitorToggle(target)

def resetAssocates(ob):
    '''reset associated monitored property'''
    log.debug("resetAssociates on %s" % ob.id)
    for associate in ob.getAssociates():
        log.debug("resetting %s associate: %s monitored" % (ob.id, associate.id))
        associate.monitorDefault()

'''
    patched overrides of built-in methods to accommodate relation updates
'''
def updateDataMap(ob, datamap): 
    '''pass-through for later override'''
    log.debug("updateDataMap for %s: %s" % (ob.id,datamap))
    return datamap

def manage_deleteComponent(ob, REQUEST=None):
    """
    Delete OSComponent
    """
    log.debug('updated manage_deleteComponent on %s' % ob.id)
    url = None
    if REQUEST is not None: url = ob.device().os.absolute_url()
    #ob.resetAssocates()
    associates = ob.getAssociates()
    ob.removeCustomRelations()
    ob.getPrimaryParent()._delObject(ob.id)
    for associate in associates: 
        log.debug("deleting %s associate: %s" % (ob.id, associate.id)) 
        associate.getPrimaryParent()._delObject(associate.id)
    if REQUEST is not None: REQUEST['RESPONSE'].redirect(url)

def manage_updateComponent(ob, datamap, REQUEST=None):
    """
    Update OSComponent
    """
    log.debug('updated manage_updateComponent on %s' % ob.id)
    url = None
    if REQUEST is not None: url = ob.device().os.absolute_url()
    ob.updateCustomRelations()
    ob.syncAssociates()
    datamap = ob.updateDataMap(datamap)
    ob.getPrimaryParent()._updateObject(ob, datamap)
    if REQUEST is not None: REQUEST['RESPONSE'].redirect(url)

'''patch for Facade'''

def setMonitor(ob, uids, monitor=False):
    '''patching this facade method so that it calls the "syncAssociates" method'''
    comps = imap(ob._getObject, uids)
    for comp in comps:
        IInfo(comp).monitor = monitor
        # patched to synchronize associated components
        comp.syncAssociates()
        # update the componentSearch catalog
        comp.index_object(idxs=('monitored',))
        # update the global catalog as well
        notify(IndexingEvent(comp, idxs=('monitored',)))
        

