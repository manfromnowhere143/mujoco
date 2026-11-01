"""Rebuild/retest final formatting without changing the retained trajectory library."""
from pathlib import Path
import json
import subprocess
import time

p=Path('/packet');w=Path('/work');records=[]
def run(label,command,cwd=w,timeout=180):
 t=time.monotonic()
 with (w/('format-'+label+'.stdout')).open('w') as out,(w/('format-'+label+'.stderr')).open('w') as err:
  r=subprocess.run(command,cwd=cwd,stdout=out,stderr=err,timeout=timeout)
 records.append({'label':label,'command':command,'cwd':str(cwd),'exit_code':r.returncode,'seconds':time.monotonic()-t})
 (w/'format-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps(records[-1]),flush=True)
 if r.returncode:raise RuntimeError(label+' failed')
run('apt-update',['apt-get','update'])
run('git-install',['apt-get','install','-y','--no-install-recommends','git'])
run('tools-env',['uv','venv','--python','3.12','/tmp/mj-main-tools'])
run('tools-install',['uv','pip','sync','--python','/tmp/mj-main-tools/bin/python','--require-hashes',str(p/'build-requirements.lock')])
run('apply',['git','apply',str(p/'format-only.patch')],cwd=w/'source')
run('check',['python',str(p/'check_formatted.py'),'--source',str(w/'source'),'--work',str(w/'qualification'),'--cmake','/tmp/mj-main-tools/bin/cmake'],timeout=240)
