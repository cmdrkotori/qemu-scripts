#!/usr/bin/env python3
import os
import platform
import configparser
from subprocess import Popen, call,PIPE
from collections import OrderedDict
from . import arch, netinfo, network, conf


str_description = '''
This program will now attempt to prepare your system for running
virtual machines.  Depending upon your hardware, you may run a
virtual machine from a desktop window and/or even a seperate
monitor with pcie passthrough of a secondary gpu.

Parts of this program will need superuser privileges, so you
should set up your sudoers file accordingly.  Later on,
superuser privileges will be needed for certain qemu features to
work correctly, such as usb-passthrough and tolerable audio
emulation.
'''

str_samba = '''
Creating sample smb.conf for host-only network sharing.
Virtual access to the share will be have the same access
privileges and ownership rights of the user running this
script.
'''

str_detected_user = '''\
The detected current user is {}.
If this is not what you want, edit _conf/_smb.conf\
'''

str_smb_conf ='''\
[global]
	hosts allow = 192.168.101.
	wins support = yes
	netbios name = {0}
	server role = standalone server
	interfaces = tap0
	bind interfaces only = yes
	socket options = TCP_NODELAY IPTOS_LOWDELAY \
SO_RCVBUF=65536 SO_SNDBUF=65536
	strict sync = no
	sync always = no
	#workgroup = WORKGROUP
	passdb backend = smbpasswd
	map to guest = Bad password
	null passwords = yes
        unix extensions = no

[qemu]
	comment = Shared Directories
	path = {1}
	force user = {2}
	force group = {2}
	read only = No
	guest only = Yes
	writeable = yes
	follow symlinks = yes
	wide links = yes
'''

str_passthrough = '''
To successfully passthrough a pcicard, the kernel command line
needs to be modified, a script called vfio-bind needs to be
installed into /usr/bin, and a upstart/systemd script needs to
be installed at /etc/init.  This requires superuser access and
will modify your system.
'''

str_vga = '''
I will now attempt to detect a secondary gpu.  If found, you can
pass it through to your guest OS for near-native graphics
performance.  Dual-monitor setups are recommended for this, but
not required.
'''

str_nopass = '''\
PCI passthrough will not be implemented at this time.  You may
still run a vm inside a window, however.
'''
str_novga = '''\
No device selected, so no vga device will be set up.
Skipping system modification.
'''

str_arch = '''\
Only Debian-based systems are supported at
present.  Please consider submitting a git pull request to
properly support your distro.
'''

str_vfio_bind = '''\
#!/bin/bash

modprobe vfio-pci

for dev in "$@"; do
        vendor=$(cat /sys/bus/pci/devices/$dev/vendor)
        device=$(cat /sys/bus/pci/devices/$dev/device)
        if [ -e /sys/bus/pci/devices/$dev/driver ]; then
                echo $dev > /sys/bus/pci/devices/$dev/driver/unbind
        fi
        echo $vendor $device > /sys/bus/pci/drivers/vfio-pci/new_id
done
'''

vfio_bind_location = '/usr/bin/vfio-bind'


str_script_upstart = '''\
# vfio-pci - bind cetain pci devices to vfio-pci

description "pci to vfio autobinder"

start on runlevel [2345]

task

script
    ''' + vfio_bind_location + ''' {}
end script
'''

str_script_systemd = '''\
[Unit]
Description=Binds devices to vfio-pci
After=syslog.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=-''' + vfio_bind_location + ''' {}

[Install]
WantedBy=multi-user.target
'''

#TODO: Add a sysv-script.  Not written, soon to be deprecated in
#favor of the systemd botnet anyway.
str_script_unknown = '''\
'''

str_script_unknown_warning1 = '''\
Unknown init system!  Resorting to old-style script.  Proceeding
will install a sysv-style init script to /etc/init.d/vfio-pci.
'''

str_script_unknown_warning2 = '''\
Old-style rc script installed directly into init.d directory!
You should inspect the script to make sure it fits your distro,
and delete it if you are not sure.
'''

## OTHER STUFF
init_systems = [
  ['upstart', {
    'stanza': 'upstart',
    'description': 'Upstart init system.',
    'script': str_script_upstart,
    'location': '/etc/init/vfio-pci.conf'
      }],
  ['systemd', {
    'stanza': 'systemd',
    'description': 'Systemd init system',
    'script': str_script_systemd,
    'location': '/usr/lib/systemd/system/vfio-pci.service',
    'postinstall': ['systemctl', 'enable', 'vfio-pci']
      }],
  ['unknown', {
    'stanza': 'unknown',
    'description': 'Unknown init system.',
    'script': str_script_unknown,
    'location': '/etc/init.d/vfio-pci',
    'warning1': str_script_unknown_warning1,
    'warning2': str_script_unknown_warning2
      }]
  ]

str_modules = '''
About to install modules into your init system image.  This
script only does something if your system is arch, debian, or
fedora-based.  If your distro is not supported, you will need to
add 'pci-stub' to your initram image yourself.  If this section
excutes quickly, that's probably why.
'''

str_grub = '''
About to configure the linux command-line.  This will add
\t{}
to your linux command-line by auto-editing the line containing
GRUB_CMDLINE_LINUX in your grub config file.  Existing options
will be preserved.  Again, this script only knows about arch,
debian, and fedora-based systems.  If you are using a different
bootloader, please indicate that you will add this stanza to the
commandline yourself.  NOTE: IF YOU SWAP YOUR VIDEO CARDS, YOU
SHOULD BOOT WITHOUT THIS STANZA BY SELECTING THE RECOVERY OPTION
INSTEAD.
'''

str_network= '''
Storing network device and host configuration.  NOTE: If your
address changes upon reboot (e.g. DHCP), you will need to rerun
this script every time.  To avoid this, ask your local network
administrator for a static IP.
'''

files_modified = []


## HELPER FUNCTIONS

def proceed():
  x = input('Do you want to proceed? (y/n): ')
  print('')
  return x == 'y'


# Find where in sysfs a certain device is
def where_in_sysfs(pci_id):
  p1 = Popen(['find', '/sys/devices', '-name', '0000:' + pci_id],
	     stdout = PIPE)
  return p1.communicate()[0].decode('utf-8')


# Find the pcidev locations of all devices used by pci_id, up to
# but excluding the root device.
def find_pci_id_tree(pci_id):
  out = where_in_sysfs(pci_id)
  if len(out):
    out = out.splitlines()[0].split('/')
    del out[0:out.index('pci0000:00')+1]
  return out


# Find all devices related to a vga card, including its bridge.
# Sometimes vga cards come with subsidiary devices.  We can't
# only look for the vga device tree, we need to include audio
# controllers and such too. So what we do is iterate over the
# last number until we get nothing more.
# Returns:
#	tree	pci devices in the tree
#	pci_stub_devices	pci-stub eligible devices
def pci_id_to_cards(pci_id):
  pci_bits = pci_id.split('.')
  vfio_devices = []
  index = 0
  pci_stub_devices = []
  while True:
    pci = '{}.{}'.format(pci_bits[0], index)
    devices = find_pci_id_tree(pci)
    if len(devices) == 0:
      break
    vfio_devices.append(devices[-1])
    pci_stub_devices.append(pci)
    index += 1
  tree = list(OrderedDict.fromkeys(vfio_devices))
  return tree, pci_stub_devices


# Convert pci devices into pci-stub.ids
def pci_device_to_stubs(pci_devices):
  out = []
  for device in pci_devices:
    device_dir = where_in_sysfs(device).splitlines()[0]
    with open('{}/vendor'.format(device_dir)) as f:
      device_vendor = f.readline()
    with open('{}/device'.format(device_dir)) as f:
      device_device = f.readline()
    out.append('{}:{}'.format(format(int(device_vendor, 16), '04x'),
			      format(int(device_device, 16), '04x')))
  return out


# look for certain processes with a 'stanza' in the process tree  
def look_for_procs(stanza):
  p1 = Popen(['ps', '-A'], stdout=PIPE)
  p2 = Popen(['grep', stanza], stdin=p1.stdout, stdout=PIPE)
  procs = p2.communicate()[0].decode('utf-8').splitlines()
  return len(procs) > 0


## PROGRAM FLOW FUNCTIONS

def print_description():
  print(str_description)

def chown_user(fname):
  username = detect_username()
  call(['chown', '{}:{}'.format(username,username), fname])

def create_dirs(dirs):
  print('Creating directories...')
  username = detect_username()
  for d in dirs:
    if not os.path.exists(d):
      print('Creating {}'.format(d))
      call(['mkdir', d])
      chown_user(d)
  print('Directories are created.\n')

def detect_username():
  try:
    username = os.environ['SUDO_USER']
  except:
    username = os.environ['USER']
  return username

def setup_samba():
  print(str_samba)
  username = detect_username()
  print(str_detected_user.format(username))
  
  conf = str_smb_conf.format('qemuhost', os.path.realpath('share'), username)
  
  if not os.path.exists('conf'):
    call(['mkdir', 'conf'])
    call(['chown', username+':'+username, 'conf'])
  with open('conf/smb.conf', 'w') as f:
    f.write(conf)
    chown_user('conf/smb.conf')
  print('Host-only samba configuration written.\n')


def print_passthrough_warning():
  print(str_passthrough)

  
def select_vga():
  print(str_vga)
  p1 = Popen('lspci', stdout=PIPE)
  p2 = Popen(['grep', 'VGA'], stdin=p1.stdout, stdout=PIPE)
  vgas = p2.communicate()[0].decode('utf-8').splitlines()
  print(vgas)
  if len(vgas) <= 1:
    print('WARNING: You do not seem to have a secondary vga adapter.')
  else:
    print(f'Your 2nd GPU appears to be at {vgas[-1].split(" ")[0]}')
  print('Select your secondary vga adapter.\n'\
    '0) None')
  i = 1
  for vga in vgas:
    print('{}) {}'.format(i,vga))
    i = i + 1
  try:
    device = int(input('Enter choice: '))
    print('')
    if device <= 0:
      raise Exception()
    pci_id = vgas[device-1].split()[0]
  except:
    print(str_novga)
    return None
  return pci_id


# guess the init system in use
def detect_init_system():
  for sys in init_systems:
    if look_for_procs(sys[1]['stanza']):
      return sys
  return sys


# install the init script, from detecting init to writing the service
def install_vfio_bind_service(pci_cards):
  print('')
  init_system = detect_init_system()
  if 'warning1' in init_system[1]:
    print(init_system[1]['warning1'])
    if not proceed():
      print('Not proceeding further.  Cleaning up.')
      call(['rm', vfio_bind_location])
      exit(0)
  else:
    print('Detected init system {}.'.format(init_system[0]))

  print('Vfio-devices: {}'.format(' '.join(pci_cards)))
  d = os.path.dirname(init_system[1]['location'])
  if not os.path.exists(d):
      os.makedirs(d)
  with open(init_system[1]['location'], 'w') as f:
    f.write(init_system[1]['script'].format(' '.join(pci_cards)))
  files_modified.append(init_system[1]['location'])
  if 'postinstall' in init_system[1]:
      call(init_system[1]['postinstall'])
  print('Init service written.  To add/remove devices, edit:\n'\
    '\t{}.'.format(init_system[1]['location']))
  if 'warning2' in init_system[1]:
    print(init_system[1]['warning2'])


def install_vfio_bind_script():
  with open(vfio_bind_location, 'w') as f:
    f.write(str_vfio_bind)
  call(['sudo', 'chmod', 'u+x', vfio_bind_location])
  files_modified.append(vfio_bind_location)
  print('Vfio-bind script written.\n')


def install_modules():
  print(str_modules)
  files_modified.append(arch.install_module_initramfs(['pci-stub']))
  files_modified.append(arch.install_module_note('drm', 'softdep drm pre: pci-stub'))
  arch.update_initramfs()

def install_grub(pci_stub_ids):
  psi = 'pci-stub.ids'
  stanza = '{}={}'.format(psi, ','.join(pci_stub_ids))
  print(str_grub.format(stanza))
  if not proceed():
    return
  files_modified.append(arch.install_grub_options({ psi: pci_stub_ids }))
  print('\nGrub config written.\n')
  

def write_host_conf(pci_stub_devices = None):
  print(str_network)
  phys, addr, mask, bcast, gw = netinfo.phys_addr_bcast_gw()
  cfg = conf.read_host_conf(False)
  cfg['net'] = { 'phys': phys, 'addr': addr, 'mask': mask, 'bcast': bcast,
    'gw': gw }
  # if pci_stub_devices is None, it probably means we're in the init me
  if pci_stub_devices:
    cfg['pci'] = { 'dev': ' '.join(pci_stub_devices),
		   'vga': pci_stub_devices[0] }
  # Some elementary shares
  cfg['smb'] = { "Documents": "~/Documents", "Downloads": "~/Downloads",
        "Pictures": "~/Pictures", "Music": "~/Music", "Videos": "~/Videos" }
  files_modified.append(conf.write_host_conf(cfg))


def print_files_modified():
  print('\nFiles modified:')
  for i in files_modified:
    print('\t{}'.format(i))


def do_init():
  arch.detect()
  print_description()
  if not proceed():
    return
  create_dirs(['conf', 'vm', 'share'])
  setup_samba()
  print_passthrough_warning()
  if not proceed():
    pci_stub_devices = None
    print(str_nopass)
  else:
    pci_id = select_vga()
    if pci_id:
      pci_cards, pci_stub_devices = pci_id_to_cards(pci_id)
      if len(pci_cards) == 0:
        print('A fatal loss of information has occurred. (Did '\
              'sysfs change?)')
        exit(1)
      install_vfio_bind_service(pci_cards)
      install_vfio_bind_script()
      install_modules()
      install_grub(pci_device_to_stubs(pci_stub_devices))
  write_host_conf(pci_stub_devices)
  print_files_modified()
  if pci_stub_devices:
    print('\n\nYou should reboot your system for the changes to '\
          'take effect.\n')
      
if __name__ == '__main__':
  do_init();

