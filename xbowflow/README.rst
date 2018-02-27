Xbowflow
========

Xbowflow provides a workflow system for use with Xbow clusters.

Using Xbowflow
--------------

A. Simple jobs
______________

To run a single command on a single worker node in your xbow cluster, use *xflow-exec*::


  % xflow-exec tar -cvf datfiles.tar *.dat


To run a single command on every worker node, use *xflow-execall*. This is mainly useful for system-wide software updates::

  % xflow-execall sudo pip install xbowflow --upgrade

For non-interactive jobs, use *xflow-submit*::

  % xflow-submit -o job.out 'tar -cvf datfiles.tar *.dat'

**Note the command is quoted.**


B. Workflow jobs
________________

To run a workflow on your xbow cluster, use *xflow-run*::

  % xflow-run workflow.xcf input.dat

*xflow-run* takes two input files. The first (*workflow.xcf* in this example) defines the workflow pattern. The second (*input.dat* in this example) defines the input data for this run of the workflow. The wiki pages describe how to make these files.

Typically you will use *xflow-submit* to run your workflow in the background::

  % xflow-submit -o workflow.log 'xflow-run workflow.xcf input.dat'



Installing  Xbowflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Prerequisites
^^^^^^^^^^^^^

Xbowflow is designed to work on Xbow clusters, and assumes they have dask.distributed installed on them and configured.

Xbowflow itself has no dependencies outside the Python standard library.

It is available via pip:
``pip install xbowflow``

Getting Xbowflow
~~~~~~~~~~~~~~~~
Xbowflow is a sub-package of Project-Xbow:

``git clone https://github.com/ChrisSuess/Project-Xbow``


