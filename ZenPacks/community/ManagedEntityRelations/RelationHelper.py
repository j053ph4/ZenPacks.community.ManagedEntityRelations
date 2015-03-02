from ZenPacks.community.ConstructionKit.CustomRelations import *
from ZenPacks.community.ConstructionKit.ZenPackHelper import *
import logging
log = logging.getLogger('zen.zenhub')

    
# - add setter methods to built-in component types for IpService, OSProcess, WinService, etc
# - add 'setCustomProp' method from CustomComponent to DeviceComponent
# patch manage_updateComponent
# patch manage_deleteComponent
# patch manage_addComponent
# patch setCustomRelation
# patch unsetCustomRelation
# patch removeCustomRelations
# patch updateCustomRelations
# patch updateCustomRelations
# patch updateCustomRelations
# patch _setPropValue
# patch setCustomProp

# set method text
SETTEXT = '''def %s(ob, name=''): 
    match = ob.findDeviceComponent(device=ob.device(), metatype='%s', attribute='%s', match=ob.%s)
    if type(match) == list:
        for m in match: 
            ob.setCustomRelation(object=m, torelation='%s', fromrelation='%s')
    else: ob.setCustomRelation(object=match, torelation='%s', fromrelation='%s')
'''
# get method text
GETTEXT = '''def %s(ob):  return ob.findDeviceComponent(device=ob.device(), metatype='%s', attribute='%s', match=ob.%s)\n'''


class RelationHelper(CustomRelations):
    ''''''
    # list of tuple (CLASS, RELATION)
    targetrelations = []
    
    def relationInfo(self, fromName, fromType, fromClass, fromAttribute, toName, toType, toClass, toAttribute):
        '''return a dictionary describing the relation'''
        info = {
                'source': self.endpointInfo(fromName, fromType, fromClass, fromAttribute),
                'dest': self.endpointInfo(toName, toType, toClass, toAttribute),
                }
        
        info['source']['relation'] = (toName, toType(fromType, toClass, fromName))
        info['dest']['relation'] = (fromName, fromType(toType, fromClass, toName))
        return info
    
    def endpointInfo(self, name, ktype, klass, attribute):
        '''returns dictionary describing endpoint'''
        module = self.import_class(klass)
        return {
                'name': name,
                'type': ktype,
                'class': klass,
                'attribute': attribute,
                'target': module,
                'children': self.inheritors(module),
                }
    
    def inheritors(self, klass):
        '''find all subclasses that inherit properties from this class'''
        subclasses = set()
        work = [klass]
        while work:
            parent = work.pop()
            for child in parent.__subclasses__():
                if child not in subclasses:
                    subclasses.add(child)
                    work.append(child)
        return subclasses
    
    def add(self, fromName, fromType, fromClass, fromAttribute, toName, toType, toClass, toAttribute):
        '''add to list of relations'''
        info = self.relationInfo(fromName, fromType, fromClass, fromAttribute, toName, toType, toClass, toAttribute)
        if info not in self.relations:  self.relations.append(info)
    
    def createRelations(self):
        '''build list of from relations'''
        for r in self.relations: self.createRelation(r)
    
    def createRelation(self, info):
        '''check existence and create relations if needed'''
        source = info['source']
        dest = info['dest']
        # from relation
        #fromRelation = (dest['name'], dest['type'](source['type'], dest['class'], source['name']))
        #print source['relation']
        self.checkAttributeAndRelation(source['target'], source['relation'], source['attribute'])
        # add relation to all children
        for child in source['children']: self.checkAttributeAndRelation(child, source['relation'], source['attribute'])
        # to relation
        #toRelation = (source['name'], source['type'](dest['type'], source['class'], dest['name']))
        #print dest['relation']
        # to attribute
        self.checkAttributeAndRelation(dest['target'], dest['relation'], dest['attribute'])
        # add relation to all children
        for child in dest['children']: self.checkAttributeAndRelation(child, dest['relation'], dest['attribute'])
    
    def checkAttributeAndRelation(self, target, relation, attribute):
        '''update the local dictionary, create the relation, add to target relations, and set attribute if needed'''
        rel = (target, relation)
        if rel not in self.targetrelations:  self.targetrelations.append(rel)
        # only if attribute is defined
        if attribute is not None:
            # only if attribute/relation is not already defined
            if self.checkAttribute(target, attribute) is False: setattr(target, attribute, None)
    
    def checkAttribute(self, target, attribute):
        '''see if target class already has a property or relation named attribute'''
        if hasattr(target, '_relations') is True:
            relnames = [x[0] for x in target._relations]
            #print "cheking %s for attribute %s" % (target.__name__, attribute)
            if attribute in relnames: return True
        if hasattr(target, attribute) is True: return True
        return False  
    
    def install(self):
        ''''''
        self.createRelations()
        self.addRelations()
        self.addGetSetMethods()
    
    def remove(self):
        ''''''
        self.createRelations()
        self.removeRelations()
    
    def info(self):
        '''print out info on source/dest classes and their relations'''
        for r in self.relations:
            source = self.import_class(r['source']['class'])
            sourcerels = [x[0] for x in source._relations]
            dest = self.import_class(r['dest']['class'])
            destrels = [x[0] for x in dest._relations]
            print "FROM %s: %s" % (source.__name__, ' '.join(sourcerels))
            print "TO %s: %s" % (dest.__name__, ' '.join(destrels))
    
    def addRelations(self):
        '''decide whether or not to add new relation'''
        for target, relation in self.targetrelations:
            relname, schema = relation
            add = True
            for x in target._relations:
                if x[0] == relname: add = False
            if add is True:
                #print "adding %s relation to class: %s" % (relname, target.__name__)
                target._relations += (relation,)
    
    def removeRelations(self):
        '''remove custom relations'''
        for target, relation in self.targetrelations:
            relname, schema = relation
            #print "removing relation %s from local class %s to remote class: %s" % (relname, target.__name__, schema.remoteClass)
            target._relations = tuple([x for x in target._relations if x[0] not in (relname)])
    
    def addGetSetMethods(self):
        '''create get/set methods and add to source class'''
        from ZenPacks.community.ConstructionKit.ClassHelper import stringToMethod
        for rel in self.relations:
            source = rel['source']
            dest = rel['dest']
            # skip if attributes not specified
            if dest['attribute'] is None or source['attribute'] is None:
                log.info("skipping get/set for %s to %s" % (source['name'], dest['name']))
                continue
            self.addGetSetMethod(source['target'], source['name'], source['attribute'], 
                                 dest['target'], dest['name'], dest['attribute'])
            for child in source['children']:
                self.addGetSetMethod(child, source['name'], source['attribute'], 
                                 dest['target'], dest['name'], dest['attribute'])
    
    def addGetSetMethod(self, fromKlass, fromName, fromAttribute, toKlass, toName, toAttribute):
        '''add a GET and SET method to the target class'''
        from ZenPacks.community.ConstructionKit.ClassHelper import stringToMethod
        # GET method name
        getname = "get%s" % toName.capitalize()
        #print "adding %s method to %s" % (getname, fromKlass.__name__)
        # GET method args
        getargs = (getname, toKlass.__name__, toAttribute, fromAttribute)
        # GET method
        getmethod = stringToMethod(getname, GETTEXT % getargs)
        # add GET method to target class
        setattr(fromKlass, getname, getmethod)
        # set method from source to dest
        setname = "set%s" % toName.capitalize()
        #print "adding %s method to %s" % (setname, fromKlass.__name__)
        #settext = SETTEXT
        setargs = (setname, toKlass.__name__, toAttribute, fromAttribute, toName, fromName, toName, fromName)
        setmethod = stringToMethod(setname, SETTEXT % setargs)
        setattr(fromKlass, setname, setmethod)
        
