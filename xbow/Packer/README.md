# Packer files for creating Crossbow AMIs

This directory contains all the files neccessary to build a Crossbow-compliant AMI.

## Overview
 
### A. How the instance is tailored at launch time
A Crossbow AMI can be used to create either a Scheduler or Worker instance, and has
the option of mounting a shared filesystem. These configuration options are set at
instance creation/launch time, through the 'user_data' option, by creating particular
files in a directory /run/metadata/xbow.

If a file 'is_scheduler' (which may be empty) is created in this directory, the instance
will launch as a scheduler.

If a file 'scheduler_ip_address' is created in this directory, containing a line of the form:

XBOW_SCHEDULER_IP_ADDRESS=X.X.X.X

where X.X.X.X is the (private) IP address of a scheduler instance, then the instance will
launch as a worker.

If a file 'shared_file_system' is created in this directory, containing a line of the form:

XBOW_SHARED_FILESYSTEM={fs_id}.efs.{region}.amazonaws.com:/

where {fs_id} is a file system id and {region} is an AWS region, then the instance will
mount this file system at /home/ubuntu/shared (at the moment this mount location is
hard wired).

###B. How the image implements launch-time tailoring.

The tailoring above is implemented by creating images with three pairs of `systemd` units.
Each pair consists of one unit that is activated at boot time and watches for the creation of
one of the three files in /run/metadata/xbow described above, and a second which is activated
when the watcher unit triggers. These units are placed in /etc/systemd/system.

## Summary of the Packer process

Crossbow images are created using `packer build`:
```
packer build xbow.json
```

Within xbow.json, file provisioners upload the systemd unit files described above, then a shell
provisioner runs `xbow-provision.sh` which does most of the work of installing the packages that
Crossbow images must have. These are:

* Python3 and pip.
* Task Spooler, as a basic job submission and monitoring tool.
* Xbowflowa for workflow management.
* NFS for the shared file system.
* Docker, including the NVIDIA runtime for GPU support.
* Pinda for the installation of Dockerized applications.

## Customising the AMI

The three most likely customizations a user will want to make are a) to provision with extra software (e.g
molecular dynamics packages), b) to change the base image that the AMI is built on, and c) to change the 
name of the AMI that is created.

Adding extra software probably just involves editing `xbow-provision.sh`, but don't forget that some
common packages are available pre-built as Docker containers that can be installed using `pinda`.

The default builds an AMI based on ubuntu 18.04. Note that changing this (edit `xbow.json`) might have an 
impact on the use of systemd to configure the instance at launch time.

The default creates an image with a name `xbow-packer-{datestamp}`. If you change this (edit `xbow.json`), 
you may need to edit the Crossbow configuration file ($HOME/.xbow/settings.yml) accordingly.
