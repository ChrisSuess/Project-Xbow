import os
import yaml
import sys
from xbowflow import xflowlib
from xbowflow.clients import XflowClient

def multirun(client, args):
    # Create and configure kernels:
    cmd1 = 'gmx grompp -f x.mdp -c x.gro -p x.top -o x.tpr'
    grompp = xflowlib.SubprocessKernel(cmd1)
    grompp.set_inputs(['x.mdp', 'x.gro', 'x.top'])
    grompp.set_outputs(['x.tpr'])

    cmd2 = 'gmx mdrun -s x.tpr -o x.trr -x x.xtc -c x.gro -e x.edr -g x.log'
    mdrun = xflowlib.SubprocessKernel(cmd2)
    mdrun.set_inputs(['x.tpr'])
    mdrun.set_outputs(['x.trr', 'x.xtc', 'x.gro', 'x.edr', 'x.log'])

    # Upload data
    startcrds = client.upload(xflowlib.load(args['startcrds']))
    mdpfile = client.upload(xflowlib.load(args['mdpfile']))
    topfile = client.upload(xflowlib.load(args['topfile']))

    # Run kernels
    mdpfiles = [mdpfile] * len(args['repdirs'])
    tprfiles = client.map(grompp, mdpfiles, startcrds, topfile)
    trrfiles, xtcfiles, grofiles, edrfiles, logfiles = client.map(mdrun, tprfiles)
    deffnm = args['deffnm']
    # Save final files
    for i, d, in enumerate(args['repdirs']):
        if not os.path.exists(d):
            os.mkdir(d)
        if trrfiles[i].result() is not None:
            trrfiles[i].result().save('{}/{}.trr'.format(d, deffnm))
        if xtcfiles[i].result() is not None:
            xtcfiles[i].result().save('{}/{}.xtc'.format(d, deffnm))
        if grofiles[i].result() is not None:
            grofiles[i].result().save('{}/{}.gro'.format(d, deffnm))
        if edrfiles[i].result() is not None:
            edrfiles[i].result().save('{}/{}.edr'.format(d, deffnm))
        if logfiles[i].result() is not None:
            logfiles[i].result().save('{}/{}.log'.format(d, deffnm))

if __name__ == '__main__':
    # Load the parameters:
    with open(sys.argv[1]) as f:
        args = yaml.load(f)

    # Get an Xflow client:
    client = XflowClient(local=args['local'])

    # Run the job:
    multirun(client, args)
    client.close()
