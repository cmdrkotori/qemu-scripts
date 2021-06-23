#!/usr/bin/env python3
import sys
import os
from subprocess import Popen, call
from time import sleep
import itertools
from . import conf
from . import mounting

dnsmasq = None
smbd = None
smb = True
nohost = False
mirror = False 
spice = False
scream = False

host_conf = {}
guest_conf = {}

def hostnet_up():
  # NOTE: if we're going to support spawning multiple vms at the
  # same time, we'd only need to create br0 and tap0 once.  This
  # would imply some sort of tracking mechanism.  But that felt
  # less like simple scripts and more like bloated virt-manager,
  # so it's not happening.
  # oh btw, the taps need to be promiscuous for samba to work.
  global dnsmasq
  global smbd
  global smb
  global nohost
  
  if nohost:
    return
  
  #global nmbd
  # setup bridge
  call(['sudo', 'brctl','addbr','br0'])
  call(['sudo', 'ip', 'addr', 'add', '192.168.101.1/24',
	 'broadcast', '192.168.101.255', 'dev', 'br0'])
  call(['sudo', 'ip', 'link', 'set', 'dev', 'br0', 'address',
        '42:48:12:34:56:78'])
  call(['sudo', 'ip', 'link', 'set', 'br0', 'up'])

  # setup host's adapter
  call(['sudo', 'ip', 'tuntap', 'add', 'dev', 'tap0', 'mode', 'tap'])
  call(['sudo', 'ip', 'addr', 'add', '192.168.101.2',
	 'broadcast', '192.168.101.255', 'dev', 'tap0'])
  call(['sudo', 'ip', 'link', 'set', 'tap0', 'up', 'promisc', 'on'])
  call(['sudo', 'brctl', 'addif', 'br0', 'tap0'])

  # setup guest's adapter
  call(['sudo', 'ip', 'tuntap', 'add', 'dev', 'tap1', 'mode', 'tap'])
  call(['sudo', 'ip', 'link', 'set', 'tap1', 'up', 'promisc', 'on'])
  call(['sudo', 'brctl', 'addif', 'br0', 'tap1'])

  # fire up the servers
  dnsmasq = Popen(['sudo', 'dnsmasq', '-k',
                   '--interface=br0', '--bind-interfaces',
		   '--dhcp-range=192.168.101.10,192.168.101.254'])
  
def hostnet_down():
  global nohost
  global dnsmasq
  global smbd
  if nohost:
    return
  
  # kill daemons politely
  call(['sudo', 'kill', str(-15), str(dnsmasq.pid)])

  # remove taps from bridge
  call(['sudo', 'brctl', 'delif', 'br0', 'tap0'])
  call(['sudo', 'brctl', 'delif', 'br0', 'tap1'])

  # delete interfaces
  call(['sudo', 'ip', 'link', 'delete', 'tap1'])
  call(['sudo', 'ip', 'link', 'delete', 'tap0'])
  call(['sudo', 'ip', 'link', 'delete', 'br0'])


qemu_parts = {
  'emu': {
    'enable-kvm': '',
    'ctrl-grab': ''
  },
  'emu-nohead': {
    'display': 'none',
    'enable-kvm': ''
  },
  'rtc': {
    'rtc': 'base=localtime'
  },
  'cpu1': {
    'cpu': 'host,hv-time,kvm={},+topoext'
  },
  'cpu2': {
    'smp': '4,cores=4'
  },
  'memory': {
    'm': '8G'
  },
  'mobo35': {
    'M': 'q35'
  },
  'mobopc': {
    'M': 'pc'
  },
  'moboisa': {
    'm': '64M',
    'M': 'isapc',
  },
  'hostnet': {
    'netdev': 'tap,id=hostnet,ifname=tap1,script=no,downscript=no',
#    'net': 'nic,model=virtio,macaddr=52:54:ea:d6:1b:ae,netdev=hostnet'
    'net': 'nic,model=virtio,macaddr={},netdev=hostnet'
# ^^ virtio
  },
  'usernet1': {
    'netdev': 'user,id=usernet{}',
#    'net': 'nic,model=e1000,macaddr=52:54:ad:47:98:03,netdev=usernet'
    'net': 'nic,model=e1000,macaddr={},netdev=usernet'
  },
  'usernet2': {
    'netdev': 'user,id=usernet{}',
#    'net': 'nic,model=virtio,macaddr=52:54:ad:47:98:03,netdev=usernet'
    'net': 'nic,model=virtio,macaddr={},netdev=usernet'
## ^^ virtio
  },
  'usb1': {
    'usb': ''
  },
  'usb2': {
    'device': [
      'usb-ehci,id=ehci'#,
      #'usb-kbd,bus=usb-bus.0',
      #'usb-mouse,bus=usb-bus.0'
    ]
  },
  'usbdev': {
    'device': [ ]
  },
  'virtio': {
    'device': [
      'virtio-keyboard-pci',
      'virtio-mouse-pci'
    ]
  },
  'vga1': {
    'vga': 'std'
  },
  'vga2': {
    'vga': 'none'
  },
  'vga3': {
    'device': [
      'ioh3420,bus=pcie.0,addr=1c,multifunction=on,port=1,chassis=1,id=root.1',
      #'vfio-pci,host=07:00.0,bus=root.1,addr=00.0,multifunction=on,x-vga=on'
      'vfio-pci,host={},bus=root.1,addr=00.0,multifunction=on,x-vga=on'
    ]
  },
  'vgahack': {
    'device': 'isa-cirrus-vga'
  },
  'audio': {
    'device': [
      'ich9-intel-hda',
      'hda-micro'
    ],
    'audiodev': 'jack,id=audio1'
  },
  'drive': {
    'drive': [
    ]
  },
  'splash': {
    'boot': 'menu=on,splash=splash/boot.jpg,splash-time=5000'
  },
  'name': {
    'name': ''
  },
  'mirror': {
    'device': 'ivshmem-plain,memdev=lg_ivshmem',
    'object': 'memory-backend-file,id=lg_ivshmem,share=on,mem-path=/dev/shm/looking-glass,size=32M'
  },
  'scream': {
    'device': 'ivshmem-plain,memdev=sc_ivshmem',
    'object': 'memory-backend-file,id=sc_ivshmem,share=on,mem-path=/dev/shm/scream,size=2M'
  },
  'huge': {
    'object': 'memory-backend-file,id=mem,size={},mem-path=/hugetlbfs,share=on'
  },
  'spice': {
    'spice': 'addr=127.0.0.1,port=5900,disable-ticketing',
    'device': [
      'virtio-serial-pci',
      'virtserialport,chardev=spicechannel0,name=com.redhat.spice.0'
    ],
    'chardev': 'spicevmc,id=spicechannel0,name=vdagent'
  }
}

audio_cards = {
  'ich9': [ 'ich9-intel-hda', 'hda-micro,audiodev=audio1' ],
  'ich6': [ 'intel-hda', 'hda-micro,audiodev=audio1' ],
  'ac97': [ 'AC97' ],
  'crys': [ 'cs4231a' ],
  'eson': [ 'ES1370' ],
  'sb16': [ 'sb16' ],
  'usba': [ 'usb-audio,bus=usb-bus.0' ],
  'none': []  
}

qemu_drives = {
  'ide1': {
    'cdrom': 'ide',
    'disks': 'ide',
    'drive': [
      'if=ide,file=vm/{}/disk.img,media=disk'
    ]
  },
  'ide2': {
    'cdrom': 'ide',
    'disks': 'ide',
    'drive': [
      'if=ide,file=vm/{}/disk.img,media=disk',
      'if=virtio,file=img/temp.qcow2,media=disk'
    ]
  },
  'virtio': {
    'cdrom': 'ide',
    'disks': 'virtio',
    'drive': [
      'if=virtio,file=vm/{}/disk.img,media=disk'
    ]
  }
}

# note: the weird format is because we need to keep it in order
qemu_model = [
  ['archaic', {
    'parts': ['emu', 'cpu1', 'cpu2', 'memory', 'moboisa', 'vga1', 'drive',
              'splash', 'name', 'rtc' ],
    'drives': 'ide1',
    'desc': 'ISA-only system with no ethernet',
    'purpose': 'To run really ancient systems',
    'memory': '16M'
  }],
  ['basic', {
    'parts': ['emu', 'cpu1', 'cpu2', 'memory', 'mobopc', 'vga1', 'usernet1',
              'usb1', 'usb2', 'usbdev', 'drive', 'splash', 'name', 'rtc'],
    'drives': 'ide1',
    'desc': 'PCI-based system with 1G of ram and a PIIX chipset',
    'purpose': 'You should install your OS and get your virtio drivers '
      'ready for later systems.',
    'memory': '2G'
  }],
  ['simple', {
    'parts': ['emu', 'cpu1', 'cpu2', 'memory', 'mobopc', 'vga1', 'usernet1',
              'usb1', 'usb2', 'usbdev', 'drive', 'splash', 'name', 'rtc'],
    'drives': 'ide2',
    'desc': 'As above with a dummy virtio disk',
    'purpose': 'Teach your OS about virtio disks.',
    'memory': '2G'
  }],
  ['virtio', {
    'parts': ['emu', 'cpu1', 'cpu2', 'memory', 'mobo35', 'vga1', 'usernet2',
              'hostnet', 'usb1', 'usb2', 'usbdev', 'drive', 'splash', 'name',
              'rtc'],
    'drives': 'virtio',
    'desc': 'As above with a virtio host-only network and virtio disks',
    'purpose': 'Teach your OS about virtio network adapters and '
      'install synergy.\n Your shared folder is at \\\\192.168.101.2.',
    'pre': hostnet_up,
    'post': hostnet_down,
    'memory': '2G'
  }],
  ['modern', {
    'parts': ['emu', 'cpu1', 'cpu2', 'memory', 'mobo35', 'vga1', 'hostnet',
              'usernet2', 'usb1', 'usb2', 'usbdev', 'audio', 'drive',
              'splash', 'name', 'mirror', 'rtc'],
    'drives': 'virtio',
    'desc': 'q35/virtio system, 8G of ram, host-only networking, and audio',
    'purpose': 'Teach your system about the q35 architechture.\n'
      '		  Meanwhile, single-card users drown in remorse.',
    'pre': hostnet_up,
    'post': hostnet_down,
    'memory': '2G'
  }],
  ['complex', {
    'parts': ['emu', 'cpu1', 'cpu2', 'memory', 'mobo35', 'vga2', 'hostnet',
              'usernet2', 'usb1', 'usb2', 'usbdev', 'vgahack', 'vga3',
              'audio', 'drive', 'splash', 'name', 'mirror', 'scream', 'huge',
              'spice', 'virtio', 'rtc'],
    'drives': 'virtio',
    'desc': 'As above with pcie-passthrough',
    'purpose': 'Play some games and blurays from the comfort of X/Wayland\n'
               'Test out distros with realish hardware.',
    'pre': hostnet_up,
    'post': hostnet_down,
    'xrandr': True,
    'memory': '8G'
  }],
  ['nohead', {
    'parts': ['emu-nohead', 'cpu1', 'cpu2', 'memory', 'mobo35', 'vga2',
              'hostnet', 'usernet2', 'usb1', 'usb2', 'usbdev', 'vgahack',
              'vga3', 'audio', 'drive', 'splash', 'name', 'mirror', 'scream',
              'huge', 'spice', 'virtio', 'rtc'],
    'drives': 'virtio',
    'desc': 'As above but without a qemu window. You are on your own',
    'purpose': 'Enjoy your fully functional guest operating system.',
    'pre': hostnet_up,
    'post': hostnet_down,
    'xrandr': True,
    'memory': '8G'
  }]
]

qemu_model_drive = {}


    
def build_opts_single(opts):
  out = []
  for o in opts:
    out.append('-'+o);
  return out


def build_opts_multi(opts,fill=''):
  out = []
  for k,v in opts.items():
    if type(v) == str:
      if v:
        out.append('-{} {}'.format(k,v))
      else:
        out.append('-{}'.format(k))
    else:
      for u in v:
        out.append('-{} {}'.format(k,u.format(fill)))
  return out


def qemu_build(name):
  global qemu_model_drive
  model = qemu_model_drive['model']
  out = []
  for part in model['parts']:
    out.extend(build_opts_multi(qemu_parts[part]))
  return out

def check_for_model(make):
  global qemu_model_drive
  qemu_model_dict = dict((k,v) for k,v in qemu_model)
  if make in qemu_model_dict:
    model = qemu_model_dict[make]
    qemu_model_drive = qemu_drives[model['drives']]
    qemu_model_drive['model'] = model
  else:
    print('We don\'t make that build :(')
    exit(1)

def print_usage():
    usage=[
      'No build and name specified.',
      '',
      f'Usage:	sudo -E {sys.argv[0]} VMNAME MODEL [OPTIONS]',
      '',
      'VMNAME	The directory name where the disk.img is',
      '',
      'MODEL	What sort of devices the vm will see.  Models available are:'
    ]
    for make,model in qemu_model:
      usage.append('\t{}\t  {}'.format(make, model['desc']))
    usage+=[
      '	You will step through these systems, typically from basic to modern.',
      '	(going backwards may harm your system, and is not recommended.)',
      '	Members of the multi-gpu master race can proceed on to nohead.',
      '	Linux vms can start at modern or complex.',
      '',
      'OPTIONS	Further options tweaking the layout of the system.',
      '	cpu:smt   Use two threads per core',
      '	vga:hack  Add a dummy isa vga to kickstart some pcie cards',
      '	smb:none  Do not share any folder over the network',
      '	user:none Do not provide a internet-visible network adapter',
      '	host:none Do not provide any host-only networks',
      '	mirror    Add 32M of shared memory for project looking glass',
      '	spice     Open a spice connection at localhost:5900 (nohead, complex)',
      '	spice:xx  Open a spice unix socket at file xx (nohead, complex)',
      '	m:ram     Set the amount of ram given to the OS (e.g. m:32G)',
      '	cd:img    mount image from the _img directory as a cdrom',
      '	dd:img    mount image from the _img directory as a disk',
      '	cdv:img   mount image from the vm directory as a cdrom',
      '	ddv:img   mount image from the vm directory as a disk',
      '	cdg:img   mount image from the filesystem as a cdrom',
      '	ddg:img   mount image from the filesystem as a disk',
      '	usb1:x:y  pass usbdevice xxxx:yyyy where available as usb1',
      '	usb2:x:y  pass usbdevice xxxx:yyyy where available as usb2',
      '	c:cores   Set the number of emulated cores',
      '	barf      Your vm barfs at acpi tables',
      '',
      'Examples:',
      '\t' + sys.argv[0] + ' archaic dos',
      '\t' + sys.argv[0] + ' virtio winxp barf',
      '\t' + sys.argv[0] + ' modern win7 vga:hack cpu:smt c:2',
      '\t' + sys.argv[0] + ' complex win7 games',
      '\t' + sys.argv[0] + ' nohead coinminer',
      ''
    ]
    print('\n'.join(usage))

## TODO: Every arg in this function should come from a conf file
# rather than cmdline args
def process_args(guest, args):
  global smb
  global mirror
  global scream
  global spice
  # check for too few arguments
  if not args or len(args) < 1:
    print_usage()
    exit(1)

  # parse first two options
  vm_model = args[0]
  vm_name = guest

  check_for_model(vm_model)

  # parse extra options if any -- these effect parsing of first
  isos = []
  imgs = []
  usbs1 = []
  usbs2 = []
  vgahack = 0
  cores = 4
  smt = 0
  kvm = 'off'
  smb = True
  sound = 'ich9'
  huge = False
  spice = False
  mirror = False
  memory = qemu_model_drive['model']['memory']
  for arg in args[1:]:
    head,sep,tail = arg.partition(':')
    if tail:
      if arg == 'vga:hack':
        vgahack = 1
      elif arg == 'cpu:smt':
        smt = 1
      elif arg == 'smb:none':
        smb = False
      elif arg == 'user:none':
        qemu_parts['usernet1'] = {}
        qemu_parts['usernet2'] = {}
      elif arg == 'host:none':
        qemu_parts['hostnet'] = {}
        nohost = True
        smb = False
      elif head == 'snd' and tail in audio_cards:
        sound = tail
      elif head == 'kvm':
        kvm = tail
      elif head == 'm':
        memory = tail
      elif head == 'cd':
        isos.append('img/'+tail)
      elif head == 'dd':
        imgs.append('img/'+tail)
      elif head == 'cdv':
        isos.append('vm/{}/{}'.format(vm_name,tail))
      elif head == 'ddv':
        imgs.append('vm/{}/{}'.format(vm_name,tail))
      elif head == 'cdg':
        isos.append(tail)
      elif head == 'ddg':
        imgs.append(tail)
      elif head == 'usb1':
        usbs1.append(tail)
      elif head == 'usb2':
        usbs2.append(tail)
      elif head == 'c':
        cores = int(tail)
      elif head == 'spice':
        spice = True
        qemu_parts['spice']['spice'] = 'unix,addr={},disable-ticketing'.format(tail)
        Popen(['touch', tail]).wait()
        Popen(['chmod', '777', tail]).wait()
    elif arg == 'barf':
      qemu_parts['emu']['no-acpi'] = ''
    elif arg == 'mirror':
      mirror = True
    elif arg == 'scream':
      scream = True
    elif arg == 'huge':
      huge = True
    elif arg == 'spice':
      spice = True
  if not vgahack:
    qemu_parts['vgahack'] = {}
  if not mirror:
    qemu_parts['mirror'] = {}
  else:
    Popen(['touch', '/dev/shm/looking-glass']).wait()
    Popen(['chmod', '777', '/dev/shm/looking-glass']).wait()
  if not scream:
    qemu_parts['scream'] = {}
  else:
    Popen(['touch', '/dev/shm/scream']).wait()
  if not spice:
    qemu_parts['spice'] = {}
  if not smt:
    qemu_parts['cpu2']['smp'] = 'cores={}'.format(cores)
  else:
    qemu_parts['cpu2']['smp'] = 'cores={},threads=2'.format(cores)
  if not huge:
    qemu_parts['huge'] = {}
  else:
    qemu_parts['huge']['object'] = qemu_parts['huge']['object'].format(memory)
  qemu_parts['audio']['device'] = audio_cards[sound]
  qemu_parts['memory']['m'] = memory
  qemu_parts['cpu1']['cpu'] = qemu_parts['cpu1']['cpu'].format(kvm)
  smbpath = os.path.realpath('./share')
  smbtext = ',smb={}'.format(smbpath) if smb else ''
  qemu_parts['usernet1']['netdev'] = \
    qemu_parts['usernet1']['netdev'].format(smbtext)
  qemu_parts['usernet2']['netdev'] = \
    qemu_parts['usernet2']['netdev'].format(smbtext)
  
  # build a list of drives for the vm
  drives = qemu_model_drive['drive']
  drives[0] = drives[0].format(vm_name)
  disk_mode = qemu_model_drive['disks']
  cdrom_mode = qemu_model_drive['cdrom']
  for img in imgs:
    if img:
      drives.append('if={},file={},media=disk'.
                    format(disk_mode,img))
  for iso in isos:
    if iso:
      drives.append('if={},file={},media=cdrom'.
                    format(cdrom_mode,iso))

  # build a list usbdevices for the vm
  usbdevices = []
  for usb in usbs1:
    if usb:
      usbdevices.append('usb-host,vendorid=0x{},productid=0x{},bus=usb-bus.0'.format(usb[0:4],usb[5:9]))
  for usb in usbs2:
    if usb:
      usbdevices.append('usb-host,vendorid=0x{},productid=0x{},bus=ehci.0'.format(usb[0:4],usb[5:9]))
  
  # add accumulated option detail to the parts list
  qemu_parts['drive']['drive'] = drives
  qemu_parts['usbdev']['device'] = usbdevices
  qemu_parts['name']['name'] = vm_name

  # return a freshly baked parameter list
  return qemu_build(vm_name)


def wire_config_into_parts(guest):
  global guest_conf
  global host_conf
  guest_conf = conf.read_guest_conf(guest)
  host_conf = conf.read_host_conf()
  qemu_parts['hostnet']['net'] = \
    qemu_parts['hostnet']['net'].format(guest_conf['mac']['hostnet'])
  qemu_parts['usernet1']['net'] = \
    qemu_parts['usernet1']['net'].format(guest_conf['mac']['usernet'])
  qemu_parts['usernet2']['net'] = \
    qemu_parts['usernet2']['net'].format(guest_conf['mac']['usernet'])
  qemu_parts['vga3']['device'][1] = \
    qemu_parts['vga3']['device'][1].format(host_conf['pci']['vga']) 

# ====================== #
# == MAIN ENTRY POINT == #
# ====================== #

# TODO:
# - convert cmdline params to guest config
# - better integration with caller script

def do_launch(guest, args):
  global mirror
  global spice

  # check for boot splash -- remove detail entry in parts list if not there
  if not os.path.exists('splash/boot.jpg'):
    qemu_parts['boot'] = {}

  if guest:
    wire_config_into_parts(guest)

  # build desired model details
  qemu_args = process_args(guest, args)
  model = qemu_model_drive['model']

  # setup environment vars
  my_env = os.environ
  if 'DISPLAY' not in my_env:
    my_env['DISPLAY'] = ':0'	# spoof running X in case we're in a tty
  if 'QEMU_AUDIO_DRV' not in my_env:
    my_env['QEMU_AUDIO_DRV'] = 'pa'
  if 'QEMU_PA_SERVER' not in my_env:
    my_env['QEMU_PA_SERVER'] = '/run/user/1000/pulse/native'

  # perform pre scripts
  if 'pre' in model:
    model['pre']()

  # turn off the display we're not using -- I've looked at XLib.ext.randr and 
  # it seems very verbose to do it in python code.
  if 'xrandr' in model:
    xrandr_opts = \
      [item for sublist in \
        [['--output', output['output'], '--off'] for output in \
        guest_conf['xrandr']] \
      for item in sublist]
    if xrandr_opts:
      Popen(['xrandr'] + xrandr_opts, env=my_env)

  # mount shared folders
  if smb and 'smb' in host_conf:
    mounting.perform(host_conf['smb'])

  # run the vm
  qemu_binary = 'qemu-system-x86_64'
  qemu_command = ' '.join([qemu_binary] + qemu_args).split()
  print('Launching:\n\t' + qemu_binary + ' \\\n\t  ' + \
        ' \\\n\t  '.join(qemu_args) + '\n')
  vm = Popen(['sudo', '-E'] + qemu_command, env=my_env)
  print('FOR WHAT PURPOSE: ' + model['purpose'])
  lg = None
  sip = None
  if mirror or scream:
    sleep(2)
  if mirror:
    args = ['sudo', '-E', '-u', '#1000', 'looking-glass-client', 'win:autoResize=yes', 'opengl:amdPinnedMem=no', 'win:borderless=yes', 'win:position=0x0', 'input:escapeKey=72']
    if spice:
      Popen(['chmod', '777', '/tmp/looking-glass.socket']).wait()
      args.extend(['spice:port=0', 'spice:host=/tmp/looking-glass.socket'])
    else:
      args.append('spice:enable=no')
    lg = Popen(args)
  if scream:
    args = ['sudo', '-E', '-u', '#1000', 'scream', '-m', '/dev/shm/scream']
    sip = Popen(args)
  vm.wait()

  # perform post scripts
  if 'post' in model:
    model['post']()

  # clean up shared folders
  if smb and 'smb' in host_conf:
    mounting.clean()
    
  # turn the display(s) back on
  if 'xrandr' in model:
    xrandr_opts = \
      [item for sublist in \
        [['--output', output['output'], '--auto']+output['location'] \
        for output in guest_conf['xrandr']] \
      for item in sublist]
    if xrandr_opts:
      Popen(['xrandr'] + xrandr_opts, env=my_env).wait()

  Popen(['kdialog', '--msgbox', f'Virtual machine {guest} has shutdown.'], env=my_env).wait()
