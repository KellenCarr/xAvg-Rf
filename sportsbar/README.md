# Sports Bar Search (prototype)

A **mobile-first** sports-bar finder. Discover a bar by **team affiliation**,
**sport/league**, **carrier/provider** (DirecTV, Xfinity, MLB.tv, NFL Sunday
Ticket…), **location**, and **what's actually on TV right now**.

The motivating query:

> "Is there a Buffalo Bills bar in San Francisco that also shows rugby?"

## Refined search UX

- **One smart search box** — type `bills rugby` or `directv near me`; every
  token must match the bar (name, neighborhood, team, sport, or carrier), so
  free text doubles as multi-facet filtering.
- **Quick chips** — one-tap toggles for the most common refinements
  (On now, Bills, Rugby, DirecTV, …).
- **Active filters** show as removable pills, so the current search is always visible.
- **Slide-up filter sheet** for the full faceted set (team / sport / carrier /
  city / what's on / time of day).
- Touch-sized targets, sticky search, dark game-day theme, responsive up to desktop.

## Model

Each bar has two layers:

1. **Static profile** — location, `carriers`, `teams`, `sports`, `tv_count`,
   recurring `events`.
2. **Live schedule** — today's `games` matched against the carriers a bar
   actually subscribes to, so "on now" reflects what *that* bar can show.

City / team / sport / carrier are hard filters; proximity, TV count, and live
games on now feed the ranking.

## Run

No build step, no server required — it's plain HTML/CSS/JS:

```bash
open sportsbar/web/index.html        # macOS
# or just open the file in any browser / host the web/ folder on any static host
```

`data.js` holds the seed bars and a mock day-of game schedule. Swap it for a
real API later.

## Next steps

- Bar-owner self-listing (supply side)
- Real sports-schedule / TV-listing feeds
- Browser geolocation for true "near me"
