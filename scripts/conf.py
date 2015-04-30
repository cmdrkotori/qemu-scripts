#!/usr/bin/python
import json, os

fn_host_conf = 'conf/host.json'
fn_guest_conf = 'conf/vm_{}.json'
fn_conf_dir = 'conf'

def get_conf(fname):
  try:
    with open(fname, 'r') as jsonfile:
      return json.load(jsonfile)
  except:
    print('Unable to read {}!'.format(fname))
    return {}

def set_conf(fname, opts):
  if not os.path.exists(fn_conf_dir):
    os.makedirs(fn_conf_dir)
  with open(fname, 'w') as jsonfile:
    json.dump(opts, jsonfile, indent=4, sort_keys=True)

def read_host_conf():
  return get_conf(fn_host_conf)

def write_host_conf(opts):
  set_conf(fn_host_conf, opts)

def read_guest_conf(vmname):
  return get_conf(fn_guest_conf.format(vmname))

def write_guest_conf(vmname, opts):
  set_conf(fn_guest_conf.format(vmname), opts)

if __name__=='__main__':
  #print read_host_conf()
  #print json.dumps(read_host_conf(), indent=4, sort_keys=True)
  print json.dumps(read_guest_conf('win7'), indent=4, sort_keys=True)