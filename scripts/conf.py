#!/usr/bin/python
import json, os

fn_host_conf = 'conf/host.json'
fn_guest_conf = 'conf/vm_{}.json'
fn_conf_dir = 'conf'

def get_conf(fname, write_error = True):
  try:
    with open(fname, 'r') as jsonfile:
      return json.load(jsonfile)
  except:
    if write_error:
      print('Unable to read {}!'.format(fname))
      print('Perhaps there is a syntax or permissions issue.')
    return {}

def set_conf(fname, opts):
  if not os.path.exists(fn_conf_dir):
    os.makedirs(fn_conf_dir)
  try:
    with open(fname, 'w') as jsonfile:
        json.dump(opts, jsonfile, indent=4, sort_keys=True)
    return fname
  except:
    print('Could not write to {}! Perhaps there is a permissions problem.'.
          format(fname))
    return None

def read_host_conf(write_error = True):
  return get_conf(fn_host_conf, write_error)

def write_host_conf(opts):
  return set_conf(fn_host_conf, opts)

def read_guest_conf(vmname, write_error = True):
  return get_conf(fn_guest_conf.format(vmname), write_error)

def write_guest_conf(vmname, opts):
  return set_conf(fn_guest_conf.format(vmname), opts)

if __name__=='__main__':
  #print read_host_conf()
  #print json.dumps(read_host_conf(), indent=4, sort_keys=True)
  print json.dumps(read_guest_conf('win7'), indent=4, sort_keys=True)