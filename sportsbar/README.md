# Sports Bar Search (prototype)

Faceted discovery for sports bars: find a bar by **team affiliation**, **sport/league**,
**carrier/provider** (DirecTV, Xfinity, MLB.tv, NFL Sunday Ticket, …), **location**, and
**what's actually on TV right now**.

The motivating query:

> "Is there a Buffalo Bills bar in San Francisco that also shows rugby?"

## Model

Each bar has two layers:

1. **Static profile** — location, `carriers`, `team_affiliations`, `sports`, `tv_count`,
   recurring `events`.
2. **Live schedule** — today's `games` are matched against the carriers a bar actually
   subscribes to, so "on now" reflects what that specific bar can show.

Search is **faceted**: city / team / sport / carrier are hard filters (must all match);
proximity, TV count, and live games on now feed the **ranking** score.

## Run

```bash
pip install -r ../requirements.txt
streamlit run sportsbar_app.py
```

## Data

- `data/bars.json` — seed bars (hand-authored)
- `data/games.json` — mock day-of game schedule used for the "on now" feature

Both are seed/demo data. Next steps: bar-owner self-listing, real sports-schedule /
TV-listing feeds, and geolocation for true "near me".
