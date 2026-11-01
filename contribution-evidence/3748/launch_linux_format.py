"""Local CPU container with internal deadline and unconditional scoped cleanup."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import time

p = Path(__file__).resolve().parent
w = Path('artifacts/mujoco3748/current-main-linux').resolve()
docker = '/Applications/Docker.app/Contents/Resources/bin/docker'
name = 'nisayon-mujoco3748-format-20261101'
image = 'sha256:33995abe6d5c9739bc6ddafc5a230c473b5a6df06e23e9b52f343d657316450f'
command = [docker, 'run', '--pull=never', '--rm', '--name', name, '--cpus', '2', '--memory', '4g',
           '--pids-limit', '256', '--security-opt', 'no-new-privileges',
           '--mount', 'type=bind,src='+str(p)+',dst=/packet,readonly',
           '--mount', 'type=bind,src='+str(w)+',dst=/work', '--entrypoint', 'timeout', image,
           '360', 'python', '/packet/linux_format.py']
record = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': command,
          'source_archive_sha256': hashlib.sha256((w / 'source.tar.gz').read_bytes()).hexdigest(),
          'status': 'running'}
(p / 'linux-format-launch.json').write_text(json.dumps(record, indent=2)+'\n')
start = time.monotonic()
try:
    result = subprocess.run(command, timeout=390)
    record.update(status='completed' if result.returncode == 0 else 'failed', exit_code=result.returncode)
except BaseException as error:
    record.update(status='interrupted_or_timeout', exception=type(error).__name__)
    raise
finally:
    subprocess.run([docker, 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    check = subprocess.run([docker, 'ps', '-aq', '--filter', 'name=^/'+name+'$'], capture_output=True, text=True, timeout=30)
    record.update(seconds=time.monotonic()-start, remaining_container_ids=check.stdout.splitlines(), cleanup_check_exit=check.returncode)
    (p / 'linux-format-launch.json').write_text(json.dumps(record, indent=2)+'\n')
raise SystemExit(result.returncode)
