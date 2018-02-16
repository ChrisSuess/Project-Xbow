from __future__ import print_function
from xbowflow.pipelines import InterfaceKernel, SubprocessKernel, Pipeline
from xbowflow.clients import dask_client

cx1 = [
         'shared   $= /home/ubuntu/shared/multirun',
         'workdir  $= {shared}/rep{rep:03d}',
         'preamble $= cd {workdir}; mpirun -np 2',
      ]

a1 = '{preamble} pmemd.MPI -O -c {workdir}/start.rst'\
                         ' -p {shared}/system.top '\
                         ' -i {shared}/run.in'\
                         ' -x {workdir}/trajectory.nc' 

inits = [{'rep' : i} for i in range(4)]

ix1 = InterfaceKernel(cx1)

amber_kernel = SubprocessKernel(a1)

#client = dask_client()
client = None

pipe = Pipeline(client, [ix1, amber_kernel])
out = pipe.run(inits)
for d in out:
    if d['returncode'] != 0:
        print( d)
