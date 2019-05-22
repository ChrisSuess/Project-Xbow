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
# tpr file data created by grompp, and return two outputs - the compressed 
# trajectory data and the final coordinates data.
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
startcrds = 'bpti.gro'
mdpfile = 'mdrun.mdp'
topfile = 'bpti.top'

startcrd_data = client.upload(xflowlib.load(startcrds))
mdp_data = client.upload(xflowlib.load(mdpfile))
top_data = client.upload(xflowlib.load(topfile))

# We want to run four jobs in parallel, so we need to make four copies of one
# of the files that will be input to grompp:
n_reps = 4
mdp_datas = [mdp_data] * n_reps

# Now we run the grompp and mdrun jobs via the client. The "map" command sends
# each replicate of the job to a different worker (if there are enough of them)
print('Running the grompp kernel for four replicates...')
tpr_datas = client.map(grompp, mdp_datas, startcrd_data, top_data)
print('Running the mdrun kernel for four replicates...')
xtc_datas, gro_datas, log_datas = client.map(mdrun, tpr_datas)

# Now we want to calculate the RMSD of each final structure from the starting
# structure. As this is not a big calculation we will not send it to the
# worker nodes, but just run it locally.
# We will use functions from the Python mdio library for this (mdio is a bit
# like mdtraj, if you know of that). The mdio library expects to load
# structures from filenames, but currently we just have file _data_, the
# data objects created by **Crossflow** have an as_file() method to achieve
# this:

print('Calculating the RMSD:')
refcrds = mdt.load(startcrds)
biggest_rmsd = 0.0
furthest_structure = None
for grodata in gro_datas:
    testcrds = mdt.load(grodata.result().as_file())
    rmsd = mdt.rmsd(testcrds,refcrds)[0]
    if rmsd > biggest_rmsd:
        biggest_rmsd = rmsd
        furthest_structure = grodata
print('Biggest rmsd = {:6.2f}'.format(biggest_rmsd))

# Now we run four more simulations, starting from this set of final coordinates
print('Starting four more simulations from this set of final coordinates...')
tpr_datas = client.map(grompp, mdp_datas, furthest_structure, top_data)
xtc_datas, gro_datas, log_datas = client.map(mdrun, tpr_datas)

# Save final files
print('Saving output files...')
for i, d, in enumerate(xtc_datas):
    d.result().save('rep{}.xtc'.format(i))

for i, d, in enumerate(log_datas):
    d.result().save('rep{}.log'.format(i)) 

for i, d, in enumerate(gro_datas):
    d.result().save('rep{}.gro'.format(i))

# All finished, so it's nice to shut down the client:
client.close()
