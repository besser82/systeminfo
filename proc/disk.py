import re
import os
import dbus
from string import Template
import template.tabletemplate
import ConfigParser
import string
import glob
import sys
import io
import proc.base

class Disk(proc.base.Base):
    lunsbypath = {}
    diskdesc = {}
    asset_info = []
    fields = [
                'targetport', 
                'storage.serial', 
                'lunid', 
                'storage.model', 
                'storage.vendor', 
                'storage.size', 
                'hwpath', 
                'srcport',
                'rportstate'
            ]
    
    def getData(self, options):
        self.getLunsByPath()
        self.getDiskDesc()
        
        for disk, info in self.diskdesc.iteritems():
        
            for key in self.fields:
                if key not in self.diskdesc[disk].keys():
                    self.diskdesc[disk][key] = ''

            diskinfo = {    
                            'toolindex': self.diskdesc[disk]['hwpath'],
                            'device': disk,
                            'targetport': self.lunsbypath[disk]['targetport'],
                            'id': str(self.diskdesc[disk]['storage.serial']),
                            'lunid': str(self.lunsbypath[disk]['lunid']),
                            'model': self.diskdesc[disk]['storage.model'],
                            'vendor': self.diskdesc[disk]['storage.vendor'],
                            'size': "%.f" % (self.diskdesc[disk]['storage.size']),
                            'hwpath': self.diskdesc[disk]['hwpath'],
                            'srcport': self.diskdesc[disk]['srcport'],
                            'rportstate': self.diskdesc[disk]['rportstate'],
                            'major': str(self.diskdesc[disk]['block.major']),
                            'minor': str(self.diskdesc[disk]['block.minor']),
                            'firmware': str(self.diskdesc[disk]['storage.firmware_version']),
                            'iodone_count': str(self.diskdesc[disk]['iodone_count']),
                            'ioerror_count': str(self.diskdesc[disk]['ioerror_count']),
                            'iorequest_count': str(self.diskdesc[disk]['iorequest_count']),
                            'queue_depth': str(self.diskdesc[disk]['queue_depth']),
                            'scsi_level': str(self.diskdesc[disk]['scsi_level']),
                            'state': self.diskdesc[disk]['state'],
                            'timeout': str(self.diskdesc[disk]['timeout']),
                    }

            self.asset_info.append(diskinfo)
            
    def getLunsByPath(self):
        disk_by_path = os.listdir('/dev/disk/by-path')
        fcpat = re.compile('.*-fc-(0x[0-9a-z]+)[:-]((lun-)?(0x)?[0-9a-z]+)$')
        dskpat = re.compile('(sd[a-z]+)')

        for disk in disk_by_path:
            match = fcpat.search(disk)
            if match:
                target_port = match.group(1)
                lun_id = match.group(2)
                target = os.readlink('/dev/disk/by-path' + '/' + match.group(0))
                dskmatch = dskpat.search(target)
                
                if dskmatch:
                    diskdev = dskmatch.group(1)
                    self.lunsbypath[diskdev] = {}
                    self.lunsbypath[diskdev]['targetport'] = target_port
                    self.lunsbypath[diskdev]['lunid'] = lun_id

            else:
                target = os.readlink('/dev/disk/by-path/'+disk)
                dskmatch = dskpat.search(target)
                if dskmatch:
                        diskdev = dskmatch.group(1)
                        self.lunsbypath[diskdev] = {}
                        self.lunsbypath[diskdev]['targetport'] = ''
                        self.lunsbypath[diskdev]['lunid'] = ''

    def getDiskDesc(self):
        system_bus = dbus.SystemBus()
        try:
            import gudev
            self.getUdevDesc()
        except ImportError:
            hal_mgr_obj = system_bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
            self.getHalDesc()
            
    def getHalDesc(self):
        system_bus = dbus.SystemBus()
        hal_mgr_obj = system_bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
        hal_mgr_iface = dbus.Interface(hal_mgr_obj, 'org.freedesktop.Hal.Manager')
        devs = hal_mgr_iface.GetAllDevices()

        for i in devs:
            dev = system_bus.get_object('org.freedesktop.Hal', i)
            interface = dbus.Interface(dev, dbus_interface='org.freedesktop.Hal.Device')

            if interface.PropertyExists('info.category'):
                category = interface.GetProperty('info.category')
                if category == 'storage':
                    props = interface.GetAllProperties()
                    devpat = re.compile('/dev/(sd\w+)')
                    devname = devpat.search(props['block.device'])
                    
                    if devname:
                        props['storage.size'] = float(props['storage.size']) / 1000000.0
                        block_dev_path = props['linux.sysfs_path'] + '/device'
                        parentdev = system_bus.get_object('org.freedesktop.Hal', props['info.parent'])
                        parentiface =dbus.Interface(parentdev, dbus_interface='org.freedesktop.Hal.Device')
                        hwpath = parentiface.GetProperty('linux.sysfs_path')
                        rportregex = re.compile('(.*\/rport-[0-9:-]+\/).*')
                        hwregex = re.compile('.*?\/([a-zA-Z0-9:.]+)$')
                        hostregex = re.compile('\/([a-zA-Z0-9:.]+)\/host[0-9]+')
                        hwmatch = hwregex.search(hwpath)
                        hostmatch = hostregex.search(hwpath)
                        rportmatch = rportregex.search(hwpath)
                        
                        iodone_count = io.file.readFile(block_dev_path + '/iodone_cnt')
                        ioerror_count = io.file.readFile(block_dev_path + '/ioerr_cnt')
                        iorequest_count = io.file.readFile(block_dev_path + '/iorequest_cnt')
                        queue_depth = io.file.readFile(block_dev_path + '/queue_depth')
                        scsi_level = io.file.readFile(block_dev_path + '/scsi_level')
                        state = io.file.readFile(block_dev_path + '/state')
                        timeout = io.file.readFile(block_dev_path + '/timeout')
                        
                        props['iodone_count'] = int(iodone_count[0].strip(), 16)
                        props['ioerror_count'] = int(ioerror_count[0].strip(), 16)
                        props['iorequest_count'] = int(iorequest_count[0].strip(), 16)
                        props['queue_depth'] = queue_depth[0].strip()
                        props['scsi_level'] = scsi_level[0].strip()
                        props['state'] = state[0].strip()
                        props['timeout'] = timeout[0].strip()
                        
                        if rportmatch:
                            rportdir = glob.glob(rportmatch.group(1) + 'fc_remote_ports*')
                            rportstate = io.file.readFile(rportdir[0] + '/port_state')
                            props['rportstate'] = rportstate[0].strip()
                        
                        if hwmatch:
                            props['hwpath'] = hwmatch.group(1)
                         
                        if hostmatch:
                            props['srcport'] = hostmatch.group(1)
                        
                        self.diskdesc[devname.group(1)] = props

                
    def getUdevDesc(self):
        import gudev
        client = gudev.Client(["block"])
        devs = client.query_by_subsystem("block")
        devpat = re.compile('/dev/(sd\w+)')

        for dev in devs:
            devicename = dev.get_property('DEVNAME')
            devtype = dev.get_property('DEVTYPE')
            devpath = dev.get_property('DEVPATH')

            if devtype == 'disk':
                devicematch = devpat.search(devicename)
                if devicematch:
                    devname = devicematch.group(1)
                    props = {}
                    self.diskdesc[devname] = {}

                    hwregex = re.compile('/([0-9:]+)/')
                    hostregex = re.compile('\/([a-zA-Z0-9:.]+)\/host[0-9]+')
                    hwmatch = hwregex.search(devpath)
                    hostmatch = hostregex.search(devpath)

                    blockdev = dev.get_parent()
                    lundev = blockdev.get_parent()
                    rport = lundev.get_parent()
                    rportsysfs = rport.get_sysfs_path()
                    rportpath = glob.glob(rportsysfs + '/' + 'fc_remote_ports' + '/' + 'rport-*')

                    if len(rportpath) > 0:
                        rportstate = io.file.readFile(rportpath[0] + '/' + 'port_state')
                        props['rportstate'] = rportstate[0].strip()

                    props['storage.vendor'] = dev.get_property('ID_VENDOR')
                    props['storage.model'] = dev.get_property('ID_MODEL')
                    props['storage.size'] = float(dev.get_sysfs_attr('size')) * 512 / 1000000.0
                    props['storage.serial'] = dev.get_property('ID_SERIAL')
                    props['block.major'] = dev.get_property('MAJOR')
                    props['block.minor'] = dev.get_property('MINOR')
                    props['storage.firmware_version'] = blockdev.get_sysfs_attr('rev')
                    props['state'] = blockdev.get_sysfs_attr('state')
                    props['timeout'] = blockdev.get_sysfs_attr('timeout')
                    props['scsi_level'] = blockdev.get_sysfs_attr('scsi_level')
                    props['queue_depth'] = blockdev.get_sysfs_attr('queue_depth')
                    props['iorequest_count'] = int(blockdev.get_sysfs_attr('iorequest_cnt'), 16)
                    props['iodone_count'] = int(blockdev.get_sysfs_attr('iodone_cnt'), 16)
                    props['ioerror_count'] = int(blockdev.get_sysfs_attr('ioerr_cnt'), 16)
                    
                    if hwmatch:
                        props['hwpath'] = hwmatch.group(1)

                    if hostmatch:
                        props['srcport'] = hostmatch.group(1)

                    self.diskdesc[devname] = props