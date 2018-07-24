import os
import yaml
import sys
from xbowflow import xflowlib

def multirun(client, args):
    # Create and configure MD kernel:
    cmd = '{mdexe} -deffnm x'.format(**args)
    mdrun = xflowlib.SubprocessKernel(cmd)
    mdrun.set_inputs(['x.tpr'])
    mdrun.set_outputs(['x.log', 'x.gro'])

    repdirs = args['reps']
    tprfiles = [client.upload(f) for f in (args['tprfiles'])]

    r = client.map(mdrun, tprfiles)

    for i, d in enumerate(repdirs):
        for key in ['x.log', 'x.gro']:
            r[key][i].result().write(os.path.join(d, key))
        
if __name__ == '__main__':
    # Get an Xflow client:
    client = xflowlib.XflowClient(local=True)

    # Load the parameters:
    with open(sys.argv[1]) as f:
        args = yaml.load(f)

    # Run the job:
    multirun(client, args)
