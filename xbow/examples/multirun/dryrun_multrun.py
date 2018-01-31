from __future__ import print_function
#import subprocess
#import socket
#from dask.distributed import Client
from xbowflow.pipelines import InterfaceKernel, GenericKernel, DummyKernel, Pipeline

cx1 = [
        ['shared',          '=', '/home/ubuntu/shared/multirun'             ],
        ['workdir',         '=', '{shared}/rep{rep:03d}'                    ],
        ['run_md',          '=', 'cd {workdir}; mpirun -np 2 pmemd.MPI'     ],
        ['template',        '=', '{run_md} -O -c {workdir}/start.rst'\
                                 ' -p {shared}/system.top '\
                                 ' -i {shared}/run.in'\
                                 ' -x {workdir}/trajectory.nc'             ]
      ]

inits = [{'rep' : i} for i in range(4)]

ix1 = InterfaceKernel(cx1)

amber_kernel = GenericKernel()

#ip = socket.gethostbyname(socket.gethostname())
#dask_scheduler = '{}:8786'.format(ip)
#client = Client(dask_scheduler)
client = None

pipe = Pipeline(client, [ix1])
out = pipe.dryrun(inits)
print(out)
