from xbowflow import xflowlib
from xbowflow.clients import XflowClient
import subprocess

ls = xflowlib.SubprocessKernel('ls {x} > output')
ls.set_inputs(['x'])
#ls.set_outputs(['output', 'RESULT'])
ls.set_outputs(['output'])

if __name__ == '__main__':
    client = XflowClient(local=True)
    testdata = '-a'
    #output, result = client.submit(ls, testdata)
    output = client.submit(ls, testdata)
    #print(result.result())
    output.result().save('ls-result1.log')
    testdata = 'crap'
    #output, result = client.submit(ls, testdata)
    output = client.submit(ls, testdata)
    #print(result.result())
    output.result().save('ls-result2.log')
    client.close()
