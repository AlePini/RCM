#!/bin/env python

import os
import pwd
import re
import logging
import logging.handlers
#from __future__ import print_function

import rcm


import rcm_protocol_server
import rcm_protocol_parser
import sys
import platformconfig



if __name__ == '__main__':

    # init loggger
    logger_name = 'basic'
    logger = logging.getLogger(logger_name)
    logger.setLevel( os.environ.get("RCM_DEBUG_LEVEL","info").upper())
    ch = logging.StreamHandler(sys.stdout)
    username=pwd.getpwuid(os.geteuid())[0]
    rcmdir=os.path.expanduser("~%s/.rcm" % username)
    if ( not os.path.isdir(rcmdir) ):
        os.mkdir(rcmdir)
        os.chmod(rcmdir,0755)
    rcmlog=os.path.join(rcmdir,'logfile')
    #fh = logging.FileHandler(rcmlog, mode='a')
    fh = logging.handlers.RotatingFileHandler(rcmlog, mode='a', maxBytes=50000, 
                                 backupCount=2, encoding=None, delay=0)
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s (%(module)s:%(lineno)d %(funcName)s) : %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)


    #logger.addHandler(ch)
    logger.addHandler(fh)
    
    num_loglevel_debug=getattr(logging, "debug".upper(), 0)
    if num_loglevel_debug==logger.level:
        string="--------new command-------------\n"
        string+="python->"+sys.executable+"\n"
        string+="script-->"+sys.argv[0]+"\nargs->"
    else:
        string="--->"+__file__+" "
    for a in sys.argv[1:]:
        string+=a+" "
    if num_loglevel_debug==logger.level:
        string+="\n--------------------------------\n"
        logger.debug(string)
    else:
        logger.info(string)

    #launch rcm
    p=platformconfig.platformconfig()
    s=p.get_rcm_server()
    r=rcm_protocol_server.rcm_protocol(s)
    c=rcm_protocol_parser.CommandParser(r)

    c.handle()

