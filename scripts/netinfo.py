#!/usr/bin/python
from subprocess import Popen, call, PIPE
import os, socket, struct


def bridge_up(phys):
  #addr="192.168.1.50/24"
  #gw="192.168.1.1"

  #echo "remove ip from eth0"
  #sudo ip addr del $addr dev eth0
  #sudo ip link set eth0 up

  #echo "create br0"
  #sudo brctl addbr br0
  #echo "add eth0 to br0"
  #sudo brctl addif br0 eth0

  #echo "bring up br0"
  #sudo ip addr add $addr dev br0
  #sudo ip link set br0 up

  #echo "set default gateway"
  #sudo ip route add default via $gw dev br0
  return

def get_gateways_for_device(phys):
  gw = []
  with open('/proc/net/route') as f:
    for line in f:
      fields = line.strip().split()
      if fields[0] == phys:
	gw.append(socket.inet_ntoa(struct.pack('<L', int(fields[2], 16))))
  return gw


def get_arps_from_device(phys, gws):
  arps = []
  with open('/proc/net/arp') as f:
    for line in f:
      fields = line.strip().split()
      if fields[-1] == phys and fields[0] in gws:
	arps.append(fields[0])
  return arps

def phys_gw():
  p1 = Popen(['find', '/sys/devices/pci0000:00', '-name', 'net'],
	     stdout=PIPE)
  netdevs = p1.communicate()[0]
  devs = [name for d in netdevs.splitlines() for name in os.listdir(d)]
  if len(devs) == 0:
    return None, None
  for phys in devs:
    gws = get_gateways_for_device(phys)
    if not gws:
      continue
    arps = get_arps_from_device(phys, gws)
    return phys, arps[0]
  return devs[0], None

def phys_addr_bcast_gw():
  phys, gw = phys_gw()
  addr = mask = bcast = None
  if phys:
    p1 = Popen(['ip', 'addr', 'show', phys], stdout=PIPE)
    detail = p1.communicate()[0].splitlines()
    if 'UP' in detail[0].split():
      netdetails = detail[2].split()
      addr_mask = netdetails[1].split('/')
      addr = addr_mask[0]
      mask =  socket.inet_ntoa(struct.pack('>L', (1<<32) - (1<<32>>int(addr_mask[1]))))
      bcast = netdetails[3]
  return phys, addr, mask, bcast, gw