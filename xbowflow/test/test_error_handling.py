from xbowflow import xflowlib
from xbowflow.clients import XflowClient
import subprocess

DEBUG = True
ls = xflowlib.SubprocessKernel('ls {x} > output')
ls.set_inputs(['x'])
if DEBUG:
    ls.set_outputs(['output', xflowlib.DEBUGINFO])
else:
    ls.set_outputs(['output'])

if __name__ == '__main__':
    client = XflowClient(local=True)
    testdata = '-a'
    if DEBUG:
        output, result = client.submit(ls, testdata)
        print(result.result())
    else:
        output = client.submit(ls, testdata)
    output.result().save('ls-result1.log')
    testdata = 'crap'
    if DEBUG:
        output, result = client.submit(ls, testdata)
        print(result.result())
    else:
        output = client.submit(ls, testdata)
    output.result().save('ls-result2.log')
    client.close()
