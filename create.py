#!/usr/bin/env python2
import sys
from scripts import create

str_usage = 'Usage:	' + sys.argv[0] + ' VMNAME [OPTIONS]' + \
  '''
Create a virtual machine called VMNAME and initialize its
configuration.
  '''

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print str_usage
    exit(1)
  create.create(sys.argv[1]) 

