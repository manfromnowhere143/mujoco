"""Qualify the exact submitted patch in a resource-bounded local Linux container."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile
import time

p = Path('/packet'); w = Path('/work'); start = time.monotonic(); records = []

def run(label, command, cwd=w, timeout=1200):
    remaining = 1740 - (time.monotonic() - start)
    if remaining <= 0:
        raise TimeoutError('Linux budget exhausted')
    t = time.monotonic()
    with (w / (label + '.stdout')).open('w') as out, (w / (label + '.stderr')).open('w') as err:
        result = subprocess.run(command, cwd=cwd, stdout=out, stderr=err, timeout=min(timeout, remaining))
    row = {'label': label, 'command': [str(x) for x in command], 'cwd': str(cwd),
           'exit_code': result.returncode, 'seconds': time.monotonic() - t}
    records.append(row); (w / 'outer-commands.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(row), flush=True)
    if result.returncode:
        raise RuntimeError(label + ' failed')

run('apt-update', ['apt-get', 'update'], timeout=180)
run('git-install', ['apt-get', 'install', '-y', '--no-install-recommends', 'git'], timeout=180)
run('tools-env', ['uv', 'venv', '--python', '3.12', '/tmp/mj-main-tools'], timeout=180)
run('tools-install', ['uv', 'pip', 'sync', '--python', '/tmp/mj-main-tools/bin/python', '--require-hashes', str(p / 'build-requirements.lock')], timeout=180)
source = w / 'source'; source.mkdir()
with tarfile.open(w / 'source.tar.gz') as archive:
    archive.extractall(source, filter='data')
run('apply-tests', ['git', 'apply', str(p / 'tests-final.patch')], cwd=source)
command = ['python', str(p / 'qualify.py'), '--source', str(source), '--work', str(w / 'qualification'),
           '--cmake', '/tmp/mj-main-tools/bin/cmake', '--ninja', '/tmp/mj-main-tools/bin/ninja', '--compiler', 'g++']
run('reference', command + ['--stage', 'reference'])
run('apply-production', ['git', 'apply', str(p / 'production.patch')], cwd=source)
run('candidate', command + ['--stage', 'candidate'])
run('packages', ['dpkg-query', '-W'], timeout=30)
(w / 'complete.json').write_text(json.dumps({'seconds': time.monotonic()-start, 'status': 'completed',
    'source_archive_sha256': hashlib.sha256((w / 'source.tar.gz').read_bytes()).hexdigest(),
    'patch_sha256': hashlib.sha256((p / 'submission-final.patch').read_bytes()).hexdigest()}, indent=2) + '\n')
