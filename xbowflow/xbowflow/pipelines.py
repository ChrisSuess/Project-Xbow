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
              input dict: {'reps': ['1', '2']}
              operation:  'rep ]= {reps}'
              output dicts: [{'rep': '1', 'reps': ['1', '2']},
                             {'rep': '2', 'reps': ['1', '2']}]

    [=  : The gather operator. The *key* gets the list of
          values of the *definition* from each of the input dictionaries in the
          list of input dictionaries.
          Example:
              input dicts [{'rep': 1}, {'rep': 2}]
              operation:  'reps [= {rep}'
              output dict: {'reps': [1, 2], 'rep': 2}
              (note how the value of 'rep' in the output dict is set from the
              value in the last input dict)

    +=  : The append operator. Similar to the gather operator, the *key* gets
          the list of values of the *definition* from each of the input
          dictionaries in the list of input dictionaries appended to it.
          Example:
              input dicts [{'reps': [1, 2], 'rep': 3},
                           {'reps': [1, 2], 'rep': 4}]
              operation:  'reps += {rep}'
              output dict: {'reps': [1, 2, 3, 4], 'rep': 4}

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

Example with ?= operator:

Given input dictionary:
    {'x': 'big', 'y': 'cycle', 'count': 4}

and interface definitions:
    [
       'a        $=  {x}-',
       'a        $=  {a}{y}',
       'count    ?= {count} + 1',
    ]

will produce the outputs dictionary:

    {'x': 'big', 'y': 'cycle', 'count': 5, 'a': 'big-cycle'}

Scatter example::
inputs:
    {'file': 'data', 'sections': ['section1', 'section2']}
desired outputs:
    [{'filename': 'data-section1'}, {'filename': 'data-section2'}]
scatter definition:
    ['section ]= {sections}',
     'filename $=   {file}-{section}']

Gather example:
inputs:
    [{'filename': 'data-section1'}, {'filename': 'data-section2'}]
desired outputs:
    {'filenames': ['data-section1', 'data-section2']}
gather definition:
    ['filenames [= {filename}']

Note that in reality, as existing keys in the input dictionary also appear
in the output dictionary, the actual outputs in both examples above will
include other keys as well.

Configuring Execution Kernels
=============================
Execution kernels do most of the "heavy lifting". They come in two flavours:
SubprocessKernels and FunctionKernels.

SubprocessKernels
-----------------
These are initiated with a string argument, which is the template for the
command the kernel will execute, as a Python subprocess. The template can
contain placeholders for data from the input dictionary that will be
passed to it, e.g.:

    append_kernel = SubprocessKernel('cat {input} >> {output}')
    result = append_kernel.run({'input': 'newdata.dat', 'output': 'all.dat'})

If the placeholder refers to a key in the inputs dictionary that is a list,
it will be represented as a string formed from the space-separeted values of
the list elements.

FunctionKernels
---------------
These are initiated with a Python function that, when the run method is called,
will be executed with the input dictionary as the sole argument, and produce
the output dictionary, e.g.:

    def myfunc(inputs):
        outputs = inputs
        outputs['count'] = len(inputs['filenames'].split())
        return outputs

    count_kernel = FunctionKernel(myfunc)
    result = count_kernel.run({'filenames': 'file1 file2 file3'})


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
from __future__ import print_function
import sys
import tempfile
import subprocess
class InterfaceKernel(object):
    '''
    An InterfaceKernel provides the rewiring between execution kernels.
    '''
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
            words = con.split()
            key = words[0]
            operator = words[1]
            defn = ' '.join(words[2:])
            self.connections.append([key, operator, defn])
        self.scatterwidth = None
        self.operation = 'link'
        for i in range(len(self.connections)):
            if self.connections[i][1] == ']=':
                self.operation = 'scatter'
            elif self.connections[i][1] == '[=':
                self.operation = 'gather'
            elif self.connections[i][1] == '+=':
                self.operation = 'gather'
            if len(self.connections[i]) != 3:
                print('Error: {}'.format(self.connections[i]))
                exit(1)

    def run(self, inputs):
        """
        Run the kernel.

        Args:
            inputs (dict or list of dicts): the input

        Returns:
            dict or list of dicts. These are guaranteed to contain at least
            one key:
                'returncode' : the returncode from running this kernel, or
                that of the previous kernel in the pipeline that exited with
                a non-zero returncode.
        """
        if isinstance(inputs, list):
            for i in inputs:
                if not isinstance(i, dict):
                    raise RuntimeError('Error: argument passed to run is a list of type {}. It must be a dict or list of dicts'.format(type(i)))
        elif not isinstance(inputs, dict):
            raise RuntimeError('Error: argument {} passed to run is of type {}. it must be a dict or list of dicts'.format(inputs, type(inputs)))

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
                outputs['returncode'] = 0
                return outputs
            except:
                outputs['returncode'] = 1
                outputs['output'] = sys.exc_info()
                return outputs
        elif self.operation == 'gather':
            try:
                outputs = inputs[0].copy()
                for inp in inputs:
                    if 'returncode' in inp:
                        if inp['returncode'] != 0:
                            outputs = inp.copy()
                if 'returncode' in outputs:
                    if outputs['returncode'] != 0:
                        return outputs
                for con in self.connections:
                    if con[1] == '$=':
                        outputs[con[0]] = con[2].format(**outputs)
                    elif con[1] == '?=':
                        outputs[con[0]] = str(eval(con[2].format(**outputs)))
                    elif con[1] == '[=':
                        outputs[con[0]] = [(con[2].format(**outputs))]
                    elif con[1] == '+=':
                        if con[0] in outputs:
                            if not isinstance(outputs[con[0]], list):
                                outputs[con[0]] = [outputs[con[0]]]
                            outputs[con[0]].append(con[2].format(**outputs))
                        else:
                            outputs[con[0]] = [con[2].format(**outputs)]
                for inp in inputs[1:]:
                    for con in self.connections:
                        if con[1] == '[=' or con[1] == '+=':
                            outputs[con[0]].append(con[2].format(**inp))
                outputs['returncode'] = 0
                return outputs
            except:
                outputs['returncode'] = 1
                outputs['output'] = sys.exc_info()
                return outputs
        else:
            if 'returncode' in inputs:
                if inputs['returncode'] != 0:
                    outputs = [inputs]
                    return outputs
            for con in self.connections:
                if con[1] == ']=':
                    scatterwidth = len(inputs[con[2][1:-1]])
                    if self.scatterwidth is not None:
                        if self.scatterwidth != scatterwidth:
                            raise ValueError('Error - inconsistent widths in scatter interface {} {}'.format(con[0], con[2]))
                    else:
                        self.scatterwidth = scatterwidth
            outputs = []
            for i in range(self.scatterwidth):
                try:
                    output = inputs.copy()
                    for con in self.connections:
                        if con[1] == ']=':
                            output[con[0]] = output[con[2][1:-1]][i]
                        elif con[1] == '?=':
                            output[con[0]] = str(eval(con[2].format(**output)))
                        elif con[1] == '$=':
                            output[con[0]] = con[2].format(**output)
                    output['returncode'] = 0
                except:
                    output['returncode'] = 1
                    output['output'] = sys.exc_info()
                outputs.append(output)
            return outputs

class SubprocessKernel(object):
    def __init__(self, template):
        """
        Builds a command from the template string and the input dict, then
        executes it  using the Python subprocess module

        Attributes:
            template (str): the template for the command to be executed
            operation (str): takes the value 'compute'
        """
        self.template = template
        self.operation = 'compute'


    def run(self, inputs, dryrun=False):
        """
        Run the kernel with the given inputs.
        Args:
            inputs (dict): the inputs. Must contain a key 'cmd' which
                contains a string that defines the command to be run.
            dryrun (Bool, optional): if True, the command is not actually
                executed

        Returns:
            dict : contains a copy of the input dictionary, with at least
                three keys:
                    'output' : the standard output and error from the command
                    'returncode' : the exit code for the command
                    'cmd' : the command that was run.
        """
        if not isinstance(inputs, dict):
            print(inputs)
            raise TypeError('Inputs is not a dict')
        outputs = inputs
        if 'returncode' in inputs:
            if inputs['returncode'] != 0:
                return outputs
        else:
            outputs['returncode'] = 0
        try:
            tmpinp = {}
            for key in inputs:
                if isinstance(inputs[key], list):
                    tmpinp[key] = ' '.join(str(k) for k in inputs[key])
                else:
                    tmpinp[key] = inputs[key]
            cmd = self.template.format(**tmpinp)
            tmpdir = tempfile.mkdtemp()
            preamble = 'mkdir -p {}; cd {}; '.format(tmpdir, tmpdir)
            cmd = preamble + cmd
        except KeyError:
            print([key for key in inputs])
            print(self.template)
            raise
        try:
            outputs['cmd'] = cmd
            if not dryrun:
                result = subprocess.check_output(cmd, shell=True,
                                                 stderr=subprocess.STDOUT)
                outputs['output'] = result
        except subprocess.CalledProcessError as error:
            outputs['returncode'] = error.returncode
            outputs['cmd'] = error.cmd
            outputs['output'] = error.output
        return outputs


class FunctionKernel(object):
    '''
    A kernel that wraps a Python function.
    '''
    def __init__(self, func):
        """
        Applies a given Python function to the input dict

        Attributes:
            operation (str): takes the value 'compute'
        """
        self.operation = 'compute'
        self.func = func

    def run(self, inputs, dryrun=False):
        """
        Run the kernel with the given inputs.
        Args:
            inputs (dict): the inputs.
            dryrun (Bool, optional): if True, the function is not actually
                evaluated.

        Returns:
            dict : contains a copy of the input dictionary, with at least
                one key:
                    'returncode' : the exit code for the command
                typically it will also feature new or modified keys
                produced by the function.
        """
        outputs = inputs
        if 'returncode' in inputs:
            if inputs['returncode'] != 0:
                return outputs
        try:
            outputs['cmd'] = self.func.__name__
            if not dryrun:
                result = self.func(inputs)
                for key in result:
                    outputs[key] = result[key]
        except:
            outputs['returncode'] = 1
            outputs['output'] = sys.exc_info()[0]
        return outputs

class Pipeline(object):
    '''
    A Pipeline is a seriers of sequentially-executed kernels.
    '''
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
        if self.client is None:
            return self.dryrun(inputs)

        intermediates = [inputs]
        for kernel in self.klist:
            evaluated = False
            inp = intermediates[-1]
            if isinstance(inp, list) and kernel.operation == 'gather':
                intermediates.append(self.client.submit(kernel.run, inp, pure=False))
            else:
                if isinstance(inp, list):
                    intermediates.append(self.client.map(kernel.run, inp,
                                                         pure=False))
                else:
                    inter = self.client.submit(kernel.run, inp, pure=False)
                    if kernel.operation == 'scatter':
                        intermediates.append(inter.result())
                        evaluated = True
                    else:
                        intermediates.append(inter)
        outputs = intermediates[-1]
        if not evaluated:
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
        kernel_number = 0
        for k in self.klist:
            if k.operation != 'compute':
                if isinstance(inp, list) and k.operation != 'gather':
                    out = [k.run(i) for i in inp]
                else:
                    out = k.run(inp)
            else:
                print('===== Kernel {} ====='.format(kernel_number))
                if isinstance(inp, list):
                    out_list = [k.run(i, dryrun=True) for i in inp]
                    for out in out_list:
                        if out['returncode'] != 0:
                            print('Error: {}'.format(out['output']))
                        else:
                            print(out['cmd'])
                        print('--------------')
                else:
                    out = k.run(inp, dryrun=True)
                    print(out['cmd'])
                    if out['returncode'] != 0:
                        print('Error: {}'.format(out['output']))
                kernel_number += 1
            inp = out
        print('======================')
        return out
