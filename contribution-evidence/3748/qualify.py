"""Bounded current-main qualification; retains every command and failed control."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
p.add_argument('--cmake', required=True)
p.add_argument('--ninja', required=True)
p.add_argument('--compiler', required=True)
p.add_argument('--stage', choices=['reference', 'candidate'], required=True)
a = p.parse_args()
a.source = a.source.resolve(); a.work = a.work.resolve()
packet = Path(__file__).resolve().parent
out = a.work / a.stage; out.mkdir(parents=True, exist_ok=False)
started = time.monotonic(); records = []
targets = ['engine_collision_convex_test', 'engine_collision_gjk_test',
           'engine_collision_driver_test', 'engine_collision_box_test']

def run(label, command, cwd=None, timeout=600, env=None, required=True):
    remaining = 1800 - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError('stage time budget exhausted')
    t = time.monotonic()
    record = {'label': label, 'command': [str(x) for x in command],
              'cwd': str(cwd or a.work), 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'timeout_seconds': min(timeout, remaining), 'status': 'running'}
    records.append(record)
    (out / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
    with (out / (label + '.stdout')).open('w') as stdout, (out / (label + '.stderr')).open('w') as stderr:
        process = subprocess.Popen([str(x) for x in command], cwd=cwd or a.work,
                                   stdout=stdout, stderr=stderr, env=env, start_new_session=True)
        try:
            record['exit_code'] = process.wait(timeout=min(timeout, remaining))
            record['status'] = 'completed'
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL); process.wait()
            record['status'] = 'interrupted_or_timeout'
            raise
        finally:
            record['seconds'] = time.monotonic() - t
            (out / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(record), flush=True)
    if required and record['exit_code']:
        raise RuntimeError(label + ' failed')
    return record['exit_code']

run('compiler', [a.compiler, '--version'])
run('platform', ['uname', '-a'])
for precision in ['double', 'single']:
    build = a.work / ('build-' + precision)
    configure = [a.cmake, '-S', a.source, '-B', build, '-G', 'Ninja',
                 '-DCMAKE_MAKE_PROGRAM=' + a.ninja, '-DCMAKE_BUILD_TYPE=Release',
                 '-DMUJOCO_BUILD_EXAMPLES=OFF', '-DMUJOCO_BUILD_SIMULATE=OFF',
                 '-DMUJOCO_BUILD_STUDIO=OFF', '-DMUJOCO_BUILD_TESTS=ON', '-DMUJOCO_TEST_PYTHON_UTIL=OFF']
    if precision == 'single':
        configure += ['-DCMAKE_C_FLAGS=-DmjUSESINGLE', '-DCMAKE_CXX_FLAGS=-DmjUSESINGLE']
    run(precision + '-configure', configure)
    run(precision + '-build', [a.cmake, '--build', build, '--target', *targets, '-j', '2'], timeout=900)
    shutil.copy2(build / 'CMakeCache.txt', out / (precision + '-CMakeCache.txt'))
    library = build / 'lib' / ('libmujoco.3.17.1.dylib' if platform.system() == 'Darwin' else 'libmujoco.so.3.17.1')
    libdir = out / precision; libdir.mkdir()
    shutil.copy2(library, libdir / library.name)
    (libdir / 'library.sha256').write_text(hashlib.sha256(library.read_bytes()).hexdigest() + '\n')
    for target in targets:
        label = precision + '-' + target
        command = [build / 'bin' / target, '--gtest_output=xml:' + str(out / (label + '.xml'))]
        if a.stage == 'reference':
            command += ['--gtest_filter=-MjcConvexTest.HorizontalCylinderBox*']
        run(label, command, cwd=a.source / 'test', timeout=180, required=False)
    label = precision + '-new-tests'
    run(label, [build / 'bin' / targets[0], '--gtest_filter=MjcConvexTest.HorizontalCylinderBox*',
                '--gtest_output=xml:' + str(out / (label + '.xml'))], cwd=a.source / 'test', timeout=180, required=False)
    if a.stage == 'candidate':
        run(precision + '-calibration', [build / 'bin' / targets[0], '--gtest_filter=MjcConvexTest.HorizontalCylinderBox*'],
            cwd=a.source / 'test', timeout=180, env={**os.environ, 'MJTOL_SCALE': '0'}, required=False)
    if precision == 'double':
        run('compile-probe', [a.compiler, '-std=c++17', '-O2', packet / 'native_probe.cc', '-I', a.source / 'include',
                             libdir / library.name, '-Wl,-rpath,' + str(libdir), '-o', libdir / 'probe'])
        for name, xml in [('original', 'reported.xml'), ('exposed', 'confirmation.xml'),
                          ('fresh', 'support-line-confirmation.xml'), ('plane', 'plane.xml')]:
            run('trace-' + name, [libdir / 'probe', packet / xml, '60'], timeout=180)
summary = {}
for f in out.glob('*.xml'):
    root = ET.parse(f).getroot()
    summary[f.stem] = {key: int(root.get(key, 0)) for key in ['tests', 'failures', 'errors', 'disabled']}
(out / 'completed.json').write_text(json.dumps({'stage': a.stage, 'seconds': time.monotonic() - started,
                                              'test_summary': summary, 'status': 'completed'}, indent=2) + '\n')
print(json.dumps({'status': 'completed', 'seconds': time.monotonic() - started, 'tests': summary}), flush=True)
