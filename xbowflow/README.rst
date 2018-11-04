Xbowflow
========

**Xbowflow** provides a workflow system for use with **Xbow** clusters. Built on top of **Dask Distributed** (https://distributed.readthedocs.io/en/latest/), **Xbowflow** distributed the different tasks in your workflow across your **Xbow** cluster in as efficient manner as possible, running jobs in parallel where appropriate, and keeping data close to compute. In addition it provides resilience (e.g., if a worker node fails, the task is re-run elsewhere).

Running Workflow jobs
_____________________

While simple jobs can be submitted to an **Xbow** cluster directly from your own workstation/laptop, to use **Xbowflow** you need to be logged into the cluster itself. 

Once there, the key command is *xflow-run*::

  % xflow-run workflow.xcf input.yml

*xflow-run* takes two input files. The first (*workflow.xcf* in this example) defines the workflow pattern. The second (*input.yml* in this example) defines the input data for this run of the workflow. 

For a detailed guide to using **Xbowflow**, see the wiki pages (https://github.com/ChrisSuess/Project-Xbow/wiki/An-Introduction-to-Xbowflow-Workflows).


Installing  Xbowflow
--------------------

**Xbowflow** is designed to work on **Xbow clusters**, and assumes they have *dask.distributed* installed on them and configured.

Other than *dask.distributed*, **Xbowflow** itself has no dependencies outside the Python standard library.

It is available via pip:
``pip install xbowflow``



