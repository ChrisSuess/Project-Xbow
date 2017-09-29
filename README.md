# Project-Xbow
A computional chemistry cloud based project.

To launch an instance: python xbow.py -n NAME_OF_JOB -p AWS

Instances take several moments to bootup so user must wait until it is ready to accept jobs.

To run a script on instance: python xbow.py -n NAME_OF_JOB -p AWS -s SCRIPT_NAME

To get SSH details of instance: python xbow.py -n NAME_OF_JOB -p AWS -i
