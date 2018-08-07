import os
import yaml
import sys
from xbowflow import xflowlib
from distributed.client import as_completed

def multirun(client, args):
    # Create and configure MD kernel:
    cmd = '{mdexe} -deffnm x'.format(**args)
    mdrun = xflowlib.SubprocessKernel(cmd)
    mdrun.set_inputs(['x.tpr'])
    mdrun.set_outputs(['x.log', 'x.gro'])

    repdirs = [os.path.split(t)[0] for t in args['tprfiles']]
    tprfiles = [client.upload(f) for f in (args['tprfiles'])]

    logfiles, grofiles = client.map(mdrun, tprfiles)

    for logfile in as_completed(logfiles):
        i = logfiles.index(logfile)
        d = repdirs[i]
        print('Replicate {} complete'.format(d))
        logfiles[i].result().write(os.path.join(d, 'x.log'))
        grofiles[i].result().write(os.path.join(d, 'x.gro'))
        
if __name__ == '__main__':
    # Get an Xflow client:
    client = xflowlib.XflowClient(local=True)

    # Load the parameters:
    with open(sys.argv[1]) as f:
        args = yaml.load(f)

    # Run the job:
    multirun(client, args)
