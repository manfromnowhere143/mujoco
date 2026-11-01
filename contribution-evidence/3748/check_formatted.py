"""Check exact submitted test bytes, while verifying unchanged native libraries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import xml.etree.ElementTree as ET

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--cmake',required=True)
a=p.parse_args();a.source=a.source.resolve();a.work=a.work.resolve();out=a.work/'formatted';out.mkdir(exist_ok=False)
records=[]; targets=['engine_collision_convex_test','engine_collision_gjk_test','engine_collision_driver_test','engine_collision_box_test']
def run(label,command,env=None):
 t=time.monotonic()
 with (out/(label+'.stdout')).open('w') as so,(out/(label+'.stderr')).open('w') as se:
  r=subprocess.run([str(x) for x in command],cwd=a.source/'test',stdout=so,stderr=se,env=env,timeout=180)
 row={'label':label,'command':[str(x) for x in command],'cwd':str(a.source/'test'),'exit_code':r.returncode,'seconds':time.monotonic()-t}
 records.append(row);(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(row),flush=True)
 return r.returncode
summary={}
for precision in ['double','single']:
 build=a.work/('build-'+precision)
 library=build/'lib'/('libmujoco.3.17.1.dylib' if platform.system()=='Darwin' else 'libmujoco.so.3.17.1')
 before=hashlib.sha256(library.read_bytes()).hexdigest()
 assert run(precision+'-build',[a.cmake,'--build',build,'--target',*targets,'-j','2'])==0
 after=hashlib.sha256(library.read_bytes()).hexdigest()
 assert before==after,'Formatting changed native library'
 summary[precision]={'library_sha256':after,'library_unchanged':True,'tests':{}}
 for target in targets:
  label=precision+'-'+target
  run(label,[build/'bin'/target,'--gtest_output=xml:'+str(out/(label+'.xml'))])
  x=ET.parse(out/(label+'.xml')).getroot();summary[precision]['tests'][target]={k:int(x.get(k,0)) for k in ['tests','failures','errors']}
 reference=a.work/'reference'/precision
 if platform.system()=='Darwin':
  env={**os.environ,'DYLD_LIBRARY_PATH':str(reference),'DYLD_PRINT_LIBRARIES':'1'}
 else:
  env={**os.environ,'LD_LIBRARY_PATH':str(reference),'LD_DEBUG':'libs'}
 label=precision+'-canaries'
 assert run(label,[build/'bin'/targets[0],'--gtest_filter=MjcConvexTest.HorizontalCylinderBox*','--gtest_output=xml:'+str(out/(label+'.xml'))],env)==1
 stderr=(out/(label+'.stderr')).read_text(); path=str(reference/library.name)
 loaded=path in stderr if platform.system()=='Darwin' else any('calling init:' in line and path in line for line in stderr.splitlines())
 assert loaded,'Unpatched library load not demonstrated'
 x=ET.parse(out/(label+'.xml')).getroot();assert x.get('tests')=='2' and x.get('failures')=='2' and x.get('errors')=='0'
 summary[precision]['canaries']={'loaded_reference':True,'tests':2,'failures':2,'environment':{k:v for k,v in env.items() if k in ['DYLD_LIBRARY_PATH','DYLD_PRINT_LIBRARIES','LD_LIBRARY_PATH','LD_DEBUG']}}
(out/'completed.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
