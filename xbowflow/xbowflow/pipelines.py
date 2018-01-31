from __future__ import print_function
import sys
import tempfile
import subprocess
"""
Introduction
============

This module defines some classes that can be used to build pipelines for
execution using dask.distributed.

The unit of execution is a "kernel". Kernels are chained together in a
"pipeline".

Kernels are instantiated with some configuration data:

my_kernel = Kernel(config_data)

and are executed when their ".run()' method is called. The run method takes 
a single input object and returns a single object:

output = my_kernel.run(input)

Typically the inputs and outputs are dictionaries, but they may be lists
of dictionaries.
 
Kernels come in two flavours: those that perform the real compute task,
and those that define how the outputs from one task become the inputs
for the next - i.e., they just tweak dictionaries. We call the first 
type of kernel an "execution kernel" and the second type an "interface 
kernel".

A pipeline thus becomes a chain of alternating interface kernels and
execution kernels, associated with some client that can schedule/distribute
the individual tasks. For this, we use a dask.distributed client:

my_pipe = Pipeline(client,[interface_kernel_01, execution_kernel_1, 
                           interface_kernel_12, execution_kernel_2, ...]

Like an individual kernel, a pipeline takes a single object as input (the
input dictionary/list for the first kernel), and outputs a single object
(the output dictionary/list from the last kernel):

output_last = my_pipe.run(input_first).


Configuring interface kernels: the kernel interface language.
=============================================================

a) Basic operation
------------------
When interface kernels are instantiated, you provide them with information
as to how they should 're-wire' the inputs dictionary/list to produce the
output dictionary/list.

This is done by passing a list of strings. The first word in the string is
the *key*. The *key* is a key in the output dictionary. It may relate to one 
from the input dictionary, or may define a new one. The second word in the
string is the *operator*. This defines how the value for the *key* is generated
from all the words in the rest of the string: the *definition*. The available
*operators* are:
    $=  : *key* gets the value of *definition* when the string format function
          is applied to this with the current output dictionary as the argument.
          Example:
              input dict: {'rep': '1'}
              operation:  'file $= input{rep}.txt'
              output dict: {'rep': '1', 'file': 'input1.txt'}

    ?=  : As above, except that after applying the format function the string
          is passed to the python eval() function.
          Example:
              input dict: {'rep':, 1}
              operation:  'next ?= {rep} + 1'
              output dict: {'rep': 1, 'next': 2}}

    ]=  : The scatter operator. Each output dictionary in the list of output
          dictionaries produced by this kernel will set the *key* to one word
          from the list of words in the *definition*.
          Example:
              input dict: {'reps': '1 2'}
              operation:  'rep ]= {reps}'
              output dicts: [{'rep': '1', 'reps': '1 2'}, 
                             {'rep': '2', 'reps': '1 2'}]

    [=  : The gather operator. The *key* gets the space-separated list of 
          values of the *definition* from each of the input dictionaries in the
          list of input dictionaries.
          Example:
              input dicts [{'rep': 1}, {'rep': 2}]
              operation:  'reps [= {rep}'
              output dict: {'reps': '1 2', 'rep': 2}
              (note how the value of 'rep' in the output dict is set from the
              value in the last input dict)

The list of operation strings are used to modify the input dict (or list of
dicts) and produce the output dict (or list of dicts) as follows. First the 
input dict is copied to the output dict unchanged. Then each operation
string in the interface definition list is applied in turn, each time
updating the current state of the output dict(s). For example, if the interface
definition list is:
    [
        'a $= {x}-',
        'a $= {a}{y}'
    ]
then if the inputs dictionary was {'x': 'big', 'y': 'top'}, the parsing would
be:

Step 1: copy the inputs dictionary to the outputs:
    outputs = {'x': 'big', 'y': 'top'}
Step 2: apply the first operation:
    outputs = {'x': 'big', 'y': 'top', 'a': 'big-'}
Step 3: apply the second operation:
    outputs = {'x': 'big', 'y': 'top', 'a': 'big-top'}

The last operation in every definitions list *must* have the key 'template', and
defines the precise command that the following execution kernel will run.
E.g.:
    [
        'a        $= {x}-',
        'a        $= {a}{y}',
        'template $= echo {a}'
    ]

Example with ?= operator::

Given input dictionary:
    {'x': 'big', 'y': 'cycle', 'count': 4}

and interface definitions:
    [
       'a        $=  {x}-',
       'a        $=  {a}{y}',
       'count    ?= {count} + 1',
       'template $= echo {a}-{count}'
    ]

will produce the outputs dictionary:

    {'x': 'big', 'y': 'cycle', 'count': 5, 'a': 'big-cycle', 
      'template': 'echo big-cycle-5'}}

Scatter example::
inputs:
    {'a': 'file', 'copies': 'copy1 copy2'}
desired outputs:
    [{'template': 'cat file-copy1'}, {'template': 'cat file-copy2'}]
scatter definition:
    ['copy ]= {copies}', 
     'a =   {a}-{copy}',
     'template $= cat {a}']

Gather example:
inputs:
    [{'a': 'file-copy1'}, {'a': 'file-copy2'}]
desired outputs:
    {'template': 'cat file-copy1 file-copy2'}
gather definition:
    ['file_list [= {a}',
     'template $= cat {file_list}']] 

Note that in reality, as existing keys in the input dictionary also appear
in the output dictionary, the actual outputs in both examples above will
include other keys as well.

Implementation details
======================

a) Concurrency
--------------

How the jobs get scheduled, and where, is controlled by the dask.distributed
client. Assuming you are familiar with dask cocepts of delayed execution and
'futures', and the general properties of acyclic graphs, the main thing to
be aware of is that each pipeline will only call the dask 'compute' method, or
equivalent, on the output from the last kernel in the pipe. This means a pipe
cannot include any re-entrant features, or feature any conditional execution.

b) Error handing
----------------

Because of the above, error handing needs to be dealt with only after the
pipe has finished executing. This is done by ensuring that the output
dictionary from each kernel includes a 'returncode' key that holds the
exit status of the job that kernel has run. If this is anything other than
zero, then when the next kernel sees this in its input dictionary, it will not
execute its command, but immediately output the input dictionary unchanged. In
this way error messages rapidly 'fall through' the pipeline to the end.

"""
class InterfaceKernel(object):
    def __init__(self, connections):
        """
        Define an interface kernel.

        The main purpose of an interface kernel is to define the 'rewiring'
        required to turn the output from the last execution kernel into the
        input for the next execution kernel.

        Args:
            connections (list):  A list of strings constructed according to
                the interface definitions language.
        Attributes:
            operation (str): the type of interface. takes values 'link', 
                'gather', or 'scatter'. The first inputs a dict and outputs
                one when run. The second takes a list of dicts as input and 
                outputs a single dict. The last takes a single dict as input
                and outputs a list of dicts.
            scatterwidth (None or int): if not None, the number of dicts
                in the output list. Note: this attribute will not be set
                until the run() method is called, since it depends on the
                data in the input dict.
        """
        self.connections = []
        for con in connections:
            w = con.split()
            key = w[0]
            operator = w[1]
            defn = ' '.join(w[2:])
            self.connections.append([key, operator, defn])
        self.scatterwidth = None
        self.operation = 'link'
        for i in range(len(self.connections)):
            if self.connections[i][1] == ']=':
                self.operation = 'scatter'
            if self.connections[i][1] == '[=':
                self.operation = 'gather'
            if len(self.connections[i]) != 3:
                print('Error: {}'.format(self.connections[i]))
                exit(1)
            if self.connections[i][2] == '$TMPDIR':
                self.connections[i][2] = tempfile.mkdtemp()
                

    def run(self, inputs):
        """
        Run the kernel.

        Args:
            inputs (dict or list of dicts): the input

        Returns:
            dict or list of dicts. These are guaranteed to contain at least
            two keys:
                'cmd' : the command that the next execution kernel will run
                'returncode' : the returncode from running this kernel, or
                that of the previous kernel in the pipeline that exited with
                a non-zero returncode.
        """
        for con in self.connections:
            if con[1] == ']=':
                scatterwidth = len(con[2].format(**inputs).split())
                if self.scatterwidth is not None:
                    if self.scatterwidth != scatterwidth:
                        raise ValueError('Error - inconsistent widths in scatter interface')
                else:
                    self.scatterwidth = scatterwidth
                            
        if self.operation == 'link':
            outputs = inputs.copy()
            if 'returncode' in inputs:
                if inputs['returncode'] != 0:
                    return outputs
            try:
                for con in self.connections:
                    if con[1] == '$=':
                        if con[0] != 'template':
                            outputs[con[0]] = con[2].format(**outputs)
                        else:
                            outputs[con[0]] = con[2]
                    elif con[1] == '?=':
                        outputs[con[0]] = str(eval(con[2].format(**outputs)))
                    else:
                        raise ValueError('Error - unknown interface operation {}'.format(con))
                outputs['cmd'] = outputs['template'].format(**outputs)
                outputs['returncode'] = 0
                return outputs
            except:
                outputs['returncode'] = 1
                outputs['cmd'] = 'interface'
                outputs['output'] = sys.exc_info()
                return outputs
        elif self.operation == 'gather':
            try:
                outputs = inputs[0].copy()
                for inp in inputs:
                    if inp['returncode'] != 0:
                        outputs = inp.copy()
                if outputs['returncode'] != 0:
                    return outputs
                for con in self.connections:
                    if con[1] == '[=':
                        outputs[con[0]] = con[2].format(**outputs)
                    if con[0] == 'template':
                        outputs['template'] = con[2]
                for inp in inputs[1:]:
                    for con in self.connections:
                        if not con[0] =='template':
                            if con[1] == '[=':
                                outputs[con[0]] = outputs[con[0]] + ' ' + con[2].format(**inp)
                
                outputs['cmd'] = outputs['template'].format(**outputs)
                outputs['returncode'] = 0
                return outputs
            except:
                outputs['returncode'] = 1
                outputs['cmd'] = 'interface'
                outputs['output'] = sys.exc_info()
                return outputs
        else:
            if inputs['returncode'] != 0:
                outputs = [inputs] * self.scatterwidth
                return outputs
            try:
                outputs = []
                for i in range(self.scatterwidth):
                    output = inputs.copy()
                    for con in self.connections:
                        if con[1] == ']=':
                            output[con[0]] = con[2].format(**output).split()[i]                         
                        elif con[1] == '?=':
                            output[con[0]] = str(eval(con[2].format(**output)))
                        elif con[1] == '$=':
                            if con[0] != 'template':
                                output[con[0]] = con[2].format(**output)
                            else:
                                output[con[0]] = con[2]
                    output['cmd'] = output['template'].format(**output)
                    output['returncode'] = 0
                    outputs.append(output)
                return outputs
            except:
                raise
                for i in range(self.scatterwidth):
                    outputs[i]['returncode'] = 1
                    outputs[i]['cmd'] = 'interface'
                    outputs[i]['output'] = sys.exc_info()
                return outputs
        

class SubprocessKernel(object):
    def __init__(self):
        """
        Executes key 'cmd' in the input dict using the Python subprocess module
        
        Attributes:
            operation (str): takes the value 'compute'
        """
        self.operation = 'compute'


    def run(self, inputs):
        """
        Run the kernel with the given inputs.
        Args:
            inputs (dict): the inputs. Must contain a key 'cmd' which
                contains a string that defines the command to be run.

        Returns:
            dict : contains a copy of the input dictionary, with at least
                three keys:
                    'output' : the standard output and error from the command
                    'returncode' : the exit code for the command
                    'cmd' : the command that was run.
        """
        outputs = inputs
        if 'returncode' in inputs:
            if inputs['returncode'] != 0:
                return outputs
        try:
            result = subprocess.check_output(inputs['cmd'], 
                                             stderr=subprocess.STDOUT,
                                             shell=True)
            outputs['output'] = result
        except subprocess.CalledProcessError as e:
            outputs['returncode'] = e.returncode
            outputs['cmd'] = e.cmd
            outputs['output'] = e.output
        return outputs

class EvalKernel(object):
    def __init__(self):
        """
        Applies the Python eval() command to the string defined by key 'cmd'
        in the input dict.
        
        Attributes:
            operation (str): takes the value 'compute'
        """
        self.operation = 'compute'


    def run(self, inputs):
        """
        Run the kernel with the given inputs.
        Args:
            inputs (dict): the inputs. Must contain a key 'cmd' which
                contains a string that defines the command to be run.

        Returns:
            dict : contains a copy of the input dictionary, with at least
                three keys:
                    'output' : the standard output and error from the command
                    'returncode' : the exit code for the command
                    'cmd' : the command that was run.
        """
        outputs = inputs
        if 'returncode' in inputs:
            if inputs['returncode'] != 0:
                return outputs
        try:
            result = eval(inputs['cmd'])
            outputs['output'] = result
        except Error as e:
            outputs['returncode'] = e.returncode
            outputs['cmd'] = e.cmd
            outputs['output'] = e.output
        return outputs

class FunctionKernel(object):
    def __init__(self, func):
        """
        Applies a given python function to the string defined by key 'cmd' in
        the input dict..
        
        Attributes:
            operation (str): takes the value 'compute'
        """
        self.operation = 'compute'
        self.func = func

    def run(self, inputs):
        """
        Run the kernel with the given inputs.
        Args:
            inputs (dict): the inputs. Must contain a key 'cmd' which
                contains a string that defines the command to be run.

        Returns:
            dict : contains a copy of the input dictionary, with at least
                three keys:
                    'output' : the standard output and error from the command
                    'returncode' : the exit code for the command
                    'cmd' : the command that was run.
        """
        outputs = inputs
        if 'returncode' in inputs:
            if inputs['returncode'] != 0:
                return outputs
        try:
            result = func(inputs['cmd']) 
            outputs['output'] = result
        except Error as e:
            outputs['returncode'] = e.returncode
            outputs['cmd'] = e.cmd
            outputs['output'] = e.output
        return outputs

class DummyKernel(object):
    def __init__(self):
        """
        A dummy kernel for testing. Just copies the input dictionary to the
        output dict.
        
        Attributes:
            operation (str): takes the value 'compute'
        """
        self.operation = 'compute'
    
    def run(self, inputs, fail=False):
        """
        Run the kernel with the given inputs.
        Args:
            inputs (dict): the inputs. Must contain a key 'cmd' which
                contains a string that defines the command to be run.

        Returns:
            dict : contains a copy of the input dictionary, with at least
                three keys:
                    'output' : the standard output and error from the command
                    'returncode' : the exit code for the command
                    'cmd' : the command that was run.
        """
        outputs = inputs
        if outputs['returncode'] != 0:
            return outputs
        if fail:
            outputs['returncode'] = 1
            outputs['output'] = 'DummyKernel failed'
        else:
            outputs['returncode'] = 0
            outputs['cmd'] = 'DummyKernel ran with {}'.format(outputs['cmd'])
        return outputs
    
    
class Pipeline(object):
    def __init__(self, client, klist):
        """
        Initialises a pipeline instance.
        A pipeline is a series of kernels that are executed one after the other

        Args:
            client (Dask.distributed.Client): the client that will run the
                pipeline
            klist (list): the list of kernels to be executed.
        """
        self.client = client
        self.klist = klist

    def run(self, inputs):
        """
        Run the pipeline. 

        Args:
            inputs (dict or list): the inputs to the first kernel in the
                pipeline.
        
        Returns:
            dict or list: the outputs from the last kernel.
        """
        intermediates = [inputs]
        for ki in self.klist:
            inp = intermediates[-1]
            if isinstance(inp, list) and ki.operation != 'gather':
                intermediates.append(self.client.map(ki.run, inp, pure=False))
            else:
                intermediates.append(self.client.submit(ki.run, inp, pure=False))
        outputs = intermediates[-1]
        if isinstance(outputs, list):
            outputs = self.client.gather(outputs)
        else:
            outputs = outputs.result()
        return outputs

    def dryrun(self, inputs):
        """
        Do a dry run of the pipeline.
        Print out the commands that would be run. 

        Args:
            inputs (dict or list): the inputs to the first kernel in the
                pipeline.
        Returns:
            dict or list: the outputs from the last kernel.
        """
        inp = inputs
        out = inp
        ik = 0
        for k in self.klist:
            if k.operation != 'compute':
                print('===== Kernel {} ====='.format(ik))
                if isinstance(inp, list) and k.operation != 'gather':
                   out = [k.run(i) for i in inp]
                else:
                   out = k.run(inp)
                if isinstance(out, list):
                    for o in out:
                        print(o['cmd'])
                        if o['returncode'] != 0:
                            print('Error: {}'.format(o['output']))
                        print('--------------')
                else:
                    print(out['cmd'])
                    if out['returncode'] != 0:
                        print('Error: {}'.format(out['output']))
                inp = out
                ik += 1
        print('======================')
        return out
