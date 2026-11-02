"""Player Comparison Lab UI. This module never imports or calls an AI provider."""
from datetime import date, timedelta
import json

import pandas as pd
import streamlit as st

from .parquet_store import ComparisonDataError, ROOT, source_paths
from .query_engine import ComparisonEngine, PHASES, METRICS_VERSION


@st.cache_resource(show_spinner=False, max_entries=2)
def _engine(data_dir, source_versions):
    return ComparisonEngine.from_sources(data_dir)


def render_player_comparison_lab():
    st.title("Player Comparison Lab")
    st.caption("HISTORICAL OBSERVATIONS · DUCKDB + PARQUET · NO LLM CALLS")
    st.write("Compare two players within one explicit evidence window. Rates describe what was recorded; they are not forecasts or acquisition rankings.")
    try:
        data_dir = ROOT / "data"
        sources = source_paths(data_dir)
        versions = tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in sources.values())
        with st.spinner("Preparing validated comparison data..."):
            engine = _engine(str(data_dir), versions)
            if not all((engine.store / f"{name}.parquet").is_file() for name in sources):
                _engine.clear()
                engine = _engine(str(data_dir), versions)
        players = engine.players()
        if len(players)<2:
            raise ComparisonDataError("At least two observed player IDs are required.")
        first, last, match_count = engine.coverage()
        ids = sorted(players, key=lambda p:(players[p].casefold(), p))
        left, right = st.columns(2)
        player_a = left.selectbox("Player A", ids, index=ids.index("ba607b88") if "ba607b88" in ids else 0,
                                  format_func=lambda p:f"{players[p]} · {p}", key="comparison_player_a")
        available_b = [pid for pid in ids if pid!=player_a]
        player_b = right.selectbox("Player B", available_b, index=available_b.index("740742ef") if "740742ef" in available_b else 0,
                                   format_func=lambda p:f"{players[p]} · {p}", key="comparison_player_b")
        kind = st.radio("Comparison type", ["Batting", "Bowling"], horizontal=True, key="comparison_type")
        dates = st.columns(2)
        start = dates[0].date_input("Historical start date (inclusive)", value=first, min_value=date(1900,1,1),
                                    max_value=date(2100,1,1), key="comparison_start")
        as_of = dates[1].date_input("Decision as-of date (exclusive)", value=last+timedelta(days=1),
                                    min_value=date(1900,1,1), max_value=date(2100,1,1), key="comparison_cutoff")
        phase = st.selectbox("Analytical window", list(PHASES), key="comparison_phase")
        st.caption(f"IPL only · {start} ≤ match date < {as_of} · {phase} · regular innings only. "
                   "These controls apply only to this Lab; the specialist agent workspaces retain their own scopes.")
        if as_of>last+timedelta(days=1):
            st.info(f"The archive ends on {last}; choosing a later cutoff adds no observations.")
        query = engine.get_batting_comparison if kind=="Batting" else engine.get_bowling_comparison
        result = query(player_a, player_b, start, as_of, phase)
        result.insert(1, "Player", result.player_id.map(players))
        if kind=="Batting":
            metrics = [("runs","Runs",0),("balls_faced","Balls faced",0),("strike_rate","Strike rate",2),
                       ("batting_average","Batting average",2),("dot_ball_percentage","Batter dot %",2),
                       ("dismissals","Dismissals",0),("matches","Matches represented",0),("innings","Innings represented",0)]
        else:
            metrics = [("legal_balls","Legal balls",0),("runs_charged","Runs charged",0),("economy","Economy",2),
                       ("wickets","Bowler wickets",0),("bowling_strike_rate","Bowling strike rate",2),
                       ("dot_ball_percentage","Bowling dot %",2),("matches","Matches represented",0),("innings","Innings represented",0)]
        columns = st.columns(2)
        for column, (_, row) in zip(columns, result.iterrows()):
            with column:
                st.subheader(row.Player)
                st.caption(f"Cricsheet ID: {row.player_id}")
                for field, label, decimals in metrics:
                    value = row[field]
                    st.metric(label, "N/A" if pd.isna(value) else f"{value:,.{decimals}f}")
                exposure = row.balls_faced if kind=="Batting" else row.legal_balls
                if not row.matches:
                    st.info("Insufficient observations: no applicable events in this window. Rates are unavailable.")
                elif exposure==0:
                    st.warning("Events are present but the rate denominator is zero; rates are N/A.")
                else:
                    st.caption(f"Observed sample: {int(exposure):,} {'balls faced' if kind=='Batting' else 'legal deliveries'}. "
                               "No validated adequacy threshold or statistical confidence interval is applied.")
        st.download_button("Download comparison metrics", result.to_csv(index=False).encode(),
                           "player_comparison.csv", mime="text/csv")
        if phase!="Overall" and st.checkbox("Also show overall statistics for these dates", value=True):
            overall=query(player_a,player_b,start,as_of,"Overall")
            overall.insert(1,"Player",overall.player_id.map(players))
            st.subheader("Overall · same historical dates")
            st.dataframe(overall, width="stretch", hide_index=True)
        st.subheader("Phase profile · same historical dates")
        profiles=[]
        field="strike_rate" if kind=="Batting" else "economy"
        for window in list(PHASES)[1:]:
            rows=query(player_a,player_b,start,as_of,window)
            for _, row in rows.iterrows():
                profiles.append({"Player":players[row.player_id]+" · "+row.player_id,"Phase":window,
                                 "Rate":row[field],"Exposure":row.balls_faced if kind=="Batting" else row.legal_balls,
                                 "Matches":row.matches,"Innings":row.innings})
        profile=pd.DataFrame(profiles)
        st.dataframe(profile.rename(columns={"Rate":"Strike rate" if kind=="Batting" else "Economy"}), hide_index=True, width="stretch")
        chart=profile.pivot(index="Phase",columns="Player",values="Rate").reindex(list(PHASES)[1:])
        if chart.notna().any().any():
            st.bar_chart(chart, y_label="Strike rate" if kind=="Batting" else "Runs per six legal balls", stack=False)
        evidence=engine.evidence(player_a,player_b,start,as_of,phase,kind)
        matches=evidence["matches"]
        reduced = (matches.match_overs.lt(20).fillna(False)
                   | matches.method_raw.fillna("").ne("") | matches.reduced_target_recorded.fillna(False)) if len(matches) else pd.Series(dtype=bool)
        st.markdown("**Data limitations and metric definitions**")
        st.caption("Batting SR = 100 × runs / balls faced; average = runs / recorded batter dismissals. "
                   "Run-outs and retired-out count against the dismissed batter; retired hurt does not. "
                   "Bowling economy = 6 × charged runs / legal balls; bowling SR = legal balls / credited wickets. "
                   "Zero denominators yield N/A; a genuine zero rate with a positive denominator remains zero.")
        st.caption("Batting dots: zero batter runs on counted balls faced, including byes/leg-byes. Wides excluded; "
                   "source-counted no-balls included. Bowling dots: legal deliveries with zero TOTAL runs, so byes, "
                   "leg-byes and penalties prevent a team-scoreless dot. Runs charged exclude byes, leg-byes and penalties.")
        st.caption("Matches and innings count applicable events in the selected window, including a batter dismissal "
                   "without a faced ball. They are not all named squad appearances. Phase average uses only dismissals in that window.")
        st.warning("The Lab's fixed 1–6, 7–15 and 16–20 over windows are analytical bands, not verified official powerplays. "
                   "They differ from the existing Moneyball middle/death bands. Shortened and DLS matches remain included.")
        if reduced.any():
            st.warning(f"{int(reduced.sum()):,} represented matches have reduced overs, an adjusted-result method or a reduced recorded target. "
                       "Phase comparisons may be less comparable; inspect match metadata below.")
        if len(matches) and matches.match_overs.isna().any():
            st.warning("Some represented matches lack planned-over metadata; do not assume standard playing conditions.")
        anomalies=engine.manifest["warnings"]["overs_with_more_than_six_legal_balls"]
        if anomalies:
            st.caption(f"Archive quality flag: {anomalies} overs record more than six legal balls. Source events are retained; "
                       "rate denominators use counted balls rather than over-number arithmetic.")
        if engine.manifest["warnings"]["missing_boundary_classification"]:
            st.info("Verified physical-boundary counts and percentages are unavailable: the supplied cleaned CSV lacks non-boundary classification. "
                    "No four/six-run event is silently treated as a verified boundary.")
        st.caption("Raw observations only. No acquisition winner, confidence interval, peer ranking or ability estimate is produced. "
                   "Cricsheet-derived research data are not independent scorecard certification. Data attribution: Cricsheet, cricsheet.org.")
        with st.expander("Evidence and Source Records"):
            st.caption(f"Complete metrics use all {evidence['delivery_count']:,} relevant source events. "
                       "Batting evidence also includes selected non-striker events for dismissal traceability. "
                       "Delivery and wicket previews are capped at 200 rows each; match metadata and match series cover the whole selection.")
            st.markdown("**Represented matches, source hashes and conditions**")
            st.dataframe(matches, hide_index=True, width="stretch")
            st.markdown("**Delivery records**")
            st.dataframe(evidence["deliveries"], hide_index=True, width="stretch")
            st.markdown("**Dismissal events**")
            st.dataframe(evidence["wickets"], hide_index=True, width="stretch")
            st.markdown("**Complete match-level series for selected players**")
            st.dataframe(evidence["series"], hide_index=True, width="stretch")
            st.download_button("Download match-level series",evidence["series"].to_csv(index=False).encode(),"comparison_match_series.csv","text/csv")
            provenance = {"scope": {"player_ids": [player_a,player_b], "comparison_type": kind,
                                    "start_inclusive": start.isoformat(), "decision_as_of_exclusive": as_of.isoformat(),
                                    "phase": phase, "competition": "IPL", "super_overs_excluded": True},
                          "metrics_version": METRICS_VERSION, "dataset_manifest": engine.manifest}
            st.json(provenance)
            st.download_button("Download evidence scope and source manifest", json.dumps(provenance,indent=2).encode(),
                               "comparison_evidence_scope.json", "application/json")
    except (ComparisonDataError, OSError, ValueError, KeyError) as exc:
        st.error(str(exc))
        st.info("Check the comparison source files and dates. Other workspaces remain available.")
        if st.button("Rebuild comparison cache"):
            _engine.clear()
            st.rerun()
