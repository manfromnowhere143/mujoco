"""Qualify the newly advanced upstream main with the same experiment contract."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

p=Path('/packet');w=Path('/work');records=[]
def run(label,command,cwd=w,timeout=180):
 t=time.monotonic()
 with (w/('update-'+label+'.stdout')).open('w') as out,(w/('update-'+label+'.stderr')).open('w') as err:
  r=subprocess.run(command,cwd=cwd,stdout=out,stderr=err,timeout=timeout)
 records.append({'label':label,'command':command,'cwd':str(cwd),'exit_code':r.returncode,'seconds':time.monotonic()-t})
 (w/'update-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps(records[-1]),flush=True)
 if r.returncode:raise RuntimeError(label+' failed')
freeze=json.loads((p/'upstream-update-freeze.json').read_text())
assert hashlib.sha256((w/'updated-source.tar.gz').read_bytes()).hexdigest()==freeze['source_archive_sha256']
run('apt-update',['apt-get','update'])
run('git-install',['apt-get','install','-y','--no-install-recommends','git'])
run('tools-env',['uv','venv','--python','3.12','/tmp/mj-main-tools'])
run('tools-install',['uv','pip','sync','--python','/tmp/mj-main-tools/bin/python','--require-hashes',str(p/'build-requirements.lock')])
run('extract',['tar','-xzf',str(w/'updated-source.tar.gz'),'-C',str(w/'source')])
for f,digest in freeze['files'].items():
 assert hashlib.sha256((w/'source'/f).read_bytes()).hexdigest()==digest
run('uncorrected',['git','apply','--reverse',str(p/'production.patch')],cwd=w/'source')
common=['python',str(p/'qualify_update.py'),'--source',str(w/'source'),'--work',str(w/'qualification'),'--cmake','/tmp/mj-main-tools/bin/cmake','--ninja','/tmp/mj-main-tools/bin/ninja','--compiler','g++']
run('reference',common+['--stage','reference'],timeout=360)
run('correction',['git','apply',str(p/'production.patch')],cwd=w/'source')
for f,digest in freeze['files'].items():
 assert hashlib.sha256((w/'source'/f).read_bytes()).hexdigest()==digest
run('candidate',common+['--stage','candidate'],timeout=360)
