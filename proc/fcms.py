import io.file
import os
import re
import string
import template.tabletemplate
import ConfigParser
import dbus
import proc.pci
import sys
import proc.base

class Fcms(proc.base.Base):
    asset_info = []

    def getData(self, options):
        system_bus = dbus.SystemBus()
        try:
            import gudev
            self.getUdevDevs(options)
        except ImportError:
            hal_mgr_obj = system_bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
            self.getHalDevs(options)

    def getUdevDevs(self, options):
        import gudev
        client = gudev.Client(["fc_host"])
        devs = client.query_by_subsystem("fc_host")
        pciinfo = proc.pci.Pci()
        pciinfo.getData(options)
        
        for dev in devs:
                props = {}
                parentdev = dev.get_parent()
                grandparent = parentdev.get_parent()
                vendorhex = grandparent.get_sysfs_attr('vendor')
                vendorhex = string.replace(vendorhex, '0x', '')
                hostregex = re.compile('\/([a-zA-Z0-9:.]+)\/host[0-9]+')
                hostmatch = hostregex.search(dev.get_sysfs_path())
                                    
                if hostmatch:
                    props['pcicard'] = hostmatch.group(1)
                                        
                props['pci.vendor'] = pciinfo.pciids['vendors'][vendorhex]
                props['linux.sysfs_path'] = dev.get_sysfs_path()
                props['nodename'] = dev.get_sysfs_attr('node_name')
                props['portname'] = dev.get_sysfs_attr('port_name')
                props['portstate'] = dev.get_sysfs_attr('port_state')
                props['porttype'] = dev.get_sysfs_attr('port_type')
                props['speed'] = dev.get_sysfs_attr('speed')
                props['driver'] = grandparent.get_property('DRIVER')
                props['irq'] = grandparent.get_sysfs_attr('irq')
                props['numanode'] = grandparent.get_sysfs_attr('numa_node')
                props['localcpulist'] = grandparent.get_sysfs_attr('local_cpulist')
                props['localcpus'] = grandparent.get_sysfs_attr('local_cpus')
                props['fabricname'] = dev.get_sysfs_attr('fabric_name')
                props['supportedclasses'] = dev.get_sysfs_attr('supported_classes')
                props['supportedspeeds'] = dev.get_sysfs_attr('supported_speeds')
                props['maxnpivvports'] = dev.get_sysfs_attr('max_npiv_vports')
                props['npivvportsinuse'] = dev.get_sysfs_attr('npiv_vports_inuse')
                props['portid'] = dev.get_sysfs_attr('port_id')
                props['symbolicname'] = dev.get_sysfs_attr('symbolic_name')

                props['toolindex'] = props['pcicard']
                
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
                classNum = interface.GetProperty('pci.device_class')
                subclassNum = interface.GetProperty('pci.device_subclass')
                
                if classNum == 12 and subclassNum == 4:
                    props = interface.GetAllProperties()
                    pcipath = os.listdir(props['linux.sysfs_path'])
                    
                    for path in pcipath:
                        pattern = re.compile('host[0-9]+')
                        mpath = pattern.search(path)
                        
                        if mpath:
                            hostdir = props['linux.sysfs_path'] + '/' + mpath.group(0)
                            hostpath = os.listdir(hostdir)
                            
                            for hostp in hostpath:
                                pattern = re.compile('fc_host.*')
                                scsipattern = re.compile('scsi_host.*')
                                hostpp = pattern.search(hostp)
                                scsihostpp = scsipattern.search(hostp)
                                
                                if hostpp:
                                    hostregex = re.compile('\/([a-zA-Z0-9:.]+)$')
                                    hostmatch = hostregex.search(props['linux.sysfs_path'])
                                    
                                    if hostmatch:
                                        props['pcicard'] = hostmatch.group(1)
                                    
                                    irq = io.file.readFile(props['linux.sysfs_path'] + '/irq')
                                    local_cpus = io.file.readFile(props['linux.sysfs_path'] + '/local_cpus')                                    
                                    
                                    nodename = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'node_name')
                                    portname = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'port_name')
                                    portstate = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'port_state')
                                    porttype = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'port_type')
                                    speed = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'speed')
                                    fabricname = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'fabric_name')
                                    supported_classes = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'supported_classes')
                                    supported_speeds = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'supported_speeds')
                                    port_id = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'port_id')
                                    symbolic_name = io.file.readFile(hostdir + '/' + hostpp.group(0) + '/' + 'symbolic_name')
                                    
                                    props['nodename'] = nodename[0].strip()
                                    props['portname'] = portname[0].strip()
                                    props['portstate'] = portstate[0].strip()
                                    props['porttype'] = porttype[0].strip()
                                    props['speed'] = speed[0].strip()
                                    props['localcpus'] = local_cpus[0].strip()
                                    props['irq'] = irq[0].strip()
                                    props['numanode'] = ''
                                    props['localcpulist'] = ''
                                    props['driver'] = props['info.linux.driver']
                                    props['fabricname'] = fabricname[0].strip()
                                    props['supportedclasses'] = supported_classes[0].strip()
                                    props['supportedspeeds'] = supported_speeds[0].strip()
                                    props['portid'] = port_id[0].strip()
                                    props['symbolicname'] = symbolic_name[0].strip()
                                
                                if scsihostpp:
                                    max_npiv_vports = io.file.readFile(hostdir + '/' + scsihostpp.group(0) + '/' + 'max_npiv_vports')
                                    npiv_vports_inuse = io.file.readFile(hostdir + '/' + scsihostpp.group(0) + '/' + 'npiv_vports_inuse')
                                    
                                    props['maxnpivvports'] = max_npiv_vports[0].strip()
                                    props['npivvportsinuse'] = npiv_vports_inuse[0].strip()
                                    
                    props['toolindex'] = props['pcicard']
                    
                    self.asset_info.append(props)

            except dbus.DBusException:
                continue
