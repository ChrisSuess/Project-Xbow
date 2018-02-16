from __future__ import print_function
import xbowflow
from xbowflow.pipelines import InterfaceKernel, SubprocessKernel, Pipeline
from xbowflow.clients import dask_client

cx1 = [
        'cycle             ?= 0',
        'stage             ?= 0',
        'input_file        $= {name}_cycle_{cycle}_stage_{stage}.in',
        'output_file       $= {name}_cycle_{cycle}_stage_{stage}.out',
      ]
c12 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {output_file}',
        'output_file       $= {name}_cycle_{cycle}_stage_{stage}.out',
      ]

foo_template = 'xflow-foo -i {input_file} -o {output_file}'

foo_kernel = SubprocessKernel(foo_template)

ix1 = InterfaceKernel(cx1)
i12 = InterfaceKernel(c12)

client = dask_client(local=True)
pipe = Pipeline(client, [ix1, foo_kernel, i12, foo_kernel])

inputs = {'name': 'foo'}
outputs = pipe.run(inputs)
print(outputs)
client.close()
