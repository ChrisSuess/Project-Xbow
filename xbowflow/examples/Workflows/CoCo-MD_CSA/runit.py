import os
import time
import mdtraj as mdt
from xbowflow import xflowlib
from xbowflow.clients import XflowClient
from extasycoco.coco import complement

def makemdt(crdfile, topfile):
    '''Make an MDTraj trajectory object from a coordinates file'''
    result = mdt.load(crdfile.as_file(), top=topfile.as_file())
    return result

if __name__ == '__main__':

    mc = XflowClient()

    inpcrd = xflowlib.load('csaw.rst7')
    mdin1 = xflowlib.load('tmd_1.in')
    mdin2 = xflowlib.load('tmd_2.in')
    mdin3 = xflowlib.load('production_md.in')
    prmtop = xflowlib.load('csaw.prmtop')

    md1 = xflowlib.SubprocessKernel('pmemd.cuda -O -i x.mdin -c x.rst7 -p x.prmtop -r out.rst7 -ref ref.rst7 -o x.mdout')
    md1.set_inputs(['x.mdin', 'x.rst7', 'ref.rst7'])
    md1.set_outputs(['out.rst7', 'x.mdout'])
    md1.set_constant('x.prmtop', prmtop)

    md2 = xflowlib.SubprocessKernel('pmemd.cuda -O -i x.mdin -c x.rst7 -p x.prmtop -x out.nc -o x.mdout')
    md2.set_inputs(['x.mdin', 'x.rst7'])
    md2.set_outputs(['out.nc', 'x.mdout'])
    md2.set_constant('x.prmtop', prmtop)

    npoints=10
    start_time = time.time()

    # Convert the initial coordinates to a single-frame trajectory - this
    # will be enlarged every CoCo-MD cycle
    t_all = mc.submit(makemdt, inpcrd, prmtop).result()
    t_all.save('cocomd.nc')
    now = time.time()
    print('Cycle: {:2d} trajectory size: {:5d} frames, cycle time: {:6d}s'.format(0, len(t_all), int(now - start_time)))
    for cycle in range(1, 40):
        start_time = time.time()
        # Run CoCo on the trajectory so far
        c0 = complement(t_all, npoints=npoints, selection='protein and (mass > 2.0)')
        # Extract each snapshot from the CoCo-generated trajectory
        x0 = [mc.upload(c0[i]) for i in range(len(c0))]
        # Run tmd step 1
        r1, o1 = mc.map(md1, mdin1, inpcrd, x0)
        # Run tmd step 2
        r2, o2 = mc.map(md1, mdin2, r1, x0)
        # Run production MD
        x3, o3 = mc.map(md2, mdin3, r2)
        # Add the new trajectory data to the collection
        t_new = mc.map(makemdt, x3, prmtop)
        for t in t_new:
            t_all += t.result()
        # Write out the current trajectory
        now = time.time()
        print('Cycle: {:2d} trajectory size: {:5d} frames, cycle time: {:6d}s'.format(cycle, len(t_all), int(now - start_time)))
        os.rename('cocomd.nc', 'cocomd.nc.bak')
        t_all.save('cocomd.nc')

    xflowlib.purge()
