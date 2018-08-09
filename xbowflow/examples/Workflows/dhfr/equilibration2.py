import os
import yaml
import sys
from xbowflow import xflowlib

def equilibration(client, args):
    # Create and configure MD kernels:
    cmd = '{mdexe} -O -i md.in -o md.out -c md.crd -p md.prmtop -r md.rst -ref ref.crd -x md.nc'.format(**args)
    mdrun1 = xflowlib.SubprocessKernel(cmd)
    mdrun1.set_inputs(['md.crd', 'ref.crd'])
    mdrun1.set_outputs(['md.rst', 'md.nc'])
    mdrun1.set_constant('md.prmtop', args['prmtop'])
    mdrun1.set_constant('md.in', args['mdin1'])

    mdrun2 = mdrun1.copy()
    mdrun2.set_constant('md.in', args['mdin2'])

    mdrun3 = mdrun1.copy()
    mdrun3.set_constant('md.in', args['mdin3'])
    
    g = {}
    g['md.crd'] = client.upload(args['startcrds'])
    g['ref.crd'] = client.upload(args['startcrds'])

    inputs = {}
    inputs['md.crd'] = g['md.crd']
    inputs['ref.crd'] = g['ref.crd']
    results = client.submit(mdrun1, inputs)
    for k in results:
        g[k] = results[k]
    inputs['md.crd'] = g['md.rst']
    results = client.submit(mdrun2, inputs)
    for k in results:
        g[k] = results[k]
    inputs['md.crd'] = g['md.rst']
    results = client.submit(mdrun3, inputs)
    for k in results:
        g[k] = results[k]

    g['md.nc'].result().write(args['outtraj'])
    g['md.rst'].result().write(args['outcrds'])
        
if __name__ == '__main__':
    # Get an Xflow client:
    client = xflowlib.XflowClient(local=True)

    # Load the parameters:
    with open(sys.argv[1]) as f:
        args = yaml.load(f)

    # Run the job:
    equilibration(client, args)
