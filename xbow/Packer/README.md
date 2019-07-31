# Packer files for creating Crossbow AMIs

This directory contains all the files neccessary to build a Crossbow-compliant AMI using [Packer](www.packer.io).

## Overview
 
### A. How the instance is tailored at launch time
A Crossbow AMI can be used to create either a scheduler or worker instance, and has
the option of mounting a shared filesystem. These configuration options are activated at boot 
time according to the presence of particular files in a directory `/run/metadata/xbow`.

If a file 'is_scheduler' (which may be empty) is present in this directory, the instance
will boot as a scheduler.

If a file 'scheduler_ip_address' is present in this directory, containing a line of the form:

XBOW_SCHEDULER_IP_ADDRESS=X.X.X.X

where X.X.X.X is the (private) IP address of a scheduler instance, then the instance will
boot as a worker.

If a file 'shared_file_system' is present in this directory, containing a line of the form:

XBOW_SHARED_FILESYSTEM={fs_id}.efs.{region}.amazonaws.com:/

where {fs_id} is a file system id and {region} is an AWS region, then the instance will
mount this file system at /home/ubuntu/shared (at the moment this mount location is
hard wired).

Within the Crossbow code, the creation (or not) of each of these files, and so the ultimate role
of the launched instance, is contolled by passing a shell script as 'user data' to the instance 
creation function.

### B. How the image implements launch-time tailoring.

The tailoring above is implemented by creating images with three pairs of `systemd` units.
Each pair consists of one unit that is activated at boot time and watches for the creation of
one of the three files in `/run/metadata/xbow` described above, and a second which is activated
when the watcher unit triggers. These units are placed in `/etc/systemd/system`.

For a guide to systemd units, see [here](https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files)

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
* [Xbowflow](https://claughton.bitbucket.io/crossflow.html) for workflow management.
* NFS for the shared file system.
* [Docker](www.docker.io), including the NVIDIA runtime for GPU support.
* [Pinda](https://claughton.bitbucket.io/pinda.html) for the installation of Dockerized applications.

## Customising the AMI

The three most likely customizations a user will want to make are a) to provision with extra software (e.g
molecular dynamics packages), b) to change the base image that the AMI is built on, and c) to change the 
name of the AMI that is created.

Adding extra software probably just involves editing `xbow-provision.sh`, but don't forget that some
common packages are available pre-built as Docker containers that can be installed using [pinda](https://claughton.bitbucket.io/pinda.html).

The default builds an AMI based on ubuntu 18.04. Note that changing this (edit `xbow.json`) might have an 
impact on the use of systemd to configure the instance at launch time.

The default creates an image with a name `xbow-packer-{datestamp}`. If you change this (edit `xbow.json`), 
you may need to edit the Crossbow configuration file ($HOME/.xbow/settings.yml) accordingly.
