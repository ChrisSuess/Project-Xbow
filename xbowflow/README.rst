========
Xbowflow
========

**Xbowflow** provides a workflow system for use with **Xbow** clusters. Built on top of **Dask Distributed**(https://distributed.readthedocs.io/en/latest/), **Xbowflow** distributed the different tasks in your workflow across your **Xbow** cluster in as efficient manner as possible, running jobs in parallel where appropriate, and keeping data close to compute. In addition it provides resilience (e.g., if a worker node fails, the task is re-run elsewhere).

Creating Workflow jobs
_____________________
 

Workflows are created by writing Python scripts, that use **Xbowflow**'s **xflowlib** library to provide an interface with conventional command-line tools. The library enables a call to a command line tool to be converted into a Python function.
For example, if we have a command line tool that takes two inputs and provides two outputs::

    mytool -a input1 -b input2 -y output1 -z output2
    
Then in Python with xflowlib, this command line tool could become the function::

        output1, output2 = myfunc(input1, input2)

A workflow is then built up by chaining these function calls together, according to the workflow logic.e.g.::

    output1a, output1b = myfunc1(input1, input2)
    output2a = myfunc2(output1a)
    output2b = myfunc3(output1b)
    output3 = myfunc4(output2a, output2b)
    
    
Here's a simple example, a script that uses the standard unix *rev* command::

    from xbowflow import xflowlib
    rev = xflowlib.SubprocessKernel('rev input > output') # creates the 'kernel'
    rev.set_inputs(['input'])                             # sets the kernel inputs
    rev.set_outputs(['output'])                           # sets the kernel outputs
    input = xflowlib.load('my_text.txt')                  # loads the input data from a file
    output = rev.run(input)                               # runs the kernel with the given 
                                                          #   input, creating output
    output.save('my_reversed_text.txt')                   # the output is saved to a file
    
    
Running Workflow jobs
______________________


**XBowflow**'s **xflowlib** library provides an extended version of the **dask.distributed** client, that distributes tasks (function calls) across the set of available worker nodes. The example script above would execute locally, to spread execution over the cluster, we use the client::

    from xbowflow import xflowlib
    rev = xflowlib.SubprocessKernel('rev input > output') # creates the 'kernel'
    rev.set_inputs(['input'])                             # sets the kernel inputs
    rev.set_outputs(['output'])                           # sets the kernel outputs
    input = xflowlib.load('my_text.txt')                  # loads the input data from a file
    from xbowflow.clients import XflowClient
    client = XflowClient()                                # create a client for the cluster 
                                                          #   of workers
    output = client.submit(rev, input)                    # the function is submitted to one of 
                                                          #   the workers for execution
    output.result().save('my_reversed_text.txt')          # the output is converted from a **future** 
                                                          #   and saved to a file
    

For more details, see the Wiki page (https://github.com/ChrisSuess/Project-Xbow/wiki/An-Introduction-to-Xbowflow-Workflows)


Installing  Xbowflow
____________________

**Xbowflow** is designed to work on **Xbow clusters**, and assumes they have *dask.distributed* installed on them and configured.

Other than *dask.distributed*, **Xbowflow** itself has no dependencies outside the Python standard library.

It is available via pip:
``pip install xbowflow``



