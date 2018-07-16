import yaml
import sys
import mdtraj as mdt
import tempfile
from extasycoco import complement
from xbowflow import xflowlib
from progress.bar import IncrementalBar

def runcocomd(client, args):
    # Create and configure MD kernel 1:
    cmd = '{mdexe} -O -i md.in -c x.crd -p x.prmtop -r x.rst -x x.nc -o md.out -ref ref.crd'.format(**args)
    pmemd1 = xflowlib.SubprocessKernel(cmd)
    pmemd1.set_inputs(['x.crd', 'ref.crd'])
    pmemd1.set_outputs(['x.rst', 'x.nc'])
    pmemd1.set_constant('md.in', args['mdin1'])
    pmemd1.set_constant('x.prmtop', args['prmtop'])

    # Create and configure MD kernel 2:
    pmemd2 = pmemd1.copy()
    pmemd2.set_constant('md.in', args['mdin2'])

    # Create and configure MD kernel 3:
    pmemd3 = pmemd1.copy()
    pmemd3.set_constant('md.in', args['mdin3'])

    # Create and configure a function kernel:
    def makemdt(trajfile, topfile):
        '''Make an MDTraj trajectory object'''
        result = mdt.load(trajfile, top=topfile)
        return result
    maketraj = xflowlib.FunctionKernel(makemdt)
    maketraj.set_inputs(['trajfile'])
    maketraj.set_outputs(['traj'])
    maketraj.set_constant('topfile', args['prmtop'])
    
    # CoCoMD parameters:
    npoints = args['npoints']
    ncycles = args['ncycles']
    selection = args['selection']

    # Convert the initial coordinates to a single-frame trajectory - this
    # will be enlarged every CoCo-MD cycle
    t_all = mdt.load(args['startcrds'], top=args['prmtop'])
    t_all.save(args['trajfile'])

    # Upload the starting coordinates to the client
    inpcrd = client.upload(args['startcrds'])

    # A progress meter:
    bar = IncrementalBar('Running', max=ncycles, suffix='%(index)d/%(max)d ETA: %(eta)dsec.')
    # Main loop:
    for cycle_number in range(1, ncycles + 1):
        # Run CoCo on the trajectory so far and convert the output trajectory
        # into separate files in Amber restart format that are then uploaded.
        tnew = complement(t_all, npoints=npoints, selection=selection)
        xref = []
        for i in range(len(tnew)):
            with tempfile.NamedTemporaryFile(suffix='.rst7') as f:
                tnew[i].save(f.name)
                xref.append(client.upload(f.name))
        # Run tmd step 1
        r1 = client.map(pmemd1, inpcrd, xref)
        # Run tmd step 2
        r2 = client.map(pmemd2, r1['x.rst'], xref)
        # Run production MD
        r3 = client.map(pmemd3, r2['x.rst'], xref)
        # Add the new trajectory data to the collection
        r4 = client.map(maketraj, r3['x.nc'])
        for t in r4['traj']:
            t_all += t.result()
        # Write out the current trajectory
        t_all.save(args['trajfile'])
        bar.next()
    bar.finish()

if __name__ == '__main__':
    # Get an Xflow client:
    client = xflowlib.XflowClient()

    # Load the parameters:
    with open(sys.argv[1]) as f:
        args = yaml.load(f)

    # Run the job:
    runcocomd(client, args)
