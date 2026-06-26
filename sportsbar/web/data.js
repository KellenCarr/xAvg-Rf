// Seed data for the Sports Bar Search prototype.
// Canonical source — the app reads window.SPORTSBAR directly so it runs with
// zero setup (open index.html, no server needed). Replace with a real API later.
window.SPORTSBAR = {
  // Origin presets so "near me" is demoable without device geolocation.
  origins: {
    "Downtown SF": { lat: 37.7793, lon: -122.4193 },
    "Mission, SF": { lat: 37.7599, lon: -122.4148 },
    "Downtown Oakland": { lat: 37.8044, lon: -122.2712 },
  },

  // Today's games. "on now" at a bar = a game whose carrier the bar subscribes to.
  games: [
    { league: "NFL", away: "Buffalo Bills", home: "Kansas City Chiefs", carrier: "NFL Sunday Ticket", start: 13, end: 16 },
    { league: "NFL", away: "San Francisco 49ers", home: "Seattle Seahawks", carrier: "DirecTV", start: 13, end: 16 },
    { league: "Rugby", away: "Ireland", home: "England", carrier: "Premier Sports", start: 8, end: 10 },
    { league: "Rugby", away: "Saracens", home: "Leinster", carrier: "ESPN+", start: 9, end: 11 },
    { league: "Premier League", away: "Liverpool FC", home: "Manchester United", carrier: "Peacock", start: 7, end: 9 },
    { league: "MLB", away: "San Francisco Giants", home: "Los Angeles Dodgers", carrier: "MLB.tv", start: 19, end: 22 },
    { league: "NBA", away: "Golden State Warriors", home: "Boston Celtics", carrier: "Xfinity", start: 19, end: 21 },
    { league: "Champions League", away: "Manchester United", home: "Real Madrid", carrier: "Premier Sports", start: 12, end: 14 },
  ],

  bars: [
    {
      id: "the-end-up", name: "The End Up", city: "San Francisco", neighborhood: "SoMa",
      lat: 37.7706, lon: -122.4083, tv_count: 18,
      carriers: ["DirecTV", "Xfinity", "ESPN+", "MLB.tv"],
      teams: ["Buffalo Bills", "San Francisco Giants"],
      sports: ["NFL", "MLB", "Rugby", "Premier League"],
      events: [
        { title: "Bills Mafia Watch Party", league: "NFL", recurring: "Sunday" },
        { title: "Six Nations Mornings", league: "Rugby", recurring: "Saturday" },
      ],
    },
    {
      id: "pilsner-inn", name: "Pilsner Inn", city: "San Francisco", neighborhood: "Castro",
      lat: 37.7649, lon: -122.4309, tv_count: 8,
      carriers: ["Xfinity", "ESPN+"],
      teams: ["San Francisco 49ers"],
      sports: ["NFL", "NBA", "MLS"],
      events: [{ title: "Niners Faithful", league: "NFL", recurring: "Sunday" }],
    },
    {
      id: "danny-coyles", name: "Danny Coyle's", city: "San Francisco", neighborhood: "Lower Haight",
      lat: 37.7715, lon: -122.4332, tv_count: 10,
      carriers: ["DirecTV", "Peacock"],
      teams: ["Buffalo Bills", "Liverpool FC"],
      sports: ["NFL", "Premier League", "Rugby", "Gaelic Football"],
      events: [
        { title: "Bills Backers SF", league: "NFL", recurring: "Sunday" },
        { title: "Rugby Union Saturdays", league: "Rugby", recurring: "Saturday" },
      ],
    },
    {
      id: "kezar-pub", name: "Kezar Pub", city: "San Francisco", neighborhood: "Cole Valley",
      lat: 37.7669, lon: -122.4527, tv_count: 14,
      carriers: ["DirecTV", "Xfinity", "ESPN+", "Premier Sports"],
      teams: ["Manchester United", "San Francisco Giants"],
      sports: ["Premier League", "Rugby", "MLB", "NFL", "Champions League"],
      events: [{ title: "Premier League Breakfast", league: "Premier League", recurring: "Saturday" }],
    },
    {
      id: "the-page", name: "The Page", city: "San Francisco", neighborhood: "Lower Haight",
      lat: 37.7723, lon: -122.4302, tv_count: 6,
      carriers: ["Xfinity"],
      teams: ["Golden State Warriors"],
      sports: ["NBA", "NFL"],
      events: [],
    },
    {
      id: "buffalo-backers-oakland", name: "Buffalo Bills Backers — Oakland", city: "Oakland", neighborhood: "Downtown",
      lat: 37.8044, lon: -122.2712, tv_count: 22,
      carriers: ["DirecTV", "MLB.tv", "ESPN+", "NFL Sunday Ticket"],
      teams: ["Buffalo Bills"],
      sports: ["NFL", "MLB", "NHL", "Rugby"],
      events: [{ title: "Bills Mafia East Bay", league: "NFL", recurring: "Sunday" }],
    },
  ],
};
