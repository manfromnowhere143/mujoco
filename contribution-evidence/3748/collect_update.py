"""Retain and audit the unchanged experiment after upstream main advanced."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

p=Path(__file__).resolve().parent
root=Path('artifacts/mujoco3748').resolve()
out=p/'upstream-update';out.mkdir(exist_ok=False)
def read(path):
 return path.read_bytes() if path.exists() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
def failures(folder,precision):
 result={}
 for name in ['convex','gjk','driver','box']:
  x=ET.fromstring(read(folder/(precision+'-engine_collision_'+name+'_test.xml')))
  for case in x.iter('testcase'):
   fs=case.findall('failure')
   if fs:result[case.attrib['classname']+'.'+case.attrib['name']]=[e.attrib.get('message') for e in fs]
 return result
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':json.loads((p/'upstream-update-freeze.json').read_text()),'platforms':{}}
for platform,work in [('macos',root/'current-main-macos'),('linux',root/'current-main-linux'/'qualification')]:
 target=out/platform
 for arm in ['reference','candidate']:
  subprocess.run([sys.executable,str(p/'retain.py'),str(work/('updated-'+arm)),str(target/arm)],check=True)
 audit_file=out/(platform+'-audit.json')
 with (out/(platform+'-audit.stdout')).open('w') as log:
  result=subprocess.run([sys.executable,str(p/'audit.py'),str(target),'--out',str(audit_file)],stdout=log,check=False)
 audit=json.loads(audit_file.read_text());record={'audit_exit_code':result.returncode,'precisions':{},'checks':audit['checks']}
 for precision in ['double','single']:
  before=failures(target/'reference',precision);after=failures(target/'candidate',precision)
  counts=audit['test_results']['candidate-'+precision]
  record['precisions'][precision]={'tests':sum(v['tests'] for v in counts.values()),'failures':sum(v['failures'] for v in counts.values()),'failure_messages_identical_to_reference':before==after,'failures_by_name':after}
 summary['platforms'][platform]=record
summary['linux_cleanup']=json.loads((p/'linux-update-launch.json').read_text())
summary['verdict']='SUPPORTED only for the bounded CPU correction if the recorded gates pass; no owner application or independent review result.'
summary['paid_compute_usd']=0
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='source'},indent=2))
for platform,record in summary['platforms'].items():
 for key,value in record['checks'].items():
  if platform=='macos' and key in ['reference-single-existing-or-complete-tests','candidate-single-existing-or-complete-tests']:continue
  assert value,(platform,key)
 for precision,counts in record['precisions'].items():
  assert counts['tests']==127
  assert counts['failure_messages_identical_to_reference']
  assert counts['failures']==(5 if platform=='macos' and precision=='single' else 0)
assert summary['linux_cleanup']['remaining_container_ids']==[]
