========
Xbowflow
========

**Xbowflow** provides a workflow system for use with **Xbow** clusters. Built on top of **Dask Distributed**(https://distributed.readthedocs.io/en/latest/), **Xbowflow** distributed the different tasks in your workflow across your **Xbow** cluster in as efficient manner as possible, running jobs in parallel where appropriate, and keeping data close to compute. In addition it provides resilience (e.g., if a worker node fails, the task is re-run elsewhere).

Creating Workflow jobs
_____________________
 

Workflows are created by writing Python scripts, that use **Xbowflow**'s **xflowlib** library to provide an interface with conventional command-line tools. The library enables a call to a command line tool to be converted into a Python function, e.g.::

    Command line:
        mytool -a input1 -b input2 -y output1 -z output2
    
    Python/xflowlib:
        output1, output2 = myfunc(input1, input2)

A workflow is then built up by chaining these function calls together, according to the workflow logic.e.g.::

    output1a, output1b = myfunc1(input1, input2)
    output2a = myfunc2(output1a)
    output2b = myfunc3(output1b)
    output3 = myfunc4(output2a, output2b)
    
    
Running Workflow jobs
______________________


**XBowflow**'s **xflowlib** library provides an extended version of the **dask.distributed** client, that distributes tasks (function calls) across the set of available worker nodes::

    Dask-distributed:
        future = distributed_client.submit(myfunc, input1, input2)
        [future1, ...] = distributed_client.map(myfunc, [input1a, ...], [input2a, ...])
    
    **Xbowflow**:
        future1, future2 = xflow_client.submit(myfunc, input1, input2)
        [future1a, ...], [future2a, ...] = xflow_client.map(myfunc, [input1a, ...], [input2a, ...])
        

Installing  Xbowflow
____________________

**Xbowflow** is designed to work on **Xbow clusters**, and assumes they have *dask.distributed* installed on them and configured.

Other than *dask.distributed*, **Xbowflow** itself has no dependencies outside the Python standard library.

It is available via pip:
``pip install xbowflow``



