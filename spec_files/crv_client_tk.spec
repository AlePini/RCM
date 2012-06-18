# -*- mode: python -*-
import platform
ROOTPATH=os.path.dirname(os.path.dirname(os.path.abspath(HOMEPATH)))
print "---------------->", os.path.abspath(HOMEPATH)
print "---------------->",ROOTPATH
if(sys.platform == 'win32'):
  data_files=[('external/win32/32bit/bin/vncviewer.exe', os.path.join(ROOTPATH,'client','external','win32','32bit','bin','vncviewer.exe'), 'DATA'),('external/win32/32bit/bin/PLINK.EXE', os.path.join(ROOTPATH,'client','external','win32','32bit','bin','PLINK.EXE'), 'DATA')]
else:
  myplatform=platform.architecture()[0]
  print "----",platform
  data_files=[('external/linux2/'+myplatform+'/bin/vncviewer', os.path.join(ROOTPATH,'client','external','linux2',myplatform,'bin','vncviewer'), 'DATA')]
a = Analysis([os.path.join(HOMEPATH,'support','_mountzlib.py'), os.path.join(HOMEPATH,'support','unpackTK.py'), os.path.join(HOMEPATH,'support','useTK.py'), os.path.join(HOMEPATH,'support','useUnicode.py'), os.path.join(ROOTPATH,'client','crv_client_tk.py'), os.path.join(HOMEPATH,'support','removeTK.py')],
             pathex=[os.path.join(ROOTPATH,'python'), os.path.join(ROOTPATH,'pyinstaller-1.5.1')])
pyz = PYZ(a.pure)
exe = EXE(TkPKG(), pyz,
          a.scripts,
          a.binaries+ data_files,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', 'crv_client_tk.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=True )