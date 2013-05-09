#import os.path
import os, stat
import subprocess
import re
import glob
import string
import time
import datetime


# get group to be used submitting a job
def getQueueGroup(self,queue):
    if len(self.accountList) == 0:
      return ''
    else:
      #cineca deployment dependencies
      if( 'cin' in self.par_u):
        group="cinstaff"
      else:
        group="cin_visual"
      return group

def prex(cmd):
    cmdstring=cmd[0]
    for p in cmd[1:]:
      cmdstring+=" '%s'" % (p) 
    #sys.stderr.write("Executing: %s\n" % (cmdstring)  )
    print cmdstring
    myprocess = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    stdout,stderr = myprocess.communicate()
    myprocess.wait()
    print stdout
    return (myprocess.returncode,stdout,stderr)
  
def cprex(cmd):
    (r,o,e)=prex(cmd)
    if (r != 0):
      print e
      raise Exception("command {0} failed with error: {1}".format([cmd[0],cmd[-1]],e))
    return (r,o,e)

# submit a LL job
# stdout and stderr are separated in 2 files
def submit_job(self,sid,rcm_dirs):
    #cineca deployment dependencies
    self.ssh_template="""
#!/bin/bash

. /cineca/prod/environment/module/3.1.6/none/init/bash
module purge
module load turbovnc

$RCM_CLEANPIDS

$RCM_VNCSERVER -otp -novncauth > $RCM_JOBLOG.vnc 2>&1
cat `ls -tr ~/.vnc/*.pid | tail -1`
"""

    s=string.Template(self.ssh_template)
    print s
    otp='%s/%s.otp' % (rcm_dirs[0],sid)
    if(os.path.isfile(otp)):
      os.remove(otp)
    file='%s/%s.job' % (rcm_dirs[0],sid)
    fileout='%s/%s.joblog' % (rcm_dirs[0],sid)
      
    batch=s.safe_substitute(RCM_JOBLOG=fileout,RCM_VNCSERVER=self.vncserver_string,RCM_CLEANPIDS=self.clean_pids_string)

    
    f=open(file,'w')
    f.write(batch)
    f.close()
    os.chmod(file, stat.S_IRWXU)
    (res,out,err)=cprex([file])
    
    if (res != 0 ) :
      sys.write.stderr(err);
      raise Exception( 'Creation of remote display failed: ' + str(err) )
    else:
      return out.rstrip() #out is the pid of Xvnc


# kill a PBS job
def kill_job(self,jid):
    #cprex(['qdel',jid])
    #cprex(['kill '+ jid])
    try:
      os.kill(int(jid), 9)
    except:
      raise Exception("Can not kill Xvnc process with pid: {0}. {1}".format(jid, err))
    
    
# get available queues for the user (ssh in no job scheduler)
def get_queue(self):
    queueList = []
    queueList.append("ssh")
    return queueList
      
# get running jobs
def get_jobs(self, sessions, U=False):
    #(retval,stdout,stderr)=prex(['llq'])
    #get list of jobs: blank-delimited list of categories (job name, class, owner)
    pidList = []
    
    p1 = subprocess.Popen(["ps","-u",self.par_u], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr = p1.communicate()
    row=stdout.split('\n')
    row = filter(None, row)
    for j in row:
      if "Xvnc" in j:
        pidList.append(j.lstrip().split(' ')[0]) #get list of pid

    jobs={} 
    for sid, ses in self.sessions.items():
      file_jid=ses.hash['jobid']
      if file_jid in pidList:
        jobs[sid]=file_jid #check if jobid in session file is a running pid
    print jobs
    return (jobs)