#import os.path
import os
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
    myprocess = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr = myprocess.communicate()
    myprocess.wait()                        
    return (myprocess.returncode,stdout,stderr)     
  
def cprex(cmd):
    (r,o,e)=prex(cmd)
    if (r != 0):
      print e
      raise Exception("command {0} failed with error: {1}".format([cmd[0],cmd[-1]],e))
    return (r,o,e)

# submit a PBS job
def submit_job(self,sid,rcm_dirs):
    self.qsub_template="""#!/bin/bash
#PBS -l walltime=$RCM_WALLTIME
#PBS -N $RCM_SESSIONID
#PBS -o $RCM_JOBLOG

##following line is probably needed for a bug in PBS thad slows down the scheduling ... ask Federico
##maybe we can take down Qlist=visual
#PBS -l "$RCM_QUEUEPARAMETER"

#PBS -j oe
#PBS -q $RCM_QUEUE

## to be substituted by the proper account: either specific for the queue if the accounting is disabled or to be
## selected by the user when the accounting will be activated
$RCM_DIRECTIVE_A

##the following line specify the specific group for controlling access to the queue ( not accounting)
##while on testing this is fixed, equal to account group

$RCM_DIRECTIVE_W

. /cineca/prod/environment/module/3.1.6/none/init/bash
module purge
module load profile/advanced
module load TurboVNC
$RCM_CLEANPIDS



$RCM_VNCSERVER -otp -fg -novncauth > $RCM_JOBLOG.vnc 2>&1
"""

    s=string.Template(self.qsub_template)
    otp='%s/%s.otp' % (rcm_dirs[0],sid)
    if(os.path.isfile(otp)):
      os.remove(otp)
    file='%s/%s.job' % (rcm_dirs[0],sid)
    fileout='%s/%s.joblog' % (rcm_dirs[0],sid)

    group = self.getQueueGroup(self.queue) 
      
    #For reserved queue set only "select=1"   
    queueParameter = "select=1"
    if(not self.queue.startswith('R')):
      queueParameter += ":Qlist=" + self.queue + ":viscons=1"
    rcm_directive_A = self.groupSubstitution(group,'#PBS -A $RCM_GROUP')

    #Industrial users do not have to use -W group_list
    if( self.par_u.startswith('a06',0,3) ):
      rcm_directive_W = ''
    else:
      rcm_directive_W = self.groupSubstitution(group,'#PBS -W group_list=$RCM_GROUP')

    batch=s.safe_substitute(RCM_WALLTIME=self.par_w,RCM_SESSIONID=sid,RCM_JOBLOG=fileout,RCM_DIRECTIVE_A=rcm_directive_A,RCM_DIRECTIVE_W=rcm_directive_W,RCM_QUEUE=self.queue,RCM_QUEUEPARAMETER=queueParameter,RCM_VNCSERVER=self.vncserver_string,RCM_CLEANPIDS=self.clean_pids_string)

    f=open(file,'w')
    f.write(batch)
    f.close()
    (res,out,err)=cprex(['qsub','-v',"RCM_OTP_FILE="+otp,file])
    r=re.match(r'(\d+\.\w+)(\.[\w\.]+)?$',out)
    if (r):
      return r.group(1)
    else:
      raise Exception("Unknown qsub output: %s" % (out))


# kill a PBS job
def kill_job(self,jid):
    cprex(['qdel',jid])
    
    
# get available queues for the user
def get_queue(self):
    #get list of possible queue (named "visual")
    queueList = []
    
    p1 = subprocess.Popen(["qstat","-q"], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", "visual"], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    stdout,stderr = p2.communicate() 
    if (p2.returncode != 0) :
      raise Exception( 'qstat returned non zero value: ' + stderr) 
    else:
      row=stdout.split('\n')
      row = filter(None, row)
    for j in row:
      queueList.append(j.split(' ')[0])
      
    #############################
    #check "visual" reserved queue
    p1 = subprocess.Popen(["pbs_rstat","-F"], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", "Name:"], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
     
    stdout,stderr = p2.communicate()
    if (p2.returncode != 0) :
      raise Exception( 'pbs_rstat returned non zero value: ' + stderr) 
    else:
      reservations=stdout.split('\n')
      reservations = filter(None, reservations)
    for i in reservations:
      resId = i.replace('Name: ', '')
      
      p1 = subprocess.Popen(["pbs_rstat","-F", resId], stdout=subprocess.PIPE)
      stdout,stderr = p1.communicate()
      outputLines=stdout.split('\n')

      r = dict()
      r["reserveName"]=["",re.compile('^Reserve_Name = (.*)')]
      r["reserveStart"]=["",re.compile('^reserve_start = (.*)')]
      r["reserveEnd"]=["",re.compile('^reserve_end = (.*)')]
    
      for l in outputLines:
        for n in r.keys():
          m = r[n][1].match(l)
          if m:
            r[n][0] = m.group(1) 
            #print "matched: " + r[n][0]

      starttime=datetime.datetime.strptime(r["reserveStart"][0], "%a %b %d %H:%M:%S %Y")
      endtime=datetime.datetime.strptime(r["reserveEnd"][0], "%a %b %d %H:%M:%S %Y")
      now = datetime.datetime.now()
      if 'visual' in r["reserveName"][0] and now >= starttime and now <= endtime:
          queueList.append(resId.split('.')[0])
     ############################### 
      
    #try to submit in each queue of the list
    queueListcopy = list(queueList);
    for tmpQueue in queueListcopy:
      group = self.getQueueGroup(tmpQueue)
      #For reserved queue set only "select=1"   
      queueParameter = "select=1"
      if(not tmpQueue.startswith('R')):
        queueParameter += ":Qlist=" + tmpQueue + ":viscons=1"
    
      p1 = subprocess.Popen(["qsub", "-l", "walltime=0:00:01", "-l", "select=1", "-q",tmpQueue, "-o","/dev/null", "-e","/dev/null" ] + self.groupSubstitution(group, "-A $RCM_GROUP -W group_list=$RCM_GROUP").split() + [ "--","echo"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      stdout,stderr=p1.communicate() 
      if len(stderr) > 0:
        queueList.remove(tmpQueue)
    return queueList
      
# get running jobs
def get_jobs(self, sessions, U=False,):
    (retval,stdout,stderr)=prex(['qstat'])
    if (retval != 0 ) :
      sys.write.stderr(stderr);
      raise Exception( 'qstat returned non zero value: ' + str(retval) )
    else:
      raw=stdout.split('\n')
      if (U):
        ure='\w+'
      else:
        ure=self.par_u
      #258118.node351    rcm-cin0449a-10  cin0449a          00:00:06 R visual          
#original..single queue      r=re.compile(r'(?P<jid>\d+[\w\.]+) \s+ (?P<sid>rcm-%s-\d+)  \s+ (%s) \s+ \S+ \s+ R \s+ visual  ' % (ure,ure) ,re.VERBOSE)
      r=re.compile(r'(?P<jid>\d+[\w\.]+) \s+ (?P<sid>%s-\S+-\d+)  \s+ (%s) \s+ \S+ \s+ R \s+ ' % (ure,ure) ,re.VERBOSE)
      jobs={}
      for j in raw:
        mo=r.match(j)
        if (mo): 
          sid=mo.group('sid')
          jid=mo.group('jid')
          jobs[sid]=jid
      return(jobs)
