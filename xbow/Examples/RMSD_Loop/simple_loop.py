import mdtraj as mdt
from xbowflow import xflowlib
from xbowflow.clients import XflowClient

# Create and configure the kernels. A kernel is a python function that
# runs a program that would normally be run from the command line, and
# returns the results the command produces.  
#
# First we create a kernel that turns "grompp" into a python function. The
# function will take three inputs (mdp file data, starting coordinates data,
# and topology data) and return one output (the tpr file data)

#print('Creating the "grompp" kernel...')
grompp_command = 'gmx grompp -f x.mdp -c x.gro -p x.top -o x.tpr'
grompp = xflowlib.SubprocessKernel(grompp_command)
grompp.set_inputs(['x.mdp', 'x.gro', 'x.top'])
grompp.set_outputs(['x.tpr'])

# Now we do the same for "mdrun". The function will take just one input, the
# tpr file data created by grompp, and return three outputs - the compressed 
# trajectory data, the final coordinates data, and the job log file.
print('Creating the grompp and mdrun kernels...')
mdrun_command = 'gmx mdrun -s x.tpr -x x.xtc -c x.gro -g x.log'
mdrun = xflowlib.SubprocessKernel(mdrun_command)
mdrun.set_inputs(['x.tpr'])
mdrun.set_outputs(['x.xtc', 'x.gro', 'x.log'])

# Now we start a **Crossflow** client. The client is how we send individual jobs
# out to the worker nodes.
print('Starting a Crossflow client...')
client = XflowClient()

# On the command line we pass data to and from programs by specifying filenames,
# But to run the same job as a function we need to pass the actual data itself,
# So we upload the input data from each input file:
print('Uploading input data...')
startcrd_name = 'bpti.gro'
targetcrd_name = 'bpti-150000.gro'
mdpfile_name = 'mdrun.mdp'
topfile_name = 'bpti.top'

startcrd = client.upload(xflowlib.load(startcrd_name))
mdp = client.upload(xflowlib.load(mdpfile_name))
top = client.upload(xflowlib.load(topfile_name))

n_cycles = 20
n_reps = 12
smallest_rmsd = 10000.0
# We want to run four jobs in parallel, so we need to make four copies of one
# of the files that will be input to grompp - we choose the mdp file:
mdps = [mdp] * n_reps

for cycle in range(n_cycles):
# Now we run the grompp and mdrun jobs via the client. The "map" command sends
# each replicate of the job to a different worker (if there are enough of them)
    print('Running the grompp kernel for {} replicates...'.format(n_reps))
    tprs = client.map(grompp, mdps, startcrd, top)
    print(f'Running the mdrun kernel for {} replicates...'.format(n_reps))
    xtcs, gros, logs = client.map(mdrun, tprs)

# Now we want to calculate the RMSD of each final structure from the starting
# structure. As this is not a big calculation we will not send it to the
# worker nodes, but just run it locally.
# We will use functions from the Python mdtraj library for this.
# The mdtraj library expects to load structures from filenames, but currently 
# we just have file _data_, the data objects created by **Crossflow** have an 
# as_file() method to achieve this:

    print('Calculating the RMSD:')
    targetcrd = mdt.load(targetcrd_name)
    atom_indices = targetcrd.topology.select('name CA')
    nearest_index = None
    for i, gro in enumerate(gros):
        testcrd = mdt.load(gro.result().as_file())
        rmsd = mdt.rmsd(testcrd, targetcrd, atom_indices=atom_indices)[0]
        if rmsd < smallest_rmsd:
            smallest_rmsd = rmsd
            nearest_structure = gro
            nearest_index = i
    print('Cycle {}, Smallest rmsd = {:6.3f}'.format(cycle, smallest_rmsd))
    # Save the best xtc and gro files, if any:
    if nearest_index is not None:
        print('Saving new trajectory segment')
        xtcs[nearest_index].result().save('bpti-cycle{:03d}.xtc'.format(cycle))
        nearest_structure.result().save('bpti-cycle{:03d}.gro'.format(cycle))
        # set startcrd to the nearest structure for the next cycle
        startcrd = nearest_structure
# All finished, so it's nice to shut down the client:
client.close()
