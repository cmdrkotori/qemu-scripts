## QEMU scripts

A poor man's virt-manager.  A collection of craft-able scripts to make 
managing my virtual machines easier.  Supports PCIE-passthrough.

Inspirational video: [Youtube video]

Discussion: [Archlinux thread]

A lot of credit to the OP of the thread for pointing me in the right 
direction.

## Prerequisites

* Python 2.7
* bridge-utils
* samba (for sharing files with Windows hosts)
* Synergy (optional, run that yourself.)

## Setup

First initialize your system.  This mostly makes your system capable of
passing through your second video card, and gathers some information about
your system.  This init script should work on Arch, Fedora, and Ubuntu.

>./init.py

>reboot

Create a virtual machine with a disk image of whatever size you want.  Note 
that you can set an exorbitantly large size and the qcow2 image will only
take up as much as it stores. (with a little overhead.)

>./create.py win7

Perform any minor tweaking to its json config as needed, then run your
virtual machine.

>./run.py win7 basic

Or if you are brave, use the legacy script.  If you have a more exotic setup
you may also want to edit this script to your liking instead.

>./launch.py win7 basic

## Caveats

This script is designed for passing through a single video card only.  It
does offer some windowed modes, however.

As the names of the launch.py "models" suggest, you can start with a basic
system and slowly make it more complicated as you feed Windows drivers in
stages.  Your computer and/or VM may or may not support all of them.

You will need the [virtio drivers] to get accelerated hard disk access on
Windows guests.

The 'shares' folder must not be a symlink.  This can cause connections to
smbd to (partially) hang.  Use the provided functionality to bind folders in
your filesystem to it instead.

The launch.py script takes as many options as you like, such as extra images
to mount and usb devices to pass through.  I recommend you store them in a
shell script (e.g. rwin7.sh) for easy launching.

The virtual machine's usb subsystem is not suitable for flashing phones.  In
fact, no virtual machine is.

You may have to edit the odd config file or two after you created your vm.
The xrandr statements if you have any will need editing, for example.

Windows VMs will need to compile [Synergy]. (good luck.)  Or you can donate
to its developers and have them provide you with a Windows installer.

Try the vga:hack flag if you having trouble getting your video card working.
You may want to keep it around anyway so you can click through superuser
prompts.

## TODO

* Use a bridged adapter for internet access instead of usermode networking,
which will let you print from your VM. (currently I print to pdf and print
that from the host.)
* Code needs rework.  This was my first non-trivial python undertaking and it
probably shows that specifically my python knowledge is self-taught.

[Youtube video]:https://www.youtube.com/watch?v=37D2bRsthfI
[Archlinux thread]:https://bbs.archlinux.org/viewtopic.php?id=162768
[virtio drivers]:http://www.linux-kvm.org/page/WindowsGuestDrivers/Download_Drivers
[synergy]:http://synergy-project.org/
