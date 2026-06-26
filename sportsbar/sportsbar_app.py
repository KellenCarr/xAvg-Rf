"""
Sports Bar Search — prototype

Faceted discovery for "find me a bar that shows the games I care about."
Answers questions like:

    "Is there a Buffalo Bills bar in San Francisco that also shows rugby?"
    "Who carries the MLB.tv app near me?"
    "What's actually on TV right now?"

A bar is modeled in two layers:
  1. Static profile  -> location, carriers (DirecTV / Xfinity / MLB.tv / ...),
                         team affiliations, sports regularly shown, recurring events.
  2. Live schedule   -> which game could be on right now, derived from the day's
                         games + the carriers the bar actually subscribes to.

Run:  streamlit run sportsbar/sportsbar_app.py
"""

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
@st.cache_data
def load_bars():
    return json.loads((DATA_DIR / "bars.json").read_text())


@st.cache_data
def load_games():
    return json.loads((DATA_DIR / "games.json").read_text())


def unique_values(bars, key):
    values = set()
    for bar in bars:
        values.update(bar.get(key, []))
    return sorted(values)


# --------------------------------------------------------------------------- #
# Live "what's on right now"
# --------------------------------------------------------------------------- #
def games_on_now(games, hour, demo_mode):
    """Games that are live at `hour` (or all of them in demo mode)."""
    if demo_mode:
        return games
    return [g for g in games if g["start_hour"] <= hour < g["end_hour"]]


def live_at_bar(bar, live_games):
    """A bar can show a live game only if it carries the right provider."""
    carriers = set(bar.get("carriers", []))
    return [g for g in live_games if g["carrier"] in carriers]


# --------------------------------------------------------------------------- #
# Scoring / ranking
# --------------------------------------------------------------------------- #
def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def score_bar(bar, filters, origin, live_games):
    """
    Returns (score, reasons) or (None, _) if the bar fails a hard filter.

    Hard filters (must match all selected): city, team, sport, carrier.
    Soft signal: live games on now, TV count, proximity -> ranking only.
    """
    reasons = []

    if filters["city"] and bar["city"] != filters["city"]:
        return None, reasons

    for team in filters["teams"]:
        if team not in bar.get("team_affiliations", []):
            return None, reasons
    for team in filters["teams"]:
        reasons.append(f"🏟️ {team} home bar")

    for sport in filters["sports"]:
        if sport not in bar.get("sports", []):
            return None, reasons
    for sport in filters["sports"]:
        reasons.append(f"📺 shows {sport}")

    for carrier in filters["carriers"]:
        if carrier not in bar.get("carriers", []):
            return None, reasons
    for carrier in filters["carriers"]:
        reasons.append(f"🛰️ has {carrier}")

    on_now = live_at_bar(bar, live_games)
    if filters["live_only"] and not on_now:
        return None, reasons

    score = 0.0
    score += 10 * len(filters["teams"])
    score += 5 * len(filters["sports"])
    score += 3 * len(filters["carriers"])
    score += 2 * len(on_now)
    score += min(bar["tv_count"], 25) / 10.0

    if on_now:
        labels = ", ".join(f"{g['away']} @ {g['home']}" for g in on_now[:3])
        reasons.append(f"🔴 on now: {labels}")

    if origin:
        miles = haversine_miles(origin[0], origin[1], bar["lat"], bar["lon"])
        score += max(0, 5 - miles)  # closer = better
        reasons.append(f"📍 {miles:.1f} mi away")

    return score, reasons


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Sports Bar Search", page_icon="🍻", layout="wide")
st.markdown("# 🍻 Sports Bar Search")
st.caption(
    "Find the right bar by team, sport, carrier, and what's on right now — "
    'e.g. *"a Buffalo Bills bar in SF that also shows rugby."*'
)

bars = load_bars()
games = load_games()

# Origin presets so "near me" is demoable without geolocation.
ORIGINS = {
    "— anywhere —": None,
    "Downtown SF": (37.7793, -122.4193),
    "Mission, SF": (37.7599, -122.4148),
    "Downtown Oakland": (37.8044, -122.2712),
}

with st.sidebar:
    st.header("Search")
    city = st.selectbox("City", ["— any —"] + sorted({b["city"] for b in bars}))
    teams = st.multiselect("Team home bar", unique_values(bars, "team_affiliations"))
    sports = st.multiselect("Sports shown", unique_values(bars, "sports"))
    carriers = st.multiselect("Carrier / provider", unique_values(bars, "carriers"))

    st.divider()
    origin_label = st.selectbox("Near", list(ORIGINS.keys()))
    st.divider()

    st.subheader("What's on")
    demo_mode = st.toggle("Demo mode (treat all games as live)", value=True)
    hour = st.slider("Time of day", 0, 23, datetime.now().hour, disabled=demo_mode)
    live_only = st.toggle("Only bars with a game on right now", value=False)

filters = {
    "city": None if city == "— any —" else city,
    "teams": teams,
    "sports": sports,
    "carriers": carriers,
    "live_only": live_only,
}
origin = ORIGINS[origin_label]
live_games = games_on_now(games, hour, demo_mode)

# Rank.
ranked = []
for bar in bars:
    score, reasons = score_bar(bar, filters, origin, live_games)
    if score is not None:
        ranked.append((score, bar, reasons))
ranked.sort(key=lambda x: x[0], reverse=True)

st.markdown(f"### {len(ranked)} bar(s) match")

if not ranked:
    st.info("No bars match every filter. Try removing a filter.")

for score, bar, reasons in ranked:
    with st.container(border=True):
        left, right = st.columns([3, 1])
        with left:
            st.markdown(f"#### {bar['name']}")
            st.caption(f"{bar['neighborhood']}, {bar['city']} · {bar['tv_count']} TVs")
            for reason in reasons:
                st.write(reason)
            if bar.get("events"):
                ev = ", ".join(f"{e['title']} ({e['recurring']})" for e in bar["events"])
                st.write(f"🎉 events: {ev}")
        with right:
            st.metric("match score", f"{score:.0f}")
            st.write("**Carriers**")
            st.write(", ".join(bar["carriers"]))

with st.expander("Map of matches"):
    if ranked:
        st.map(pd.DataFrame([{"lat": b["lat"], "lon": b["lon"]} for _, b, _ in ranked]))
