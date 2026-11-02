# Hosted development demo: configuration, acceptance and CI

Baseline audited: `b60c0a97194903d1b3a01c22ddd4e61a2db6c3f9`.
This update changes only development diagnostics and CI targeting. Cricket formulas,
agent prompts, credentials handling, source data and the production deployment are
unchanged. No further memory tuning was applied: the actual Cloud allowance is
unavailable, and previous query filtering is already validated.

## Release decision and quality gates

**Hosted demonstration is NOT VERIFIED.** Local acceptance and contract CI pass,
but Cloud settings, the deployed revision, logs and resource allowance cannot be
inspected with the available tools. The reported URL could not be opened by the
remote reader; that does not prove the app is down.

| Requested gate | Result | Evidence / required action |
| --- | --- | --- |
| Hosted deployment | NOT VERIFIED | No authenticated Streamlit account/session or Cloud logs available. Follow the checklist below. |
| Correct deployed commit | NOT VERIFIED | Compare Cloud build/checkout evidence and Home diagnostics with the final dev commit. No revision was observed remotely. |
| Cold startup | NOT VERIFIED hosted; PASS locally | Fresh worktree/venv, no cached Parquet: 22.546 s for first Lab visit under concurrent local test load. Prior runs were about 14.56 s; these are not identical-load benchmarks. |
| Memory headroom | NOT VERIFIED | New cold-process peak 653.44 MiB; earlier broader server peak about 801 MiB. Local container has 8 GiB, not the unknown Cloud allowance. No OOM locally does not establish small-host safety. |
| All six workspaces | NOT VERIFIED hosted; PASS locally | Existing workspace/acceptance tests pass, including comparison-filter isolation. Prior browser QA checked six routes and emulated desktop/mobile. |
| Deterministic cricket statistics | PASS sampled/local | Original engine fixtures and 144 independently sourced field comparisons across six matches pass. This is not an exhaustive official-data audit. |
| Source evidence exports | NOT VERIFIED hosted; PASS locally | Existing CSV/JSON download and dismissal/wicket reconciliation checks pass. Recheck hosted downloads after the rebuild. |
| Development CI | PASS locally; remote run NOT VERIFIED until observed | Explicit target: 149 passing tests; four selector-policy unit checks pass. Workflow is committed but local results are not a GitHub Actions execution claim. |
| Production regression isolation | PASS locally | Production target on unchanged main: 12 pass; shared on both applications: 59 pass each. Assertions and original test files are preserved. |
| Live specialist integration | NOT VERIFIED live; PASS mocked | No credentials or paid-call budget were supplied for this audit. No live API request was made. |
| Security and secrets handling | PASS for changed-code/local checks; Cloud secrets NOT VERIFIED | Diagnostics never read secrets, environment dumps or Git remote URLs. Workflow has contents:read, no secret injection and no production deploy step. Cloud secrets settings still require owner verification. |

Machine-readable command outcomes and memory measurements are in
[hosting/evidence.json](hosting/evidence.json). The previous detailed independent
scorecard/UX evidence remains in [POST_INTEGRATION_QA.md](POST_INTEGRATION_QA.md).

## What the repository actually configures

- `start.sh` starts `python -m streamlit run app.py` and installs requirements.
- `.streamlit/config.toml` configures theme and headless serving only. It does not
  select a GitHub repository/branch or set a hosting memory allowance.
- Intended dev tuple: `br-abishek-07/creaseiq-cricket-capstone`, `dev-phase1-ui`,
  `app.py`, Python **3.12**.
- Reported dev address: https://creaseiq-cricket-capstone.streamlit.app/ . Its actual
  configured source tuple has **not** been verified from Cloud account settings.
- Production `main`/https://creaseiq.streamlit.app/ must not be changed by this work.

## Exact owner deployment and verification checklist

1. Sign in to https://share.streamlit.io/ with the account that owns the development
   app. Identify the row corresponding to the **reported dev URL**, not the
   production CreaseIQ app. Record the repository, branch and entry file shown in
   the app row/source link. Follow the GitHub link and confirm all three fields.
2. Confirm the tuple is the intended dev tuple above. If it differs, stop: do not
   repoint/delete the production app. Use the development app's source-edit/redeploy
   flow where supported, or create a separate development app with that exact tuple.
   Keep the existing production app on `main`.
3. Select Python 3.12 for the development deployment. Confirm `requirements.txt` is
   being installed. Inspect Manage app/build logs for successful DuckDB 1.5.6 and
   PyArrow 23.0.1 installation, absence of import errors, and startup completion.
   Record the checkout revision/build commit if the logs expose it.
4. Reboot **only the development app** after the source update finishes. From Home,
   open **Deployment diagnostics**. Save the JSON: observed Git commit, tracked-change
   flag, file hashes, package versions, current/peak process RSS and cgroup limit.
   No secrets are displayed. A dirty checkout is not proof of the published build.
5. Compare `git_commit` to the final commit linked in the delivery. If Git metadata
   is unavailable, inspect Cloud checkout/build evidence. Hashes corroborate only
   the listed files and do not independently prove a complete deployed commit.
   For file checks: `git show <commit>:app.py | sha256sum`, and repeat for the other
   paths listed in the JSON. Use the exact commit, not moving branch contents.
6. Obtain the service's actual resource allowance from the Cloud account/provider
   status or support. Compare it with observed whole-process peaks under the intended
   demo workload, with headroom. A cgroup limit may reflect a container/parent and
   must not be assumed to be the contractual app allowance. RSS values are snapshots;
   run this diagnostic again after visiting all pages. Do not tune memory based on
   the local 8 GiB limit or assume 653/801 MiB automatically fits Cloud.
7. Check cold startup on a fresh dev build/container without a derived cache. A
   reboot alone may retain files and therefore be a warm test. Observe conversion
   completion and memory/OOM logs; record elapsed time. Repeat the same Lab request
   and confirm cache reuse. Generated Parquet belongs under `data/parquet/` and is
   recreated from committed checked CSVs; never delete original CSVs to clear cache.
8. Open Home/Overview, Player Profile, Team Matchups, Squad Analysis, Auction Trends
   and Player Comparison Lab. Confirm each finishes rendering without an exception.
9. In the Lab select Kohli `ba607b88` and Rohit `740742ef`. Verify Batting and Bowling,
   all four windows, and the explicit date scope. With cutoff `2023-01-01`, downloaded
   records must have match dates strictly earlier than that date. Set dates to
   `2000-01-01`/`2001-01-01`: zero observations and N/A rates should be explained.
   Set start equal to cutoff: expect a readable validation message, not a traceback.
10. Search “Harmeet Singh”: the two IDs `0bf15e52` and `2a72fd4f` must remain separate.
    Select both; identical IDs must be prevented. Repeat at desktop and narrow mobile
    width. Real iOS/Android/touch testing remains separate from Chromium emulation.
11. Download comparison metrics CSV, full match series CSV and scope/manifest JSON.
    Confirm two intended IDs, dates, phase, super-over exclusion and
    `comparison-metrics-1.0.1`. Batting series includes dismissals; bowling series
    includes credited wickets. Preview limits do not limit totals or the full series.
12. Save each specialist's inspected evidence packet, change Lab filters, then return
    and compare packets with unchanged original controls. Lab controls must not change
    specialist scopes. Browsing the Lab must not send any LLM request.
13. To test missing-data recovery, use a disposable local/dev clone, temporarily move
    one comparison source aside, verify a readable Lab error and accessible other
    pages, then restore it. Do not disrupt the hosted production app to simulate faults.
14. Live DeepSeek is optional and **not authorized by this runbook automatically**.
    If you choose to authorize it, provide the credential through development Cloud
    Secrets, approve a fixed call/token/cost ceiling, test one report at a time and
    inspect usage. Never paste keys into repository files, issues or public logs.
15. Record actual outcomes and unresolved gates. Do not label the deployment ready
    merely because local tests or GitHub Actions pass.

Settings/logs navigation follows the official
[Streamlit app-settings documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings):
workspace overflow → Settings, or the app's Manage app panel. No Cloud settings
were changed by this agent.

## Explicit CI contracts — no assertions removed

Use the new runner from the dev checkout:

```bash
python ci/check_contracts.py
python ci/test_targets.py --target shared
python ci/test_targets.py --target development
# Separate read-only checkout of production, not the dev app:
python ci/test_targets.py --target production --app-root /path/to/main-checkout
python ci/test_targets.py --target shared --app-root /path/to/main-checkout
# Deliberately unchanged universal discovery:
python -m pytest -q
```

The runner prints the checked-out commit, inventory and explicit deselection count.
An unclassified test module/node fails classification instead of silently being omitted. Production
selection on the dev app is refused before running assertions; development selection
on a production app is likewise refused. These contract checks inspect the actual
app strings, not just a branch name. Shared tests use the application tree specified
by `--app-root`.

The unchanged whole-suite discovery still includes twelve production UI tests and
therefore remains non-green on dev. A green **contract workflow** does not mean
that every assertion has passed against one incompatible application.

`.github/workflows/application-contracts.yml` runs on dev pushes/PRs or manual dispatch:

- shared-development and development: checkout the event revision;
- shared-production and production: read-only checkout of `main`;
- separate application requirements, Python 3.12, `pip check` and selector policy;
- JUnit artifacts uploaded even after failure; no deployment, secret or write step.

For a PR, the event revision can be GitHub's merge revision; the runner records the
actual checked-out SHA. The `main` reference can advance independently; every job
must retain that SHA in its logs. Local production tests used
`85e0b5f3c34dd18d15447a96e229c0e37e7047da`. No main files or deployment were edited.
