========
Xbowflow
========

**Xbowflow** provides a workflow system for use with **Xbow** clusters. Built on top of **Dask Distributed**(https://distributed.readthedocs.io/en/latest/), **Xbowflow** distributed the different tasks in your workflow across your **Xbow** cluster in as efficient manner as possible, running jobs in parallel where appropriate, and keeping data close to compute. In addition it provides resilience (e.g., if a worker node fails, the task is re-run elsewhere).

Running Workflow jobs
_____________________

While simple jobs can be submitted to an **Xbow** cluster directly from your own workstation/laptop, to use **Xbowflow** you need to be logged into the cluster itself. 

We provide two options for creating and running workflow jobs: by writing scripts in Python, or by writing scripts in **Xbowflow**'s own workflow definition language (which is a bit like **Common Workflow Language** (https://en.wikipedia.org/wiki/Common_Workflow_Language), but a bit more basic).

A. Using Python
~~~~~~~~~~~~~~~

**Xbowflow** provides a simple mechanism to turn command line tools into Python functions::

    Command line:
        mytool -a input1 -b input2 -y output1 -z output2
    
    Python:
        output1, output2 = myfunc(input1, input2)

And an slightly extended client for **dask-distributed**::

    Dask-distributed:
        future = distributed_client.submit(myfunc, input1, input2)
        [future1, ...] = distributed_client.map(myfunc, [input1a, ...], [input2a, ...]
    
    **Xbowflow**:
        future1, future2 = xflow_client.submit(myfunc, input1, input2)
        [future1a, ...], [future2a, ...] = xflow_client.map(myfunc, [input1a, ...], [input2a, ...])
        
B. Using **Xflow-run**
~~~~~~~~~~~~~~~~~~~~~~

Instead of writing scripts in Python, they can be written in a specialised workflow definition language
and executed using *xflow-run*::

  % xflow-run workflow.xcf input.yml

*xflow-run* takes two input files. The first (*workflow.xcf* in this example) defines the workflow pattern. The second (*input.yml* in this example) defines the input data for this run of the workflow. 

For a detailed guide to using **Xbowflow**'s workflow definition language, see the wiki pages (https://github.com/ChrisSuess/Project-Xbow/wiki/An-Introduction-to-Xbowflow-Workflows).


Installing  Xbowflow
____________________

**Xbowflow** is designed to work on **Xbow clusters**, and assumes they have *dask.distributed* installed on them and configured.

Other than *dask.distributed*, **Xbowflow** itself has no dependencies outside the Python standard library.

It is available via pip:
``pip install xbowflow``



