#!/usr/bin/env python3
import sys
from scripts import create

str_usage = f'Usage:\t{sys.argv[0]} VMNAME [OPTIONS]\n\
Create a virtual machine called VMNAME and initialize its\n\
configuration.'

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print(str_usage)
    exit(1)
  create.create(sys.argv[1]) 

