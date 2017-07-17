#!/usr/bin/env python2
# arch.py - Architecture-specific functions for dealing with conf files
# Licensed under GPLv2.

## EXAMPLES:
#inline_parm_add('/etc/default/grub', 'GRUB_CMDLINE_LINUX', ['pci-stub', 'dummy'])
#inline_key_value_add('/etc/default/grub', 'GRUB_CMDLINE_LINUX_DEFAULT', {'pci-stub.ids': ['0000:0000']})
#inline_key_value_add('/etc/default/grub', 'GRUB_CMDLINE_LINUX_DEFAULT', {'pci-stub.ids': None})
#
# you need to run arch.detect() first

from collections import OrderedDict
from subprocess import call


str_unknown = 'Unknown architecture!  Not updating configuration.'


arches = {
  'arch': {
    'modules': {
      'loc': '/etc/mkinitcpio.conf',
      'var': 'MODULES',
      'cmd': ['sudo', 'mkinitcpio', '-p', 'linux']
      },
    'grub': {
      'loc': '/etc/default/grub',
      'var': 'GRUB_CMDLINE_LINUX_DEFAULT',
      'cmd': ['sudo', 'grub-mkconfig', '-o', '/boot/grub/grub.cfg']
    }
  },
  'fedora': {
    'modules': {
      'loc':  '/etc/dracut.conf.d/pci-stub',
      'cmd': ['sudo', 'dracut', '--force']
    },
    'grub': {
      'loc': '/etc/default/grub',
      'var': 'GRUB_CMDLINE_LINUX_DEFAULT',
      'cmd': ['sudo', 'grub2-mkconfig', '-o', '/boot/grub2/grub.cfg']
    }
  },
  'debian': {
    'modules': {
      'loc':  '/etc/initramfs-tools/modules',
      'cmd': ['sudo', 'update-initramfs', '-u', '-k', 'all']
    },
    'grub': {
      'loc': '/etc/default/grub',
      'var': 'GRUB_CMDLINE_LINUX_DEFAULT',
      'cmd': ['sudo', 'update-grub']
    }
  }   
}

arch = {}


def read_conf_keys(fname):
  w = OrderedDict()
  with open(fname, 'r') as f:
    z = f.read().split('\n')
  for y in z:
    x = y.split('=',1)
    if x and x[0]:
      w[x[0]] = x[1]
  return w


def detect():
  global arch
  conf = read_conf_keys('/etc/os-release')
  keys_to_try = ['ID', 'ID_LIKE']
  arches['neon'] = arches['debian']
  for key in keys_to_try:
    if key in conf:
      release = conf[key]
      if arches.has_key(release):
	arch = arches[release]
	return release
  return {}


def inline_add(fname, parms):
  call(['touch', fname])
  with open(fname, 'r') as f:
    config = f.read().split('\n')
  c = OrderedDict().fromkeys(config)
  if type(parms) is not list:
    parms = [parms]
  for i in parms:
    c[i] = True
  out = '\n'.join([i for i in c.keys()])
  with open(fname, 'w') as f:
    f.write(out)


# add keys and/or values to a cmdline list of options already
# stored somewhere in conf file.  Preserves comments.
# key_values = some sort of dict
# e.g. { 'pci-stubs.ids'=['0012:3456', '1234:45678'], 'debug'=''}
# will add "pci-stubs.ids=0012:3456,1234:45678 debug" to the list
def inline_key_value_add(fname, var, key_values):
  with open(fname, 'r') as f:
    config = f.read().split('\n')
  out = []
  for c in config:
    if c.startswith(var+'='):
      d = c.replace('\"','').split('=',1)
      d = d[1].split(' ') if d[1] else []
      d = [i.split('=') if i.count('=') else [i,None] for i in d]
      d = OrderedDict(d)
      for key,values in key_values.items():
	e = d[key] if key in d else ''
	if not values:
	  d[key] = values
	else:
	  if type(values) is not list:
	    values = [values]
	  e = e.split(',') + values
	  d[key] = ','.join([i for i in set(e)])
      d = ' '.join(['{}={}'.format(k,v) if v else k for k,v in d.items()])
      out.append('{}=\"{}\"'.format(var, d))
    else:
      out.append(c)
  with open(fname, 'w') as f:
    f.write('\n'.join(out))  


# add parms to a configuration variable
# merges them into existing ones there
def inline_parm_add(fname, var, parms):
  inline_key_value_add(fname, var, OrderedDict.fromkeys(parms,None))


def install_module_initramfs(modules):
  if not arch:
    print str_unknown
    return None
  mod_info = arch['modules']
  if 'var' in mod_info:
    inline_parm_add(mod_info['loc'], mod_info['var'], modules)
  else:
    inline_add(mod_info['loc'], modules)
  return mod_info['loc']

def install_module_note(module, note):
  fname = ''.join(['/etc/modprobe.d/', module, '.conf'])
  inline_add(fname, note)
  return fname

def update_initramfs():
  call(arch['modules']['cmd'])


def install_grub_options(options):
  if not arch:
    print str_unknown
    return None
  grub_info = arch['grub']
  inline_key_value_add(grub_info['loc'], grub_info['var'], options)
  call(grub_info['cmd'])
  return grub_info['loc']


