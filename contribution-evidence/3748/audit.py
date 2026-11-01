"""Reconstruct current-main comparison from retained traces and test reports."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('records', type=Path)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()

def read(path):
    if path.exists():
        return path.read_bytes()
    return gzip.decompress(Path(str(path) + '.gz').read_bytes())

results = {}; tests = {}; checks = {}
for arm in ['reference', 'candidate']:
    for name, xy in [('original', (0, 0)), ('exposed', (.006, -.004)),
                     ('fresh', (.009, .006)), ('plane', (0, 0))]:
        raw = read(a.records / arm / ('trace-' + name + '.stdout'))
        lines = raw.decode().splitlines()
        assert lines[0].startswith('# version=3.17.1 '), 'Unexpected native version'
        rows = list(csv.DictReader(lines[1:]))
        assert len(rows) == 30000, 'Incomplete trace'
        peak = 0; late = []; zmin = math.inf; leave = None
        for i, row in enumerate(rows):
            values = {k: float(v) for k, v in row.items()}
            assert all(math.isfinite(values[k]) for k in ['time','x','y','z','qw','qx','qy','qz','vx','vy','vz','wx','wy','wz']), 'Non-finite state'
            assert abs(values['time'] - (i + 1) * .002) < 1e-8, 'Incorrect clock'
            peak = max(peak, math.hypot(values['x'] - xy[0], values['y'] - xy[1]) * 1000)
            zmin = min(zmin, values['z'])
            if values['z'] < .02 and leave is None:
                leave = values['time']
            if values['time'] >= 30:
                late.append(math.hypot(values['vx'], values['vy']) * 1000)
        results[arm + '-' + name] = {'rows': len(rows), 'peak_horizontal_mm': peak,
            'late_mean_horizontal_speed_mm_s': math.fsum(late) / len(late), 'minimum_center_z_m': zmin,
            'first_center_below_platform_top_s': leave, 'uncompressed_sha256': hashlib.sha256(raw).hexdigest()}
    for precision in ['double', 'single']:
        counts = {}
        for target in ['convex', 'gjk', 'driver', 'box']:
            f = a.records / arm / (precision + '-engine_collision_' + target + '_test.xml')
            root = ET.fromstring(read(f))
            counts[target] = {k: int(root.get(k, 0)) for k in ['tests', 'failures', 'errors', 'disabled']}
        tests[arm + '-' + precision] = counts
        checks[arm + '-' + precision + '-existing-or-complete-tests'] = all(x['failures'] == x['errors'] == 0 and x['tests'] > 0 for x in counts.values())
        root = ET.fromstring(read(a.records / arm / (precision + '-new-tests.xml')))
        tests[arm + '-' + precision + '-new-tests'] = {k: int(root.get(k, 0)) for k in ['tests', 'failures', 'errors']}
        checks[arm + '-' + precision + '-new-tests'] = int(root.get('tests')) == 2 and int(root.get('failures')) == (2 if arm == 'reference' else 0) and int(root.get('errors')) == 0
checks['candidate-panel-bound'] = all(r['peak_horizontal_mm'] < .1 and r['minimum_center_z_m'] >= .02 for k, r in results.items() if k.startswith('candidate-'))
before = results['reference-fresh']['peak_horizontal_mm']; after = results['candidate-fresh']['peak_horizontal_mm']
checks['retained-17-degree-criterion'] = before >= 1 and after < .01 * before
checks['plane-full-trace-identical'] = results['reference-plane']['uncompressed_sha256'] == results['candidate-plane']['uncompressed_sha256']
result = {'scope': 'Exact-current-main revision qualification on already exposed cases, not new incidents or owner application validation.',
          'trajectory_results': results, 'test_results': tests, 'checks': checks, 'all_checks_pass': all(checks.values())}
a.out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['all_checks_pass'] else 1)
