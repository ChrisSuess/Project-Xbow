from xbowflow import xflowlib
from xbowflow.clients import XflowClient
import subprocess

DEBUG = True
xflowlib.set_filehandler('shared')
ls = xflowlib.SubprocessKernel('ls {x} > output')
ls.set_inputs(['x', 'td.dat'])
if DEBUG:
    ls.set_outputs(['output', xflowlib.DEBUGINFO])
else:
    ls.set_outputs(['output'])

if __name__ == '__main__':
    client = XflowClient(local=True)
    with open('test_data.dat', 'w') as f:
        f.write('some test data\n')
    td = xflowlib.load('test_data.dat')
    testarg = '-al'
    if DEBUG:
        output, result = client.submit(ls, testarg, td)
        print(result.result())
    else:
        output = client.submit(ls, testarg, td)
    output.result().save('ls-result1.log')
    testarg = 'crap'
    if DEBUG:
        output, result = client.submit(ls, testarg, td)
        print(result.result())
    else:
        output = client.submit(ls, testarg, td)
    output.result().save('ls-result2.log')
    client.close()
