# MuJoCo cylinder/box support recovery: current-main qualification

The correction reconstructs a zero-margin cylinder's side-contact segment from
the selected flat-face normal before the existing clipping operation. It addresses
[MuJoCo #3748](https://github.com/google-deepmind/mujoco/issues/3748), where a cylinder
resting on a box moves without an applied horizontal force. No solver setting,
friction coefficient, timestep or released default is changed.

The base is `0f1092ebb6a3247e10ed85bf72ffc3a52415f70a`, verified current main at
intake and checked again before publication. The submitted source is
`8d2b7d1798b58b8294223ae37b08862d562d2061`. Its two commits contain 19 added
production lines and two regression tests; the second commit only applies the
project's C++ formatting. `submission-source.json` binds both files and the
complete patch. This correction does not depend on PR #3743.

## Mechanism and tests

For cylinder axis `u`, center `c`, radius `r`, half-length `h` and selected
opposing face normal `n`, reconstruct the segment as
`c - r*v +/- h*u`, where `v = normalize(n - u*(u dot n))`. The existing edge/face
alignment test selects the feature before this reconstruction. The positive-margin
path is retained. This is standard support geometry, not a claimed new algorithm.
The intervention changes recovered position, depth and endpoint ordering together;
their individual contributions to the dynamic result have not been separated.

The static regression checks transverse support-line error, penetration and
normal at five yaw angles. It also calls the collider with both argument orders
directly: changing XML order alone does not establish which order the collision
driver executes. The second regression runs the reported resting case for
2,500 steps. Both tests fail on the uncorrected library in both precisions.

## Results

Default double precision, 60 simulated seconds per trajectory, 2 ms timestep.
All rows use the same correction and criteria. Maximum horizontal displacement
is computed at every step, not just at the reporter's one-second sampling points.

| Case | macOS reference | Linux reference | Corrected, either platform |
|---|---:|---:|---:|
| Reported cylinder | 53.1456 mm | Leaves platform; center crosses below its top at 42.878 s | < 0.000001 mm, supported |
| Exposed 30-degree case | 4.7988 mm | 4.7974 mm | < 0.000001 mm, supported |
| Previously reserved 17-degree case | 5.9097 mm | 5.9097 mm | < 0.000001 mm, supported |
| Plane control | Numerically at rest | Numerically at rest | Full trace byte-identical to its platform reference |

The large late displacement of the unpatched Linux original occurs after it
leaves the finite platform. It must not be treated as ordinary creep or used to
inflate an improvement ratio. Numerical near-zero residuals are not physical
calibration accuracy.

The correction satisfies the frozen diagnostic bounds: finite state, continued
support and maximum displacement below 0.1 mm; the 17-degree case also improves
by more than 100x relative to a reference exceeding 1 mm. That case was untouched
before the original candidate study, but was already exposed before this
current-main qualification. These are four diagnostic configurations and two
software platforms, not independent application incidents.

| Platform | Precision | Targeted suite with correction | Uncorrected new regressions |
|---|---|---:|---:|
| macOS ARM64 | Double | 126/126 pass | 2/2 fail as intended |
| macOS ARM64 | Single | 121/126 pass; five unchanged baseline failures | 2/2 fail as intended |
| Linux ARM64 | Double | 126/126 pass | 2/2 fail as intended |
| Linux ARM64 | Single | 126/126 pass | 2/2 fail as intended |

macOS uses Apple clang 15; Linux uses GCC 12 in a local ARM64 Docker container.
Both execute on ARM64. The four suites are convex collision, GJK, collision
driver and box collision. The five existing macOS single-precision failures are
`BoxBoxDepth2`, `BoxBoxDepth3`, `BoxBoxMultiCCD12`,
`EllipsoidEllipsoidSlowConvergence` and `BoxBoxMarginDeepMultiCCD`. The before/after
failure messages are identical. They are not suppressed, repaired here or
reported as passing. Linux's uncorrected existing single-precision suite passes.

Single-precision coverage consists of the targeted suites, including the
five-second resting regression; the separate 60-second trajectory panel uses
double precision. `MJTOL_SCALE=0` calibration and exact-library adverse controls
are retained. The formatting follow-through rechecks all four executables and
requires the native library hash to remain unchanged before reusing trajectories.

## Reproduction and retained evidence

[Reproduction commands](REPRODUCE.md) build the reference and correction from
public source, using the included native recorder and four XMLs. The
[macOS audit](macos-audit.json), [Linux audit](linux-audit.json), command records, test XML, complete
compressed trajectories and file hashes permit read-only reconstruction.
`audit.py` reports a nonzero exit if a complete suite is not green, including
the known macOS single-precision failures. Command completion is not a passing
scientific verdict.

The earlier `support-line-current-main.patch` export contained only the tests,
contrary to the handoff's combined-patch implication. That packaging error was
caught before publication. Its historical records remain unchanged; this packet
binds and executes the complete production-and-test patch. Initial tests, later
argument-order coverage, calibration failures and formatting attempts are retained
separately. This does not invalidate the earlier complete-patch macOS/Linux runs.

All execution uses local CPU resources with two build jobs. The Linux container
has a 4 GiB memory limit and an independent timeout/cleanup path. No paid GPU,
cloud or model API calls are used. Command wall times are recorded; complete
human engineering effort and owner savings have not been measured.

## Scope and next decision

**SUPPORTED:** this bounded source correction on the recorded models, source
revision and configurations. The full macOS single-precision suite remains
non-green for the five unchanged baseline failures.

**BLOCKED on external evidence:** maintainer acceptance and the reporter's full
bin scene with the original rest-detector threshold and duration. Linux x86_64,
Windows, actual robots and broader task transfer have not been qualified here.

This is an agent-directed native investigation retained by Nisayon, not a new
autonomous SDK capability or evidence of competitive superiority. The useful next
result is whether the unchanged application detector now reaches a correct
landing decision without introducing contact regressions. A passing minimal
example alone cannot answer that question.
