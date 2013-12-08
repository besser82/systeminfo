import io.file
import os
import re
import string
import template.tabletemplate
import ConfigParser
import sys
import proc.base
import platform
import csv
import dbus

class Pci(proc.base.Base):
        pciids = {'vendors' : {}, 'devices' : {}, 'classes' : {}, 'subclasses' : {}, 'subdevs' : {}}
        pcidevs = []
        asset_info = []
        
        def getData(self, options):
            isclasssection = 0
            currentclass = ''
            currentvend = ''
                
            f = open('/usr/share/hwdata/pci.ids', 'r')
            for line in f:
                vend = re.search('^(\w+)\s*(.*)', line)
                dev = re.search('^\t(\w+)\s*(.*)$', line)
                subdev = re.search('^\t\t(\w+)\s+(\w+)\s+(.*)$', line)
                isclasssec = re.search('^C\s+(\w{2,4})\s+(.*)$', line)
                issubclass = re.search('^\t(\w{2,4})\s+(.*)$', line)
                        
                if isclasssec:
                    isclasssection = 1
                                
                if isclasssection:
                    if isclasssec:
                        self.pciids['classes'][isclasssec.group(1)] = isclasssec.group(2)
                        currentclass = isclasssec.group(1)
                    elif issubclass:
                        if currentclass not in self.pciids['subclasses'].keys():
                            self.pciids['subclasses'][currentclass] = {}
                        
                        self.pciids['subclasses'][currentclass][issubclass.group(1)] = issubclass.group(2)
                elif vend:
                    self.pciids['vendors'][vend.group(1)] = vend.group(2)
                    currentvend = vend.group(1)
                elif dev:
                    if currentvend not in self.pciids['devices'].keys():
                        self.pciids['devices'][currentvend] = {}
                            
                    self.pciids['devices'][currentvend][dev.group(1)] = dev.group(2)
                elif subdev:
                    if currentvend not in self.pciids['subdevs'].keys():
                        self.pciids['subdevs'][currentvend] = {}

                    self.pciids['subdevs'][currentvend][subdev.group(1) + subdev.group(2)] = subdev.group(3)

            f.close()

            self.pcidevs = os.listdir('/sys/bus/pci/devices')

            system_bus = dbus.SystemBus()
            
            try:
                import gudev
                self.getUdevDevs(options)
            except ImportError:
                hal_mgr_obj = system_bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
                self.getHalDevs(options)
                                   
        def getUdevDevs(self, options):
            import gudev
            client = gudev.Client(["pci"])
            devs = client.query_by_subsystem("pci")
            
            for dev in devs:
                props = {}
                
                vendorhex = dev.get_sysfs_attr('vendor')
                devhex = dev.get_sysfs_attr('device')
                classhex = dev.get_sysfs_attr('class')
                subvendhex = dev.get_sysfs_attr('subsystem_vendor')
                subdevhex = dev.get_sysfs_attr('subsystem_device')
                
                vendorhex = string.replace(vendorhex, '0x', '')
                devhex = string.replace(devhex, '0x', '')
                classhex = string.replace(classhex, '0x', '')
                subvendhex = string.replace(subvendhex, '0x', '')
                subdevhex = string.replace(subdevhex, '0x', '')
                subdevid = subvendhex + subdevhex
                
                subdevice = ''
                
                classreg = re.search('^(\w{2})(\w{2})(\w{2})', classhex)
                
                if vendorhex in self.pciids['subdevs'].keys():
                    if subdevid in self.pciids['subdevs'][vendorhex].keys():
                        subdevice = self.pciids['subdevs'][vendorhex][subdevid]
                    
                props['addr'] = dev.get_property('PCI_SLOT_NAME')
                props['vendor'] = self.pciids['vendors'][vendorhex]
                props['device'] = self.pciids['devices'][vendorhex][devhex]
                props['class'] = self.pciids['classes'][classreg.group(1)]
                props['subclass'] = self.pciids['subclasses'][classreg.group(1)][classreg.group(2)]
                props['subdevice'] = subdevice
                props['driver'] = dev.get_property('DRIVER')
                props['sysfspath'] = dev.get_sysfs_path()
                props['localcpus'] = dev.get_sysfs_attr('local_cpus')
                props['irq'] = dev.get_sysfs_attr('irq')
                props['numanode'] = dev.get_sysfs_attr('numa_node')
                props['localcpulist'] = dev.get_sysfs_attr('local_cpulist')
                
                props['toolindex'] = props['addr']
                
                self.asset_info.append(props)
                    
        def getHalDevs(self, options):
            system_bus = dbus.SystemBus()
            hal_mgr_obj = system_bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
            hal_mgr_iface = dbus.Interface(hal_mgr_obj, 'org.freedesktop.Hal.Manager')
            devs = hal_mgr_iface.GetAllDevices()
            
            for i in devs:
                dev = system_bus.get_object('org.freedesktop.Hal', i)
                interface = dbus.Interface(dev, dbus_interface='org.freedesktop.Hal.Device')
                
                try:
                    subsystem = interface.GetProperty('linux.subsystem')
                    
                    if subsystem == 'pci':
                        props = interface.GetAllProperties()
                        addr_match = re.search('.*?\/([a-zA-Z:0-9\.]+)$', props['linux.sysfs_path'])
                        addr = ''
                        subdevice = ''
                        
                        irq = io.file.readFile(props['linux.sysfs_path'] + '/irq')
                        local_cpus = io.file.readFile(props['linux.sysfs_path'] + '/local_cpus')
                        
                        if addr_match:
                            addr = addr_match.group(1)
                        
                        vendorhex = props['pci.vendor_id']
                        classhex = hex(props['pci.device_class'])
                        subclasshex = hex(props['pci.device_subclass'])
                        subvendhex = hex(props['pci.subsys_vendor_id'])
                        subdevhex = hex(props['pci.subsys_product_id'])
                        
                        vendorhex = string.replace(str(vendorhex), '0x', '')
                        classhex = "%02x" % int(classhex[2:], 16)
                        subclasshex = "%02x" % int(subclasshex[2:], 16)
                        subvendhex = "%02x" % int(subvendhex[2:], 16)
                        subdevhex = "%02x" % int(subdevhex[2:], 16)
                        subdevid = subvendhex + subdevhex

                        if vendorhex in self.pciids['subdevs'].keys():
                            if subdevid in self.pciids['subdevs'][vendorhex].keys():
                                subdevice = self.pciids['subdevs'][vendorhex][subdevid]
                            
                        props['addr'] = addr
                        props['vendor'] = props['pci.vendor']
                        props['device'] = props['pci.product']
                        props['class'] = self.pciids['classes'][classhex]
                        props['subclass'] = self.pciids['subclasses'][classhex][subclasshex]
                        props['subdevice'] = subdevice
                        props['sysfspath'] = props['linux.sysfs_path']
                        props['localcpus'] = local_cpus[0].strip()
                        props['irq'] = irq[0].strip()
                        props['numanode'] = ''
                        props['local_cpulist'] = ''
                        
                        if 'info.linux.driver' in props.keys():
                            props['driver'] = props['info.linux.driver']
                            
                        props['toolindex'] = props['addr']
                        
                        self.asset_info.append(props)

                except dbus.DBusException:
                    continue
