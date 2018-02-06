from __future__ import print_function
#import subprocess
#import socket
#from dask.distributed import Client
from xbowflow.pipelines import InterfaceKernel, SubprocessKernel, Pipeline

cx1 = [
        'tmp             $=  $TMPDIR',
        'run_md          $= mkdir - p {tmp}; cd {tmp}; pmemd.CUDA',
        'stage           ?= 0',
        'cycle           ?= 0',
        'shared          $= /home/ubuntu/shared/CoCo-MD_example2',
        'input_file      $= {shared}/min1.in',
        'end_coordinates $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
        'ref_coordinates $= {shared}/penta_w.crd',
        'template        $= {run_md} -O -c {shared}/penta_w.crd'\
                                 ' -p {shared}/[penta_w.top '\
                                 ' -i {input_file}'\
                                 ' -r {end_coordinates}'\
                                 ' -ref {ref_coordinates}'
      ]
c12 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/min2.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
        'template          $= {run_md} -O -c {start_coordinates}'\
                                   ' -p {shared}/penta_w.top'\
                                   ' -i {input_file}'\
                                   ' -r {end_coordinates}'\
                                   ' -ref {ref_coordinates}'
      ]

c23 = [
        'stage             ?= {stage} + 1',
        'input_file        $= {shared}/md.in',
        'start_coordinates $= {end_coordinates}',
        'end_coordinates   $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
        'trajectory        $= {shared}/ala5_{cycle}_{rep}.nc',
        'energies          $= {shared}/ala5_{cycle}_{rep}.ene',
        'template          $= {run_md} -O -c {start_coordinates}'\
                                   ' -p {shared}/penta_w.top'\
                                   ' -i {input_file}'\
                                   ' -r {end_coordinates}'\
                                   ' -e {energies}'\
                                   ' -x {trajectory}'
      ]

c34 = [
        'ref_coordinate_list [= {shared}/ala5_{cycle}_{rep}.rst7',
        'reps                [= {rep}',
        'template            $= mkdir -p {tmp}; cd {tmp};'\
                                     ' pyCoCo -v --dims 3 --grid 20 '\
                                     ' -t {shared}/p[enta_w.pdb'\
                                     ' -s "(not water) and (mass > 2.0)" '\
                                     ' -o {ref_coordinate_list}'\
                                     ' -i {shared}/*.nc'\
                                     ' -l {shared}/coco{cycle}{rep}.log'
      ]

c41 = [
        'tmp             $= $TMPDIR',
        'run_md          $= mkdir -p {tmp}; cd {tmp}; pmemd.CUDA',
        'stage           ?= 0',
        'cycle           ?= {cycle} + 1',
        'input_file      $= {shared}/min1.in',
        'ref_coordinates ]= {ref_coordinate_list}',
        'rep             ]= {reps}',
        'end_coordinates $= {shared}/ala5_{cycle}_{rep}_{stage}.rst',
        'template        $= {run_md} -O'\
                                 ' -c {shared}/penta_w.crd'\
                                 ' -p {shared}/penta_w.top'\
                                 ' -i {input_file}'\
                                 ' -r {end_coordinates}'\
                                 ' -ref {ref_coordinates}'
      ]

ref_coordinates = '/home/ubuntu/shared/CoCo-MD_example2/penta_w.crd'
inits = [{'rep' : 0, 'ref_coordinates': ref_coordinates}, 
         {'rep' : 1, 'ref_coordinates': ref_coordinates}]

ix1 = InterfaceKernel(cx1)
i12 = InterfaceKernel(c12)
i23 = InterfaceKernel(c23)
i34 = InterfaceKernel(c34)
i41 = InterfaceKernel(c41)

amber_kernel = SubprocessKernel()
coco_kernel = SubprocessKernel()

#ip = socket.gethostbyname(socket.gethostname())
#dask_scheduler = '{}:8786'.format(ip)
#client = Client(dask_scheduler)
client = None

prepipe = Pipeline(client, [ix1])
mainpipe = Pipeline(client, [amber_kernel, i12, amber_kernel, i23, amber_kernel, i34, coco_kernel, i41])
out = prepipe.dryrun(inits)
for i in range(2):
    out = mainpipe.dryrun(out)
print(out)
