# Manual hosted acceptance audit

This audit reads the public **development** app at
<https://creaseiq-cricket-capstone.streamlit.app/>. It does not deploy code,
change settings, read secrets, rebuild the app cache, or request AI reports.
Production `main` is outside its target allowlist.

## Run on GitHub Actions

The workflow is `.github/workflows/hosted-acceptance.yml`. Its only trigger is
`workflow_dispatch`; it does not run the browser audit on every push. The existing
four-job `application-contracts.yml` workflow remains separate and unchanged.

1. Wait for Streamlit to finish deploying the intended development revision.
2. Open **Home/Overview → Deployment diagnostics**. Record the full `git_commit`.
   A dirty checkout or a different revision fails the revision gate.
3. From your authenticated GitHub CLI, run:

   ```bash
   gh workflow run hosted-acceptance.yml \
     --repo br-abishek-07/creaseiq-cricket-capstone \
     --ref dev-phase1-ui \
     -f expected_commit=FULL_40_CHARACTER_INTENDED_COMMIT
   ```

   Leaving the input out requires the workflow checkout's own revision. Supply
   an older revision only if that is deliberately the revision being audited;
   a successful test of an older app does not certify a newer deployment.
4. Find and watch the run:

   ```bash
   gh run list --repo br-abishek-07/creaseiq-cricket-capstone \
     --workflow hosted-acceptance.yml --branch dev-phase1-ui --limit 5
   gh run watch RUN_ID --repo br-abishek-07/creaseiq-cricket-capstone
   gh run download RUN_ID --repo br-abishek-07/creaseiq-cricket-capstone \
     --dir hosted-audit-artifacts
   ```

   The run URL is `https://github.com/br-abishek-07/creaseiq-cricket-capstone/actions/runs/RUN_ID`.
   Artifacts are retained for 14 days under `hosted-streamlit-acceptance-RUN_ID`.
   GitHub's run status is non-green for both a real failure and an incomplete or
   blocked audit. Read `quality_gates.json` to distinguish them.

GitHub may require a manually dispatched workflow to be registered on the
default branch before offering it in Actions. If the workflow is absent or
dispatch returns “workflow not found”, record that registration blocker. Do
not modify `main`, change the default branch, add a push trigger, or silently
rerun a different workflow to work around it. Use the local command below until
the repository owner explicitly authorizes a registration approach.

## Run from a browser-capable local machine

Use Python 3.12 from the development checkout. This harness needs no API key and
does not import the application's metric functions or start a local app.

```bash
python -m venv .audit-venv
# macOS/Linux:
source .audit-venv/bin/activate
# Windows PowerShell instead: .audit-venv\Scripts\Activate.ps1
python -m pip install -r requirements-hosted-audit.txt
python -m playwright install chromium
python -m pytest tests/hosted -q
python scripts/hosted_acceptance.py \
  --url https://creaseiq-cricket-capstone.streamlit.app/ \
  --expected-commit FULL_40_CHARACTER_INTENDED_COMMIT \
  --output-dir .runtime/hosted-audit
```

Linux may also need `python -m playwright install --with-deps chromium`.
For testing the harness itself, `--url http://127.0.0.1:PORT/` is supported.
Such a run is explicitly labeled **LOCAL harness validation** and provides no
evidence of public hosting readiness. Run against a clean checkout if checking
the revision gate. The runner uses the normal network proxy and TLS trust;
it does not bypass a restricted network.

## Coverage and interpretation

- Connectivity first: DNS, HTTP and HTTPS status, redirect chains, Streamlit
  HTML markers, and connection errors/timeouts. HTTPS must be reachable before
  browser testing proceeds. A proxy denial is **NOT VERIFIED**, not an app defect.
- Chromium opens all six workspaces. Specialist player, team, franchise and
  auction controls are exercised and their nonempty JSON evidence is inspected.
- Player Comparison Lab: Kohli/Rohit batting and Bumrah/Rashid bowling at the
  archive cutoff `2026-06-01` and exclusive cutoff `2023-01-01`, each across
  Overall, Powerplay (1–6), Middle (7–15), and Death (16–20) analytical windows.
- Stable Cricsheet IDs are checked, including two distinct Harmeet Singh IDs.
  Empty windows and invalid date order must produce readable results/errors.
- Each case downloads metrics CSV, complete match-series CSV and scope/source
  JSON. The validator checks identities, scope, inclusive/exclusive dates,
  counts, weighted rates and display/export agreement. Exported source hashes
  must match hashes computed independently from the runner checkout's CSVs.
- External historical checks use the existing manually transcribed scorecard
  fixture, not values calculated by the app. Two batters and two bowlers in
  each of six matches produce **96 external metric comparisons**. Every result
  records source URL, match ID, player ID, expected and observed values. The
  complete existing fixture has 144 comparisons; this browser audit samples
  96 of them and does not claim to repeat all 144.
- Whole-history series reconciliation establishes consistency, not independent
  correctness of every underlying delivery. External scorecards check overall
  innings; phase totals are reconciled with exports, not independently certified
  from a second ball-by-ball archive. Exported series do not contain all
  inputs needed to independently certify dots, innings or physical boundaries.
  Those limits remain visible in the report.
- Specialist evidence is captured before and after Lab use under the same
  explicit specialist selections. The packets must be identical. No Generate
  Report button is clicked. Browser-visible provider requests are blocked and
  recorded. Server-side traffic is **NOT VERIFIED** from a browser alone;
  absence of a browser request is not proof of no server-side request.
- Deployment SHA, clean/dirty state, package versions and process memory are
  collected before/after. These are observations, not a hosting SLA or proof of
  cold process startup. The audit does not reboot a hosted app or clear its cache.

## Evidence and exit codes

`quality_gates.json` and `ACCEPTANCE_REPORT.md` contain PASS, FAIL and NOT VERIFIED
outcomes. `connectivity.json`, execution logs, screenshots, raw/parsed diagnostics,
specialist packets, per-case reproduction steps and downloads, checksum checks,
independent scorecard comparisons and any exception traceback are preserved.
No authenticated browser state, secret values or browser traces are saved.

Exit **0** means all required gates passed; **1** means a required gate failed;
**2** means incomplete/blocked verification without an established required
failure. Unreached tests are recorded as NOT VERIFIED. Optional limitations do
not silently turn into PASS. A deployment cannot be declared accepted until a
real run against the public URL has passed the required gates.

## Execution access in this development session

The environment's public Streamlit request received a proxy tunnel denial
(`403 Forbidden`) and local DNS resolution failed. That does not establish an
application defect. The connected GitHub tools can commit files but expose no
workflow-dispatch operation; the local GitHub CLI reports invalid authentication.
Consequently this session cannot honestly provide a new hosted Actions run URL
until an authenticated owner dispatches the manual workflow. No hosted audit
completion or uploaded GitHub artifact is implied by adding these files.

## Temporary automatic execution authorized on 2 November 2026

For this audit only, the owner authorized a push trigger restricted to
`dev-phase1-ui` so GitHub Actions can register and execute the workflow without
GitHub CLI installation. It is removed after the hosted run completes. `main`
and the existing four-job contract workflow remain unchanged.

The browser polls for the exact intended clean checkout for up to 600 seconds,
with bounded individual browser operations and a 15-second retry interval.
`deployment_poll.json` records each observed revision or startup error. A stale
revision at timeout is NOT VERIFIED (deployment/access blocked), not an
application failure. If the revision changes during the workload, revision
stability is NOT VERIFIED and the audit cannot declare acceptance.
