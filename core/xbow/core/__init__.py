import os
XBOW_CONFIGDIR = os.getenv('XBOW_CONFIGDIR', 
                           os.path.join(os.getenv('HOME'), '.xbow'))
XBOW_CONFIGFILE = os.path.join(XBOW_CONFIGDIR, 'xbow.cfg')
