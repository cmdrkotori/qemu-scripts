import os, sys
from subprocess import Popen, call, PIPE
import conf, network

str_enter_size = '''
Enter the size of your virtual machine.  The disk image is
created in the qcow2 format, which has the advantage of
expanding to accomodate the actual data written.  You need to
include the units as well.  T = terabytes, G = gigabytes, and
M = megabytes.  For example, '200G' specifies an image with a
capacity of 200 gigabytes.
'''

str_xrandr_set = '''
I will now attempt to detect your connected monitors so you can
switch one or more off if you want to while the vm is running.
If you don't want to turn any off, don't select anything.
'''

str_xrandr_select = '''
Select an output to turn off.  I will place an asterisk beside
each output you select.  When satisfied, select Done.
'''

str_xrandr_done = '''\n
You have selected to turn off the following inputs while the vm
is running:

    {}

I'll save those to the config file, but you still need to tell
me where to place them when I'm done.  Please edit each location
field with an appropriate xrandr placement stanza, like this:

            "location": ["--left-of", "DVI-I-2"]
'''

str_done = '''
Config written.
'''

str_image_done = 'Image created.  Proceeding to create its options.'
str_size_prompt = 'Enter size of image: '
str_select_prompt = 'Make selection: '

def xrandr_enumerate():
  text = Popen(['xrandr'], stdout = PIPE).communicate()[0]
  outputs = []
  descriptions = []
  for line in text.split('\n'):
    if ' connected ' in line:
      outputs.append(line.split(' ')[0])
      descriptions.append(' '.join(line.split(' ')[2:]))
  return outputs, descriptions

def xrandr_select():
  selected = []
  possible, descriptions = xrandr_enumerate()

  print str_xrandr_set
  
  while (True):
    print str_xrandr_select
    index = 0
    for display in possible:
      star = '*' if display in selected else ' '
      print '{} {}. {} {}'.format(star, str(index), display, 
        descriptions[index])
      index += 1
    print '  2. Done'
    choice = int(raw_input(str_select_prompt))
    if choice == 2:
      break
    if possible[choice] in selected:
      selected.remove(possible[choice])
    else:
      selected.append(possible[choice])
  
  selected_text = '\n    '.join(selected) if selected else 'None'
  print str_xrandr_done.format(selected_text)
  return selected

def create(name):
  vm_dir = os.path.join('vm', name)
  if not os.path.exists(vm_dir):
    call(['mkdir', '-p', vm_dir])

  print str_enter_size
  size = raw_input(str_size_prompt)
  
  call(['qemu-img', 'create', '-f', 'qcow2', vm_dir + '/' + 'disk.img'])
  print str_image_done
  
  config = {}
  config['mac'] = {'hostnet': network.gen_mac(), 'usernet': network.gen_mac()}
  
  selected = xrandr_select()
  config['xrandr'] = [{'output': output, 'location':[]}
                      for output in selected]  
  conf.write_guest_conf(name, config)
  print str_done
