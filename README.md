## QEMU scripts

A poor man's virt-manager.  A collection of craft-able scripts to make 
managing my virtual machines easier.  Supports PCIE-passthrough.

Inspirational video: [Youtube video]

Discussion: [Archlinux thread]

A lot of credit to the OP of the thread for pointing me in the right 
direction.

## Prerequisites

* Python 3
* qemu-system-x86
* bridge-utils
* Synergy (optional, run that yourself.)

## Setup

First initialize your system.  This mostly makes your system capable of
passing through your second video card, and gathers some information about
your system.  This init script should work on Arch, Fedora, and Ubuntu.  (It
needs superuser permissions to write to system config files.)

>sudo ./init.py

>reboot

Create a virtual machine with a disk image of whatever size you want.  Note 
that you can set an exorbitantly large size and the qcow2 image will only
take up as much as it stores. (with a little overhead.)

>./create.py win7

Perform any minor tweaking to its json config as needed, then run your
virtual machine.

>sudo -E ./run.py win7 basic

Or if you are brave, use the legacy script.  If you have a more exotic setup
you may also want to edit this script to your liking instead.

>sudo -E ./launch.py win7 basic

## Caveats

The scripts will fail if they are not invoked correctly or the prerequisites
are not met.

This script is designed for passing through a single video card only.  It
does offer some windowed modes, however.

As the names of the launch.py "models" suggest, you can start with a basic
system and slowly make it more complicated as you feed Windows drivers in
stages.  Your computer and/or VM may or may not support all of them.

You will need the [virtio drivers] to get accelerated hard disk access on
Windows guests.

The 'shares' folder must not be a symlink.  This can cause connections to
smbd to (partially) hang.  Use the provided functionality to bind folders in
your filesystem to it instead.  Any system-wide smbd and nmbd should be
disabled.

The launch.py and init.py script takes as many options as you like, such as
extra images to mount and usb devices to pass through.  I recommend you store
them in a shell script (e.g. rwin7.sh) for easy launching.

The virtual machine's usb subsystem is not suitable for flashing phones.  In
fact, no virtual machine is.

You may have to edit the odd config file or two after you created your vm.
The xrandr statements if you have any will need editing, for example.

Windows VMs may need to compile [Synergy] (good luck), or you can donate
to its developers and have them provide you with a Windows installer.  You
can also use [looking-glass] which provides lower-latency and framebuffer
passthrough.  Looking Glass's spice server works even when framebuffer
passthrough does not, i.e. mouse + keyboard control even at the bios and on
"unsupported" operating system.

Try the vga:hack flag if you having trouble getting your video card working.
You may want to keep it around anyway so you can click through superuser
prompts in the case of you using Synergy.

Windows 10's PC Health Check program requires that the emulated system supports
UEFI and TPM2.  Adding the terms `uefi` and `tpm` to launch.py's argument list
will load the required components into the virtual machine, with one exception:
the uefi files OVMF_CODE.fd and OVMF_VARS.fd must be the secboot versions.  As
of writing, they are not available in Arch's edk2-ovmf package (the bundled
script in the ovmf directory will work but may not be what you want).  The
secboot variants must be downloaded and extracted from [fedora's edk2-ovmf]
package.  In addition, you may have to then have to disable secure boot in the
BIOS menu to prevent a bootloop; it will still pass the secure boot check as
the firmware only has to support secure boot even if it is not switched on.

The `tpm` option requires that `swtpm` is installed on your system.

## TODO

* Use a bridged adapter for internet access instead of usermode networking,
which will let you print from your VM. (currently I print to pdf and print
that from the host.)
* Mac support ([mac gist])

[Youtube video]:https://www.youtube.com/watch?v=37D2bRsthfI
[Archlinux thread]:https://bbs.archlinux.org/viewtopic.php?id=162768
[virtio drivers]:http://www.linux-kvm.org/page/WindowsGuestDrivers/Download_Drivers
[synergy]:http://synergy-project.org/
[looking-glass]:https://looking-glass.hostfission.com/
[mac gist]:https://gist.github.com/cmdrkotori/d4f78cd814e185b820b19f938392d58a
[fedora's edk2-ovmf]:https://rpmfind.net/linux/rpm2html/search.php?query=edk2-ovmf
