# Post-integration QA — Player Comparison Lab

Audit date: 2 November 2026. Baseline: `76a29063bb854552745f58298d0a6ac8dd65a1c4`.
Target: `dev-phase1-ui`. Unchanged production reference:
`85e0b5f3c34dd18d15447a96e229c0e37e7047da`.

**Decision:** suitable for a supervised local capstone demonstration after the
corrections below. A hosted production release is **NOT VERIFIED**. The default
whole-repository test run remains **FAIL** because twelve production-UI tests are
being run against a different development application. No tests were removed,
skipped, relabelled or weakened to hide that fact.

## Quality gates

| Gate | Result | Evidence / remaining action |
| --- | --- | --- |
| Clean installation and local startup | PASS | New Python 3.12 venv without system packages, fresh checkout/worktree, no secrets; requirements install and `pip check` pass. Home and all six pages open. |
| First-run conversion and cache reuse | PASS | No Parquet existed in the measured clean worktree. Four tables converted with all rows preserved, then reused. Invalid manifests rebuild. |
| Cached data integrity | PASS | Reused engines reject changed Parquet bytes and recover through a verified rebuild. Checks occur before and after query use. |
| Cricket arithmetic and historical cutoff | PASS | Original 38 engine tests plus new defect regressions pass. Exclusive cutoff, phase bands, extras, dismissals and super-over exclusion remain enforced. |
| Independent scorecard sample | PASS | 144 field comparisons across 36 player/discipline records in six real matches agree. One external rate-display rounding difference is separately recorded. This is a sample, not whole-archive certification. |
| Existing workspaces and specialist isolation | PASS | All five original pages remain accessible; four specialist evidence packets are identical before/after Lab filter changes. Existing provider-boundary tests pass with mocks. |
| Desktop/mobile and exports | PASS | Browser layouts at widths 1440 and 390; search, real duplicate names, mobile controls and downloads checked. No page exceptions or page-level horizontal overflow. |
| Local single-user query responsiveness | PASS | Measured median about 0.097 s, p95 about 0.144 s over 20 queries; warm whole-Lab rerun about 1.0 s. No hosted SLA is inferred. |
| Small-host memory capacity | NOT VERIFIED | Clean-process peak about 694 MiB; see actual server measurement in `qa/server_memory.json`. Host limits and multi-user headroom must be checked before launch. |
| Unrestricted repository CI | FAIL | 204 passed, twelve failures remain; the exact same twelve failed before corrections and pass on the unchanged production reference. |
| Live Streamlit Cloud operation | NOT VERIFIED | The reported development URL could not be opened by the available remote web reader. No authenticated Streamlit browser/session or cloud logs were available. Local checks do not establish hosted health. |
| Live DeepSeek health/report quality | NOT VERIFIED | No paid/live calls were made. Existing request, parser, citation and error tests use mocked responses. |
| Sustained multi-user load | NOT VERIFIED | Per-query connections and concurrent-query tests pass; no sustained hosted multi-user load test was performed. |

Machine-readable results: [test outcomes](qa/test_results.json),
[environment](qa/environment.json), [performance](qa/performance.json),
[browser checks](qa/browser_results.json) and [quality gates](qa/quality_gates.json).

## Corrections and proof

1. **Manifest validation:** a syntactically valid JSON array/string could raise an
   uncaught AttributeError. Missing warning metadata could be accepted and fail
   later; mismatched source hashes were not rejected. The cache now validates
   root/nested structure, converter/source identity, row metadata, warning types
   and Parquet hashes before reuse. Invalid metadata is rebuilt from the source.
2. **Changed Parquet under a cached engine:** an engine already retained by
   Streamlit could read modified data without checking it again. File metadata
   changes now trigger checksum verification against the validated manifest. An
   integrity change is rejected with a rebuild instruction, rather than returning
   unvalidated values. Checks are before/after query use; immutable input sources
   and original CSVs are untouched.
3. **Incomplete exports:** the batting series omitted a non-striker dismissed
   before facing a ball. It now includes that player with zero batting exposure
   and the correct dismissal count. Batting dismissals and bowling wicket credits
   are exported and reconcile to summaries; wicket joins do not multiply runs.
   Real archive examples include PP Ojha, match `335986`, and A Nel, `336032`,
   both run out without a striker event. These archive examples are source
   reconciliation, not additional external scorecard certification.
4. **Unnecessary query materialization:** statistics previously materialized full
   rows for every player in the date range. The temporary statistics table now
   projects only needed fields and filters selected actors early. Evidence keeps
   all original columns but filters actors before materialization. Non-striker
   dismissals remain included. All external and manual fixtures still pass.

`tests/test_post_integration_qa.py` reproduced seven failures on the audited commit
before the fixes (one additional malformed-table case already passed). All eight
regression cases pass after correction. Metrics/export version is now
`comparison-metrics-1.0.1`. Agent prompts, authentication, evidence schemas,
Moneyball, legacy loaders, source CSVs and `main` were not changed.

## Independent cricket verification

Expected values were manually transcribed from external scorecards, not generated
from the Cricsheet archive. Each match has three batting and three bowling records.
Batting checks: runs, balls faced, attributed dismissals and strike rate. Bowling
checks: legal balls, charged runs, credited wickets and economy. Rates derive from
those independently transcribed primitive counts; external displayed rates are
also stored so rounding discrepancies cannot disappear inside a tolerance.

| Cricsheet match ID | Date | Reason / conditions | Reference |
| --- | --- | --- | --- |
| 335982 | 2008-04-18 | Bengaluru high-scoring opener; byes, leg-byes and wides | [RCB–KKR scorecard](https://www.cricbuzz.com/live-cricket-scorecard/10557/rcb-vs-kkr-1st-match-indian-t20-league-2008) |
| 981019 | 2016-05-29 | Bengaluru final; large totals and a run-out dismissal | [RCB–SRH scorecard](https://www.cricbuzz.com/live-cricket-scorecard/16448/rcb-vs-srh-final-indian-premier-league-2016) |
| 1082617 | 2017-04-23 | Eden Gardens collapse; no-balls, wides, leg-byes and a partial bowling over | [KKR–RCB scorecard](https://www.cricbuzz.com/live-cricket-scorecard/18147/kkr-vs-rcb-27th-match-indian-premier-league-2017) |
| 1178424 | 2019-04-30 | Five-over rain-shortened no-result; retained in descriptive stats | [RCB–RR scorecard](https://www.cricbuzz.com/live-cricket-scorecard/22484/rcb-vs-rr-49th-match-indian-premier-league-2019) |
| 1216517 | 2020-10-18 | Dubai double Super Over; only ordinary innings contribute | [MI–KXIP scorecard](https://www.cricbuzz.com/live-cricket-scorecard/30464/mi-vs-pbks-36th-match-indian-premier-league-2020) |
| 1370353 | 2023-05-29 | Ahmedabad final; full first innings and 15-over DLS chase, pace/spin examples | [CSK–GT scorecard](https://www.cricbuzz.com/live-cricket-scorecard/72622/csk-vs-gt-final-reserve-day-indian-premier-league-2023) |

References were accessed on 2 November 2026. Match body dates/teams were checked;
some provider page-title metadata incorrectly says 2026, so that title was not used
as the season identity. Official IPL reports also support the
[2019 shortened match](https://www.iplt20.com/news/article/match-report-m49-rcb-vs-rr)
and [2023 DLS final](https://www.iplt20.com/news/article/tata-ipl-2023-final-csk-vs-gt-match-report).

Every tested player, metric, expected/observed value, difference, match ID and
reference URL is in [the comparison ledger](qa/independent_scorecard_results.csv).
The offline reference fixture is `tests/fixtures/independent_ipl_scorecards.json`.
There are **144 PASS rows and zero engine-statistic discrepancies** in the sample.

One external display discrepancy remains: Noor Ahmad's economy is displayed as
**5.70** on the 2023 reference page, while its own 17 runs and 3 overs imply
`6 × 17 / 18 = 5.666…`, or **5.67** to two decimals. The primitive counts match;
exact engine arithmetic is retained. See [the discrepancy record](qa/scorecard_discrepancies.json).
Boundary classification, all players/seasons and every source event are not
independently certified by this sample.

## Investigation of the twelve historical failures

The four files containing these twelve tests are byte-identical in the dev and
production checkouts. The same targeted tests pass **12/12 with 100 passing subtests**
against untouched `main` at `85e0b5f…`. Therefore these particular failures are
application/test-target mismatches, not evidence of newly broken dev functionality.

| Test group | Why it fails on dev | Required test target |
| --- | --- | --- |
| `test_accuracy.py::DossierInterface` (1) | Selects “Player dossier” and asserts production dossier controls/metrics. Dev exposes “Player Profile”. | Production UI |
| `test_runtime.py` tests 01 and 06 (2) | Expects production “Decision desk” state; appends code referring to production variable `s`. Dev uses `squads` and a different runtime graph. | Production UI/runtime |
| `test_startup.py` first two startup checks (2) | Requires production Home pitch “From a cricket question” and production navigation. Dev Home has the Phase 3 overview. Startup itself succeeds. | Production UI |
| `test_ui.py::Interface` (7) | Requires “Home”, “Decision desk”, production scenarios/journal/themes and production state objects. These are not the dev application's routes. | Production UI |

All twelve remain discoverable in `python -m pytest -q`; none were deleted,
weakened or marked skipped. Exact IDs and before/after sets are recorded in JSON.
The pre-existing intermittent SQLite-lock failure mentioned in the earlier audit
was not reproduced in this fresh run; shared storage code was not changed.

**Recommended suite separation:** retain `tests/shared` for pure analytics/storage,
`tests/dev` for the six current workspaces/agents, and `tests/production` for the
existing production acceptance tests. Use an explicit application-entrypoint
fixture plus a CI checkout matrix: production tests against the production app,
dev tests against the dev app, shared tests in both. Preserve all assertions.
Do not rename a production route inside tests merely to obtain a green result.
This audit documents that separation; it does not silently alter default discovery.

## Actual commands and outcomes

A new venv was installed from `requirements-dev.txt` without system site packages;
`python -m pip check` returned “No broken requirements found.” Versions and local
CPU/memory limits are in `qa/environment.json` (two CPU quota, 8 GiB container limit).
No real API key was copied into the clean checkouts.

- Baseline `python -m pytest -q`: **158 passed, 12 failed**, 168 passing subtests.
- Corrected `python -m pytest -q`: **204 passed, 12 failed**, 168 passing subtests.
- Explicit current dev/Lab suite: **145 passed**, 23 passing subtests.
- New QA coverage: **46 passed** (36 external records, 8 defect cases, 2 UX/isolation cases).
- Targeted production-reference tests: **12 passed**, 100 passing subtests.
- Syntax compilation, package imports, CSV-to-Parquet verification and `pip check`: **PASS**.
- No new failure IDs; no skipped tests in these pytest runs.

Exact commands, including the explicit dev-suite file list and production node IDs,
are saved in [test_results.json](qa/test_results.json). The full suite deliberately
returns a nonzero exit code until test targeting is aligned.

## Performance and UX measurements

Final corrected clean-process measurements (single analyst, no cached Parquet):

| Measurement | Observed |
| --- | ---: |
| Home startup | 1.112 s |
| First Lab visit including conversion | 14.559 s |
| Warm Lab rerun | 0.997 s |
| Query median / p95, twenty repetitions | 0.0973 / 0.1435 s |
| Validated manifest/cache reuse | 0.0075 s |
| Current RSS at Home / after Lab | 255.07 / 349.17 MiB |
| Peak RSS in that process | 694.18 MiB |
| Derived Parquet total size | 2,385,428 bytes |

Before the actor-filter correction, two clean-process trials measured query medians
near 0.40 s and whole-Lab warm reruns near 2 s. Those records are retained alongside
the final record. First-load conversion and peak memory were not materially reduced
by query projection; do not infer a smaller cold-build memory requirement. Timings
are local observations under other local QA work, not hosted guarantees or an SLA.

An actual local Streamlit server was also measured after all six workspaces were
visited. See `qa/server_memory.json` for the final current/peak RSS and scenario.
Legacy Pandas workspaces can increase the combined memory footprint beyond the
Home/Lab-only measurement. Small-host memory headroom and sustained multi-user load
remain unverified and must not be inferred from the 8 GiB local container.

Desktop browser checks cover search, all six routes and CSV/JSON downloads. Both
actual “Harmeet Singh” identities (`0bf15e52`, `2a72fd4f`) were selected separately;
labels include IDs and no name-based merging occurs. Mobile checks cover layout,
phase selection by typing in the searchable selector, bowling mode and player search at width 390. These are emulated Chromium viewport checks, not physical iOS/Android or direct popup/touch certification.
Tables scroll within
their containers; the page has no horizontal overflow. Empty windows, invalid date
ranges and original-agent filter isolation are also exercised through AppTest.

Browser automation waits for Streamlit reruns and changed-player ID captions before
interacting with the next control. Earlier automation attempts timed out on detached
selector nodes while a rerun was replacing them; the corrected harness uses labeled
widgets and waits for backend acknowledgement. Successful final checks and download
validation are recorded in `qa/browser_results.json`; these timeouts were not
silently counted as successful checks.

## Reproduce

```bash
python -m venv /tmp/ipl-qa-venv
/tmp/ipl-qa-venv/bin/python -m pip install -r requirements-dev.txt
/tmp/ipl-qa-venv/bin/python -m pip check
/tmp/ipl-qa-venv/bin/python -m pytest -q tests/test_post_integration_qa.py tests/test_independent_scorecards.py tests/test_comparison_ux_qa.py
/tmp/ipl-qa-venv/bin/python -m pytest -q
/tmp/ipl-qa-venv/bin/python -m compileall -q src scripts
```

For an uncontaminated first-run measurement, create a fresh detached worktree of
the corrected commit, with no `data/parquet/` directory and no private secrets:

```bash
git worktree add --detach /tmp/ipl-qa-clean HEAD
/tmp/ipl-qa-venv/bin/python scripts/qa_measure_startup.py --root /tmp/ipl-qa-clean --output /tmp/ipl-qa-performance.json
```

Browser QA is optional developer tooling; it is not an app runtime dependency.
Install Playwright/Chromium in a test environment, start the corrected dev app
locally, then run:

```bash
python -m pip install playwright
python -m playwright install chromium
python -m streamlit run app.py --server.port 8541 --browser.gatherUsageStats false
# In another terminal:
python scripts/qa_browser.py --url http://127.0.0.1:8541 --output-dir /tmp/ipl-browser-qa
```

The harness accepts a local dev URL and creates a temporary browser session; use a
test app/session. It downloads only public cricket evidence and never clicks an AI
report button. A system Chromium is used when available; otherwise Playwright's
installed Chromium is used.

## Before a hosted release

1. Rebuild/reboot the dev Cloud app after deployment and verify exported
   `metrics_version` is `comparison-metrics-1.0.1`. Inspect actual cloud logs,
   dependency installation, first-load conversion, all six pages and exports.
2. Confirm the hosting memory limit and measured headroom. Warm/prebuild the derived
   store before a timed demo; query projection does not eliminate conversion memory.
3. Align production/dev CI targets as above while preserving shared coverage.
4. If live specialist availability is a release requirement, perform an explicitly
   budgeted live DeepSeek check separately; mocked tests do not establish endpoint health.

No new agents, advanced models, source-data alterations or `main` changes are part
of these corrections. The final delivery provides the verified dev commit SHA.
