import os
from subprocess import call

def perform(mount_dict):
  for key in mount_dict:
    value = mount_dict[key]
    where = os.path.realpath(os.path.join('share', key))
    what = os.path.realpath(os.path.expanduser(value))
    if not os.path.exists(where):
      call( [ 'mkdir', where ] )
    else:
      if os.path.ismount(where):
        call( [ 'umount', where ] )
    call( [ 'mount', '--bind', what, where ] )
    print ''.join(['Mounted ', value, ' to ', key])

def is_mount_in_mtab(mount):
  with open('/etc/mtab', 'r') as f:
    for line in f:
      if mount in line:
        return True
  return False

def clean():
  folders = [os.path.join('share', name) for name in os.listdir('share')
             if os.path.isdir(os.path.join('share', name))]
  mounted_folders = [name for name in folders
                     if is_mount_in_mtab(os.path.realpath(name))]

  for folder in mounted_folders:
    call(['umount', folder])
    
  for folder in folders:
    if len(os.listdir(folder))==0:
      call(['rmdir', folder])


