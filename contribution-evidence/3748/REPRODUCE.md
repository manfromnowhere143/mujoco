# Reproduce the cylinder support-segment correction

Base: `0f1092ebb6a3247e10ed85bf72ffc3a52415f70a`.
Correction: `8d2b7d1798b58b8294223ae37b08862d562d2061`.

Use a new scratch directory. These commands do not reset an existing checkout.
CMake 4.1.2 and Ninja 1.13.0 are pinned in `build-requirements.lock`.
Run the commands below from this evidence directory.
The native recorder calls the source-built C API, avoiding a Python/native ABI mismatch.

```sh
MUJOCO3748_PACKET="$PWD"
uv venv --python 3.12 /tmp/mujoco3748-tools
uv pip sync --python /tmp/mujoco3748-tools/bin/python --require-hashes "$MUJOCO3748_PACKET/build-requirements.lock"
git clone --filter=blob:none --no-checkout https://github.com/google-deepmind/mujoco.git /tmp/mujoco3748-main
git -C /tmp/mujoco3748-main checkout --detach 0f1092ebb6a3247e10ed85bf72ffc3a52415f70a
git -C /tmp/mujoco3748-main apply "$MUJOCO3748_PACKET/tests-formatted.patch"
python3 "$MUJOCO3748_PACKET/qualify.py" --source /tmp/mujoco3748-main --work /tmp/mujoco3748-records \
  --cmake /tmp/mujoco3748-tools/bin/cmake --ninja /tmp/mujoco3748-tools/bin/ninja \
  --compiler clang++ --stage reference
git -C /tmp/mujoco3748-main apply "$MUJOCO3748_PACKET/production.patch"
python3 "$MUJOCO3748_PACKET/qualify.py" --source /tmp/mujoco3748-main --work /tmp/mujoco3748-records \
  --cmake /tmp/mujoco3748-tools/bin/cmake --ninja /tmp/mujoco3748-tools/bin/ninja \
  --compiler clang++ --stage candidate
python3 "$MUJOCO3748_PACKET/audit.py" /tmp/mujoco3748-records --out /tmp/mujoco3748-audit.json
```

On Linux use `--compiler g++`. The script builds both precisions using two jobs,
runs the four targeted executables, retains command records and runs the eight
60-second double-precision trajectories. It limits each stage to 30 minutes;
individual tests and trajectories have 180-second deadlines. Every output directory
must be new. Compiled binaries and dependency downloads are not part of the
portable evidence package.

`qualify.py` completion means command collection completed; it deliberately retains
nonzero test results. Inspect `completed.json` and the XML reports. The two new
regressions must fail without the production patch and pass with it. Calibration
runs with `MJTOL_SCALE=0` are expected to fail while exposing numerical residuals.

The macOS first reference run uses the initial two tests. Its separately retained
`final-canaries/` runs the final expanded tests against the archived unpatched
library, with `DYLD_PRINT_LIBRARIES` verifying which library was loaded. The Linux
reference and candidate both use the final test patch directly.

`audit.py` also audits already retained `macos/` or `linux/` records without
executing simulator code. It returns nonzero when any complete test suite is not
green. Five existing single-precision GJK failures were observed before the patch;
they are reported rather than suppressed. Compare baseline/candidate failure
messages and consult the accompanying failure-comparison records before attributing
a failure to the correction.

The 17-degree XML was reserved before the original study's first candidate run.
It is already exposed here. Repeating it on a newer revision or platform is
compatibility qualification, not a new independent confirmation incident.
