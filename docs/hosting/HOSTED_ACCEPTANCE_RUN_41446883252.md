# Public hosted acceptance report — 2 November 2026

**Result: PASS for the required hosted demonstration gates.** Real Playwright
Chromium interactions ran on GitHub Actions against the public development app.
This result does not use local Playwright outcomes as hosted evidence.

- App: <https://creaseiq-cricket-capstone.streamlit.app/>
- Successful audit: <https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41446883252>
- Audited revision: `9cca4e7c65cd02cf07ad4d6fc4cab0785cc274b8`.
- Observed before and after: that exact revision, `git_tracked_changes: false`.
- Browser workload: 12:43–12:48 UTC; first deployment snapshot at 12:43:38 UTC.
- Result: **48 PASS, 0 FAIL, 3 optional NOT VERIFIED**; workflow conclusion success.

The cleanup commit advances the development branch after this audit. It removes
the temporary push trigger, records these results and hardens the test adapter's
frame reset after navigation. No application runtime or data files change.
The audited revision above is the observed deployed revision; a later branch
revision is not silently presented as having been observed in this run.

## Evidence

[Download the hosted evidence artifact](https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41446883252/artifacts/13143002426)

Artifact `hosted-streamlit-acceptance-41446883252` contains 179 files, including
screenshots, 90 downloaded CSV/JSON files, per-case reproduction steps, before/after
diagnostics and specialist packets, source-checksum comparisons, external scorecard
comparisons, execution logs, `quality_gates.json` and `ACCEPTANCE_REPORT.md`.
The ZIP is 4,233,631 bytes; GitHub reports SHA-256
`d5071ac2130b52cf4fc5d2d3542bffc4bd3a191157b40a0e025f40a96a92e090`.
It expires on **16 November 2026**; download it before that date.

[Runner logs](https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41446883252/job/125282101071)
and [the machine-readable summary parsed from those logs](hosted-run-41446883252-summary.json)
provide a permanent review trail. The summary is explicitly a log-derived record;
the full per-metric comparison data remain in the original uploaded artifact.

## Quality gates

| Gate | Result | Observed evidence |
|---|---|---|
| GitHub runner connectivity | PASS | DNS resolved to 35.201.127.49; HTTP and HTTPS finished at the app root with 200 responses. |
| Redirect behavior | PASS | Anonymous 303 redirects through share.streamlit.io/-/auth/app and the app's /-/login returned to the public app. |
| Intended deployed revision | PASS | Exact clean audited revision observed on the first polling attempt. |
| All six workspaces | PASS | Home/Overview, Player Profile, Player Comparison Lab, Team Matchups, Squad Analysis and Auction Trends rendered without Streamlit exception panels. |
| Player identity | PASS | Requested registry IDs remained attached to displays and exports; two Harmeet Singh identities remained distinct. |
| Batting comparison | PASS | Kohli ba607b88 versus Rohit 740742ef, archive-wide and exclusive cutoff 2023-01-01. |
| Bowling comparison | PASS | Bumrah 462411b3 versus Rashid 5f547c8b, archive-wide and exclusive cutoff 2023-01-01. |
| Four analytical windows | PASS | Overall, 1–6, 7–15 and 16–20 over windows in both modes at both cutoffs. These are analytical bands. |
| Evidence exports | PASS | 30 scenarios; metrics CSV, complete match-series CSV and scope/source JSON downloaded and checked for each: 90 files. |
| Cutoff and export consistency | PASS | Exported dates obeyed inclusive start/exclusive cutoff; identities, scopes and 16 displayed metrics per case agreed with downloads. |
| Independent arithmetic | PASS | 360 match-series totals/rates/count comparisons, calculated without calling app metric functions. |
| Source checksums | PASS | All four exported source hashes matched independently hashed runner-checkout CSVs; input/output row counts agreed. |
| External historical scorecards | PASS | 96 sampled metric fields across six matches reconciled. One external rate-display precision difference was documented. |
| Empty and invalid dates | PASS | Empty windows produced unavailable rates; invalid date order produced readable validation text without exception panels. |
| Existing specialist controls | PASS | Player, team, franchise and auction selectors worked; nonempty evidence packets were inspected. |
| Specialist input isolation | PASS | Before/after specialist evidence JSON packets were identical under restored specialist selections. |
| Client provider requests | PASS | Zero browser-visible provider attempts; zero Generate Report buttons clicked. |
| Browser errors | PASS | No uncaught browser errors were recorded. |
| Revision stability | PASS | Same clean audited revision at the end. |
| Memory observations | PASS | Process memory read before and after; no observed out-of-memory failure during this workload. See limits below. |
| Existing four contract jobs | PASS | [CI run 41446883190](https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41446883190) succeeded on the audited commit. |
| Production isolation | PASS | main remained 85e0b5f3c34dd18d15447a96e229c0e37e7047da; existing four-job workflow unchanged. |
| Live paid specialist reports | NOT VERIFIED | Intentionally excluded; no paid DeepSeek requests were made by the test actions. |
| Server-side provider traffic | NOT VERIFIED | A browser cannot prove absence of all server-side traffic; no live report was requested. |
| Whole-history dot/innings/boundary certification | NOT VERIFIED | Match-series exports do not expose all primitive inputs needed for independent certification. |

The last three items are the optional NOT VERIFIED results counted by the runner.
Cold process startup and aggregate hosting memory headroom were not established
by this read-only workload either; no hosted reboot or cache clearing was performed.

## Timing and memory

Each complete comparison scenario took **7.72–11.19 seconds**, median **8.57
seconds**, including control changes, reruns, three downloads, arithmetic checks
and a screenshot. This measures end-to-end browser work, not query latency alone.

| Diagnostic | Before | After |
|---|---:|---:|
| Process RSS | 916.15 MiB | 1,141.36 MiB |
| Process high-water mark | 916.15 MiB | 1,241.35 MiB |
| Observed cgroup limit | 3 GiB | 3 GiB |

Peak process memory was about 40.4% of the observed limit. This is useful process
evidence, but it is not a measurement of all cgroup usage or a guarantee of memory
available under simultaneous users. The process was already running before the
audit; these are not cold-start measurements.

## Independent cricket checks and their limits

The browser selected two batters and two bowlers in each reference match, set the
match date as the inclusive start and the following day as the exclusive cutoff,
selected Overall, and downloaded the results. It checked runs, balls faced,
dismissals and strike rate, or legal balls, charged runs, credited wickets and
economy, against the pre-existing externally transcribed fixture.

| Match ID | External scorecard | Reason for inclusion |
|---|---|---|
| 335982 | [2008 opener](https://www.cricbuzz.com/live-cricket-scorecard/10557/rcb-vs-kkr-1st-match-indian-t20-league-2008) | High score and significant extras |
| 981019 | [2016 final](https://www.cricbuzz.com/live-cricket-scorecard/16448/rcb-vs-srh-final-indian-premier-league-2016) | High scores and run-out context |
| 1082617 | [2017 KKR–RCB](https://www.cricbuzz.com/live-cricket-scorecard/18147/kkr-vs-rcb-27th-match-indian-premier-league-2017) | RCB 49 and shortened bowling spells |
| 1178424 | [2019 RCB–RR](https://www.cricbuzz.com/live-cricket-scorecard/22484/rcb-vs-rr-49th-match-indian-premier-league-2019) | Five-over rain-affected match |
| 1216517 | [2020 MI–Punjab](https://www.cricbuzz.com/live-cricket-scorecard/30464/mi-vs-pbks-36th-match-indian-premier-league-2020) | Double super over; regular innings checked |
| 1370353 | [2023 final](https://www.cricbuzz.com/live-cricket-scorecard/72622/csk-vs-gt-final-reserve-day-indian-premier-league-2023) | DLS and 15-over chase |

All 96 expected field comparisons passed. For Noor Ahmad in the 2023 final, 17
charged runs in 18 legal balls gives exact economy 5.6666666667, displayed by the
app as 5.67. The reference displays 5.70. Counts agree; the external display uses
coarser rate precision. This is recorded in `reference_display_notes.json`, not
treated as a primitive-count discrepancy.

These references certify the sampled innings fields. Whole-history reconciliation
certifies consistency with downloaded match-series evidence; it does not establish
independent correctness of every delivery, every career total or every phase
boundary in a second archive. Source checksums certify which input files were used,
not that every source record is correct. No new statistical model was introduced.

## Reproduction and commands

For any comparison, open Player Comparison Lab, search for the registry IDs above,
choose Batting/Bowling, set the stated dates and analytical window, open Evidence
and Source Records, then download all three exports. Every scenario's `steps.json`
in the artifact contains its exact scope. Dates are checked against the complete
match-series export, not just a capped preview.

GitHub Actions executed:

```bash
python -m pip install -r requirements-hosted-audit.txt
python -m playwright install --with-deps chromium
python -m pytest tests/hosted -q
# 21 passed on the audited revision
python scripts/hosted_acceptance.py \
  --url https://creaseiq-cricket-capstone.streamlit.app/ \
  --expected-commit 9cca4e7c65cd02cf07ad4d6fc4cab0785cc274b8 \
  --output-dir hosted-evidence
# Exit 0; 48 PASS, 0 FAIL, 3 optional NOT VERIFIED
```

## Earlier blocked attempts and the corrected harness

The first run [41443702605](https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41443702605)
passed HTTP connectivity but timed out looking for Home/Overview in the outer
page. Its bounded deployment polling correctly left revision and browser gates
NOT VERIFIED. [Its screenshots/logs remain available](https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41443702605/artifacts/13142062079).

The diagnostic run [41445990402](https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41445990402)
captured the actual frame structure: the working app was in the same-host `/~/+/`
iframe, alongside a separate third-party status frame. The harness had searched
the wrong context. [Diagnostic evidence](https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/41445990402/artifacts/13142492449)
is retained. This was an automation defect, not a demonstrated app failure.

The corrected harness scopes UI queries to the application frame while retaining
page-level screenshots, navigation and download events. Third-party frames are
excluded. No application code was changed to obtain the successful audit.

## Release recommendation

The audited public revision is suitable for the tested deterministic capstone
demonstration workflows. Keep scope limitations visible, download the evidence
before retention expires, and perform any future paid specialist acceptance as a
separately authorized check with a controlled budget. Do not describe this run as
complete source certification, cold-start/load testing, or live LLM validation.
