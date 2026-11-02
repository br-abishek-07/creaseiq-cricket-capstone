# Player Comparison Lab v1.0

The Lab compares recorded IPL performances for two stable Cricsheet player IDs.
It uses DuckDB to query compressed Parquet files. It makes no AI or network calls.

## Run it

1. Check out `dev-phase1-ui` and use Python 3.12.
2. Run `python -m pip install -r requirements.txt`.
3. Optional: run `python scripts/convert_to_parquet.py` before starting the app.
4. Run `python -m streamlit run app.py`.
5. Select **Player Comparison Lab** in the sidebar.

The first visit builds and validates Parquet automatically if needed. Later visits
reuse that source version. All required compressed CSVs are included in the branch.
A DeepSeek key is not needed for this page. Existing specialist reports keep their
own key requirements and data scopes.

## Compare players

1. Search for Player A and Player B. The displayed ID distinguishes similar names.
   Only IDs observed in the delivery/wicket archive appear; they are not necessarily
   the full list of people named in team rosters. Identical IDs cannot be selected.
2. Choose Batting or Bowling.
3. Set the inclusive start date and exclusive decision date. For example, choosing
   1 January 2023 as the decision date excludes that day and every later observation.
4. Choose Overall or an analytical window. These controls affect only this Lab.
5. Read the exposure counts alongside rates. A result is not an acquisition ranking.
6. Expand **Evidence and Source Records** to inspect source matches, deliveries,
   dismissals, the full match series and the dataset manifest. Download the metrics,
   match series and JSON scope/manifest to preserve the calculation context.

The two summary columns contain only metrics relevant to the selected discipline.
The phase profile compares all three windows using the same dates. Selecting a
phase also offers an overall table for those dates.

## Windows and formulas

| Window | Displayed overs | Source zero-based overs |
| --- | --- | --- |
| Powerplay window | 1–6 | 0–5 |
| Middle overs | 7–15 | 6–14 |
| Death overs | 16–20 | 15–19 |

These fixed analytical bands are not certified official powerplays in reduced
matches. They intentionally differ from the existing Moneyball page's requested
middle/death split. Overall includes all regular source overs, even an unusual
over beyond a standard window; the source anomaly is reported rather than deleted.

| Metric | Calculation |
| --- | --- |
| Batting runs | Sum of batter runs in the selected deliveries |
| Balls faced | Sum of the source batter-ball flag; wides excluded, source-counted no-balls included |
| Batting strike rate | 100 × runs / balls faced |
| Batting average | Runs / batter dismissals attributed through the wicket table |
| Batter dot percentage | 100 × counted balls faced with zero batter runs / balls faced |
| Legal balls bowled | Sum of the legal-delivery flag; wides/no-balls excluded |
| Runs charged | Batter runs + wides + no-balls; byes, leg-byes and penalties excluded |
| Bowling economy | 6 × charged runs / legal balls |
| Bowler wickets | Sum of the wicket-event bowler-credit flag |
| Bowling strike rate | Legal balls / bowler wickets |
| Bowling dot percentage | 100 × legal deliveries with zero total runs / legal balls |

A batter dot can include byes, leg-byes or a zero-batter-run no-ball. A bowling dot
is a legal team-scoreless delivery, so those scoring extras do not count as dots.
These are explicit definitions, not interchangeable dot-rate conventions.

Run-outs and retired-out events count against the dismissed batter. Retired hurt
does not. A non-striker's dismissal belongs to that person's ID. Batting average
for a phase uses runs and dismissals in that phase, not the full innings' dismissal.
Wicket aggregates are calculated separately from runs/balls, preventing multiple
wicket events from multiplying delivery totals. All ordinary figures exclude super
overs in both delivery and wicket records.

Matches/innings represented count relevant events in the selected window, including
a dismissal without a faced ball. They do not count every named appearance or DNB.
A zero denominator gives N/A. A genuine zero rate with exposure remains zero.
There is no invented minimum-sample threshold, confidence interval, posterior
estimate, peer percentile, skill score or “better buy” recommendation.

## Data and conversion

The new Lab uses full cleaned Cricsheet files:

| File stem (CSV or CSV.gz) | Rows |
| --- | ---: |
| `ipl_matches_clean_2008_2026` | 1,243 |
| `ipl_deliveries_clean_2008_2026` | 295,732 |
| `ipl_wickets_clean_2008_2026` | 14,705 |
| `ipl_innings_clean_2008_2026` | 2,514 |

Only the match and innings metadata are new repository source files. They were
copied without changing CSV bytes from the uploaded
`IPL_Cricsheet_Clean_Accurate_Data_2008_2026.zip` and losslessly gzip-compressed.
Existing deliveries, wickets, registry and legacy analytical sources remain intact.

The converter reads compressed CSV directly, checks required fields and strict
integer types, preserves IDs as strings and dates as DATE, and writes Zstandard
Parquet. All source columns are preserved. It verifies row counts using DuckDB and
PyArrow and compares all typed source rows with the Parquet rows in both directions.
Checks cover primary keys, foreign keys, innings references, dates, player IDs,
flags, dismissal semantics and run arithmetic. No fuzzy player-name joins are used.

A hash of all source files and the converter code identifies a dataset version.
A manifest records file hashes, schemas, row counts and warnings. Builds use a
private staging directory, process/thread locks and atomic publication. Partial or
corrupt caches are rebuilt. Each query has its own connection; connections are
never shared between Streamlit sessions. SQL values are parameterized.

Generated versions live in `data/parquet/` and are ignored by Git. They can be
regenerated from the committed CSVs, including after a new Streamlit deployment.
Replacing sources selects a new hash version; old complete versions are retained.
For frequent updates, remove unused derived versions while the app is stopped.
Do not delete original source CSVs to clear a cache.

## Limitations and evidence

Coverage is 18 April 2008 through 31 May 2026. There are 295,557 regular delivery
events and 175 super-over events. The selector resolves 805 observed person IDs;
all exist in the existing registry. The archive has four overs with more than six
legal deliveries. Rates use actual counted balls, not over-label arithmetic.

Reduced planned overs, adjusted-result methods and reduced targets remain available
in the match/innings metadata. Such matches are retained, with page warnings for
represented matches. A normal short chase is not automatically called rain-shortened.
The page does not reconstruct official powerplay allocations from original JSON.

The cleaned CSV lacks original non-boundary classification, and the original match
JSON archive was not available for this implementation. Physical-boundary counts
and rates are therefore unavailable, even when a delivery records four or six off
the bat. The engine supports an explicitly supplied `is_boundary` classification;
hand-calculated fixtures verify genuine and non-boundary four/six distinctions.
No such classification is invented for the shipped archive.

Delivery and wicket previews are capped at 200 rows each. Totals use the full
filtered sample; match metadata and match-level series cover the whole selection.
The exported scope and hashes make the inputs traceable. Source-derived validation
is not independent certification of every scorecard.

The official IPL report for the [2016 final](https://www.iplt20.com/news/article/match-report-final-rcb-vs-srh)
was read on 2 November 2026. Sample tests check Kohli's 54 runs/35 balls, Warner's
69/38, and Jordan's 24 legal balls/45 charged runs/3 wickets against that report.
This is a seven-field sample across three players in one match, not an audit of
all players or every metric. Batting averages and dot rates have manual-formula
checks but have not been independently compared against complete official careers.

Data attribution: [Cricsheet](https://cricsheet.org/), under the included
[ODC Attribution licence](../data/CRICSHEET_SOURCE_LICENSE.txt).
See [the machine-readable data audit](PLAYER_COMPARISON_DATA_AUDIT.json) and
[the implementation/test audit](PLAYER_COMPARISON_AUDIT.md).

## Verify or troubleshoot

Install test dependencies with `python -m pip install -r requirements-dev.txt`.
Then run:

```bash
python scripts/convert_to_parquet.py
python -m pytest tests/test_player_comparison_engine.py -q
python -m pytest -q
python -m compileall -q app.py src scripts
```

Missing dependencies or sources produce readable errors local to the Lab. Other
workspaces remain available. Install the requirements and reboot after deployment
if new packages are missing. Restore the expected source filenames for a missing
file. **Rebuild comparison cache** clears the cached engine and rechecks data;
missing/corrupt generated files rebuild from sources. Rebuild cannot repair an
invalid source schema; fix or restore the actual input file first.
