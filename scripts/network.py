#!/usr/bin/python
from random import randint


def gen_mac():
  return '52:54:{}:{}:{}:{}'.format(
    format(randint(0,255),'02X'),
    format(randint(0,255),'02X'),
    format(randint(0,255),'02X'),
    format(randint(0,255),'02X'))