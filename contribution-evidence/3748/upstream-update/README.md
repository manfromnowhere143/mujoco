# Latest-main qualification: 58425011

The unchanged correction passes its bounded CPU qualification against upstream
`58425011e15fc26870272ec46e8586c210078471`. The submitted code head is
`cca77a24b381edeec2baea7b148c7a08cceb142f`. Only the 19-line production correction
and two regression tests differ from that base. The complete patch has SHA-256
`7b9d47d8ae8b93ece35fb061d512ced80bb281dbbe201656125948294ae529dd`.

Upstream advanced while publication was being prepared. The intervening tree
change fixes the BVH descent heuristic and adds a collision-driver test, so the
comparison was re-executed on both platforms. The correction, cases, durations,
precision tolerances and acceptance criteria were unchanged. The source and
resource contract were frozen before that execution in
[`upstream-update-freeze.json`](../upstream-update-freeze.json).

| Platform | Precision | Corrected targeted tests | New tests without correction |
|---|---|---:|---:|
| macOS ARM64, Apple clang 15 | Double | 127/127 pass | 2/2 fail |
| macOS ARM64, Apple clang 15 | Single | 122/127 pass | 2/2 fail |
| Linux ARM64, GCC 12 | Double | 127/127 pass | 2/2 fail |
| Linux ARM64, GCC 12 | Single | 127/127 pass | 2/2 fail |

The five macOS single-precision failures are unchanged in name and message
between reference and candidate: `BoxBoxDepth2`, `BoxBoxDepth3`,
`BoxBoxMultiCCD12`, `EllipsoidEllipsoidSlowConvergence` and
`BoxBoxMarginDeepMultiCCD`. The complete macOS single-precision suite is not green.
The new regressions pass with the correction in every listed configuration.

Each platform also re-executed eight default-double trajectories: reference and
correction on the reported model, the exposed 30-degree case, the previously
reserved 17-degree case and a plane control, for 60 simulated seconds each.
All three corrected box cases remain supported and below 0.000001 mm maximum
horizontal displacement; the acceptance bound is 0.1 mm. Each plane-control
trace is byte-identical before/after. Near-zero numerical residuals are not a
claim of physical measurement accuracy. The unpatched Linux original leaves the
platform at 42.878 s; its later free-flight displacement is not resting creep.

The [macOS audit](macos-audit.json), [Linux audit](linux-audit.json) and
[test/failure comparison](summary.json) reconstruct these outcomes. Command
logs, test XML and complete compressed trajectories are under `macos/` and
`linux/`, with per-arm file manifests. The audit deliberately returns nonzero
for the known macOS failures rather than suppressing them. The collection check
separately requires those failure messages to match the reference exactly.

Use the [reproduction commands](../REPRODUCE.md) with the exact base above.
The replay audit can also run without simulation:

```sh
python3 ../audit.py linux --out /tmp/mujoco3748-linux-audit.json
python3 ../audit.py macos --out /tmp/mujoco3748-macos-audit.json
```

The second command exits nonzero for the five disclosed baseline failures.
The current Linux execution took 624.60 seconds including setup and cleanup,
using two CPU cores and 4 GiB. Its container is removed. macOS reference and
candidate stages took 72.63 and 74.30 seconds. No paid compute was used. Full
human effort, application review effort and savings were not measured.

**SUPPORTED:** this correction on these source identities and CPU cases.
**Pending external evidence:** maintainer acceptance, the reporter's unchanged
rest detector in its full bin scene, and broader compatibility. The cases are
already exposed diagnostic conditions, not fresh independent owner incidents.
