from __future__ import print_function
from xbowflow.pipelines import InterfaceKernel, SubprocessKernel, Pipeline
from xbowflow.clients import dask_client

# Interface rewiring for the 'pre-loop'
cx1 = [
        'tmp             ?= tempfile.mkdtemp()',
        'preamble        $= mkdir -p {tmp}; cd {tmp}; mpirun -np 2',
        'stage           ?= 0',
        'cycle           ?= 0',
        'shared          $= /home/ubuntu/shared/CoCo-MD_example',
        'input_file      $= {shared}/tmd_1.in',
        'end_coordinates $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
        'ref_coordinates $= {shared}/csaw.min1',
      ]

# Template for the first MD stage (restrained MD)
a1 = '{preamble} pmemd.MPI -O -c {shared}/csaw.min1'\
     ' -p {shared}/csaw.top '\
     ' -i {input_file}'\
     ' -r {end_coordinates}'\
     ' -ref {ref_coordinates}'

# Interface rewiring between 1st and 2nd MD steps
c12 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/tmd_2.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
      ]

# Template for the second restrained MD step
a2 = '{preamble} pmemd.MPI -O -c {start_coordinates}'\
     ' -p {shared}/csaw.top'\
     ' -i {input_file}'\
     ' -r {end_coordinates}'\
     ' -ref {ref_coordinates}'

# Interface rewiring between 2nd and 3rd MD steps
c23 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/production_md.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
        'trajectory        $= {shared}/csaw_{cycle}_{rep}.nc',
      ]

# Template for the unrestrained (production) MD
a3 = '{preamble} pmemd.MPI -O -c {start_coordinates}'\
     ' -p {shared}/csaw.top'\
     ' -i {input_file}'\
     ' -r {end_coordinates}'\
     ' -x {trajectory}'

# Rewiring for interface between MD and CoCo
c34 = [
       'ref_coordinate_list [= {shared}/csaw_{cycle}_{rep}.rst7',
       'reps                [= {rep}',
      ]

# Template for pyCoCo step
c1 = '{preamble} pyCoCo -v -n 2 --dims 4 --grid 13 '\
     ' -t {shared}/csaw_amber.pdb'\
     ' -s "(not water) and (mass > 2.0)" '\
     ' -o {ref_coordinate_list}'\
     ' -i {shared}/*.nc'\
     ' -l {shared}/coco{cycle}{rep}.log'

# Rewiring for interface between CoCo output and starting next MD cycle
c41 = [
        'tmp             ?= tempfile.mkdtemp()',
        'preamble        $= mkdir -p {tmp}; cd {tmp}; mpirun -np 2',
        'stage           ?= 0',
        'cycle           ?= {cycle} + 1',
        'input_file      $= {shared}/tmd_1.in',
        'ref_coordinates ]= {ref_coordinate_list}',
        'rep             ]= {reps}',
        'end_coordinates $= {shared}/csaw_{cycle}_{rep}_{stage}.rst',
      ]

# Defining the dictionary of initial inputs
ref_coordinates = '/home/ubuntu/shared/CoCo-MD_example/csaw.min1'
inits = [{'rep' : 0, 'ref_coordinates': ref_coordinates}, 
         {'rep' : 1, 'ref_coordinates': ref_coordinates}]

# Instatiate the kernels
ix1 = InterfaceKernel(cx1)
i12 = InterfaceKernel(c12)
i23 = InterfaceKernel(c23)
i34 = InterfaceKernel(c34)
i41 = InterfaceKernel(c41)

amber_kernel_1 = SubprocessKernel(a1)
amber_kernel_2 = SubprocessKernel(a2)
amber_kernel_3 = SubprocessKernel(a3)
coco_kernel = SubprocessKernel(c1)

# If client is None, a "dry run" of the pipelines is done, printing out
# the commands that would have been executed.
#client = dask_client()
client = None

# Build the pipelines
prepipe = Pipeline(client, [ix1])
mainpipe = Pipeline(client, [amber_kernel_1, i12, amber_kernel_2, i23, 
                             amber_kernel_3, i34, coco_kernel, i41])

# Run the pre-pipeline, then the main pipeline as many times as desired
out = prepipe.run(inits)
for i in range(2):
    out = mainpipe.run(out)

# Any errors, print the dictionary:
for d in out:
    if d['returncode'] != 0:
        print(d)
