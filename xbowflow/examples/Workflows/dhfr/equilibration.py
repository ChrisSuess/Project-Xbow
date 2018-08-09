import os
import yaml
import sys
from xbowflow import xflowlib

def equilibration(client, args):
    # Create and configure MD kernels:
    cmd = '{mdexe} -O -i md.in -o md.out -c md.crd -p md.prmtop -r md.rst -ref ref.rst -x md.nc'.format(**args)
    mdrun1 = xflowlib.SubprocessKernel(cmd)
    mdrun1.set_inputs(['md.crd', 'ref.rst'])
    mdrun1.set_outputs(['md.rst', 'md.nc'])
    mdrun1.set_constant('md.prmtop', args['prmtop'])
    mdrun1.set_constant('md.in', args['mdin1'])

    mdrun2 = mdrun1.copy()
    mdrun2.set_constant('md.in', args['mdin2'])

    mdrun3 = mdrun1.copy()
    mdrun3.set_constant('md.in', args['mdin3'])
    
    startcrds = client.upload(args['startcrds'])

    restart, trajfile = client.submit(mdrun1, startcrds, startcrds)
    restart, trajfile = client.submit(mdrun2, restart, startcrds)
    restart, trajfile = client.submit(mdrun3, restart, startcrds)

    trajfile.result().write(args['outtraj'])
    restart.result().write(args['outcrds'])
        
if __name__ == '__main__':
    # Get an Xflow client:
    client = xflowlib.XflowClient(local=True)

    # Load the parameters:
    with open(sys.argv[1]) as f:
        args = yaml.load(f)

    # Run the job:
    equilibration(client, args)
