/* Sports Bar Search — refined mobile UX
 *
 * One smart search box + tappable refinements. Typing "bills rugby" filters by
 * team AND sport because every free-text token must match somewhere on the bar.
 * City / team / sport / carrier chips are hard filters; proximity, TV count and
 * live games on now drive the ranking.
 */
(() => {
  const DATA = window.SPORTSBAR;
  const $ = (id) => document.getElementById(id);

  // ---- derive vocab from data ----
  const uniq = (key) => [...new Set(DATA.bars.flatMap((b) => b[key]))].sort();
  const VOCAB = {
    teams: uniq("teams"),
    sports: uniq("sports"),
    carriers: uniq("carriers"),
    cities: [...new Set(DATA.bars.map((b) => b.city))].sort(),
  };

  // ---- state ----
  const state = {
    query: "",
    teams: new Set(),
    sports: new Set(),
    carriers: new Set(),
    city: null,
    originLabel: null, // key into DATA.origins, or null = anywhere
    onNow: false,
    hour: new Date().getHours(),
    demo: true, // treat all games as live so "on now" is always demoable
  };

  // ---- helpers ----
  const norm = (s) => s.toLowerCase();
  const milesBetween = (a, b) => {
    const R = 3958.8, toRad = (d) => (d * Math.PI) / 180;
    const dLat = toRad(b.lat - a.lat), dLon = toRad(b.lon - a.lon);
    const x = Math.sin(dLat / 2) ** 2 +
      Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.asin(Math.sqrt(x));
  };

  const liveGames = () =>
    state.demo ? DATA.games : DATA.games.filter((g) => g.start <= state.hour && state.hour < g.end);

  const liveAtBar = (bar, games) => {
    const carriers = new Set(bar.carriers);
    return games.filter((g) => carriers.has(g.carrier));
  };

  // free-text: every token must hit name / hood / city / team / sport / carrier
  const haystack = (bar) =>
    norm([bar.name, bar.neighborhood, bar.city, ...bar.teams, ...bar.sports, ...bar.carriers].join(" "));

  const activeFilterCount = () =>
    state.teams.size + state.sports.size + state.carriers.size +
    (state.city ? 1 : 0) + (state.onNow ? 1 : 0);

  // ---- search + rank ----
  function search() {
    const games = liveGames();
    const origin = state.originLabel ? DATA.origins[state.originLabel] : null;
    const tokens = state.query.split(/\s+/).map(norm).filter(Boolean);

    const out = [];
    for (const bar of DATA.bars) {
      if (state.city && bar.city !== state.city) continue;
      if ([...state.teams].some((t) => !bar.teams.includes(t))) continue;
      if ([...state.sports].some((s) => !bar.sports.includes(s))) continue;
      if ([...state.carriers].some((c) => !bar.carriers.includes(c))) continue;

      const hs = haystack(bar);
      if (tokens.length && !tokens.every((t) => hs.includes(t))) continue;

      const onNow = liveAtBar(bar, games);
      if (state.onNow && onNow.length === 0) continue;

      let score = 10 * state.teams.size + 5 * state.sports.size + 3 * state.carriers.size;
      score += 2 * onNow.length + Math.min(bar.tv_count, 25) / 10;
      let miles = null;
      if (origin) { miles = milesBetween(origin, bar); score += Math.max(0, 6 - miles); }

      out.push({ bar, score, onNow, miles });
    }
    out.sort((a, b) => b.score - a.score);
    return out;
  }

  // ---- render ----
  function reasonTags(bar) {
    const tags = [];
    const hit = (set, val) => set.has(val);
    bar.teams.forEach((t) => tags.push({ text: `🏟️ ${t}`, match: hit(state.teams, t) }));
    bar.sports.forEach((s) => tags.push({ text: s, match: hit(state.sports, s) }));
    // surface matched sports/teams first
    return tags.sort((a, b) => Number(b.match) - Number(a.match)).slice(0, 5);
  }

  function render() {
    const results = search();
    $("resultCount").textContent =
      results.length === 0 ? "No matches" : `${results.length} bar${results.length > 1 ? "s" : ""}`;
    $("applyCount").textContent = `${results.length} result${results.length === 1 ? "" : "s"}`;

    const fc = activeFilterCount();
    $("filterCount").hidden = fc === 0;
    $("filterCount").textContent = fc;

    const el = $("results");
    if (results.length === 0) {
      el.innerHTML = `<div class="empty">No bars match.<br/>Try removing a filter or widening your search.</div>`;
      return;
    }

    el.innerHTML = results.map(({ bar, onNow, miles }) => {
      const live = onNow.length > 0;
      const liveBadge = live
        ? `<div class="live-badge"><span class="dot"></span> On now</div>
           <div class="live-games">${onNow.slice(0, 3).map((g) => `${g.away} @ ${g.home} <span style="color:var(--muted)">· ${g.league}</span>`).join("<br/>")}</div>`
        : "";
      const onCarriers = new Set(onNow.map((g) => g.carrier));
      const carriers = bar.carriers
        .map((c) => `<span class="carrier ${onCarriers.has(c) ? "on" : ""}">${c}</span>`).join("");
      const tags = reasonTags(bar)
        .map((t) => `<span class="tag ${t.match ? "match" : ""}">${t.text}</span>`).join("");
      const events = bar.events.length
        ? `<div class="events">🎉 ${bar.events.map((e) => `${e.title} · ${e.recurring}`).join(" • ")}</div>`
        : "";
      const dist = miles != null ? `<span class="dist">${miles.toFixed(1)} mi</span>` : "";

      return `<article class="card ${live ? "live" : ""}">
        <div class="card-top">
          <div>
            <h3>${bar.name}</h3>
            <div class="meta">${bar.neighborhood}, ${bar.city} · ${bar.tv_count} TVs</div>
          </div>
          ${dist}
        </div>
        ${liveBadge}
        <div class="reasons">${tags}</div>
        <div class="carriers">${carriers}</div>
        ${events}
      </article>`;
    }).join("");
  }

  // ---- active filter pills ----
  function renderActive() {
    const pills = [];
    const add = (label, onRemove) => pills.push({ label, onRemove });
    if (state.city) add(`📍 ${state.city}`, () => (state.city = null));
    if (state.onNow) add(`🔴 On now`, () => (state.onNow = false));
    state.teams.forEach((t) => add(`🏟️ ${t}`, () => state.teams.delete(t)));
    state.sports.forEach((s) => add(s, () => state.sports.delete(s)));
    state.carriers.forEach((c) => add(`🛰️ ${c}`, () => state.carriers.delete(c)));

    const row = $("activeRow");
    row.innerHTML = "";
    pills.forEach((p) => {
      const el = document.createElement("span");
      el.className = "pill";
      el.innerHTML = `${p.label} <button aria-label="Remove">✕</button>`;
      el.querySelector("button").onclick = () => { p.onRemove(); syncQuickChips(); renderActive(); render(); };
      row.appendChild(el);
    });
  }

  // ---- quick chips (popular one-tap refinements) ----
  const QUICK = [
    { kind: "live", label: "🔴 On now" },
    { kind: "team", value: "Buffalo Bills", label: "Bills" },
    { kind: "team", value: "San Francisco 49ers", label: "49ers" },
    { kind: "sport", value: "Rugby", label: "Rugby" },
    { kind: "sport", value: "Premier League", label: "Premier League" },
    { kind: "carrier", value: "DirecTV", label: "DirecTV" },
    { kind: "carrier", value: "MLB.tv", label: "MLB.tv" },
  ];
  function isQuickOn(q) {
    if (q.kind === "live") return state.onNow;
    if (q.kind === "team") return state.teams.has(q.value);
    if (q.kind === "sport") return state.sports.has(q.value);
    if (q.kind === "carrier") return state.carriers.has(q.value);
  }
  function toggleQuick(q) {
    if (q.kind === "live") state.onNow = !state.onNow;
    else {
      const set = state[q.kind + "s"];
      set.has(q.value) ? set.delete(q.value) : set.add(q.value);
    }
  }
  function buildQuickChips() {
    const row = $("quickRow");
    row.innerHTML = "";
    QUICK.forEach((q) => {
      const el = document.createElement("button");
      el.className = `chip ${q.kind === "live" ? "live" : ""}`;
      el.textContent = q.label;
      el.onclick = () => { toggleQuick(q); el.classList.toggle("on"); renderActive(); render(); };
      el.dataset.kind = q.kind; el.dataset.value = q.value || "";
      row.appendChild(el);
    });
    syncQuickChips();
  }
  function syncQuickChips() {
    document.querySelectorAll("#quickRow .chip").forEach((el, i) => {
      el.classList.toggle("on", isQuickOn(QUICK[i]));
    });
  }

  // ---- filter sheet ----
  function buildSheet() {
    const groups = [
      { title: "Team home bar", kind: "teams", opts: VOCAB.teams },
      { title: "Sports shown", kind: "sports", opts: VOCAB.sports },
      { title: "Carrier / provider", kind: "carriers", opts: VOCAB.carriers },
    ];
    const body = $("sheetBody");
    body.innerHTML = "";

    // City
    const cityGroup = document.createElement("div");
    cityGroup.className = "filter-group";
    cityGroup.innerHTML = `<h4>City</h4><div class="opt-wrap"></div>`;
    ["Any", ...VOCAB.cities].forEach((c) => {
      const o = document.createElement("button");
      o.className = "opt"; o.textContent = c;
      const isOn = c === "Any" ? !state.city : state.city === c;
      o.classList.toggle("on", isOn);
      o.onclick = () => {
        state.city = c === "Any" ? null : c;
        cityGroup.querySelectorAll(".opt").forEach((x) => x.classList.remove("on"));
        o.classList.add("on");
        liveRefresh();
      };
      cityGroup.querySelector(".opt-wrap").appendChild(o);
    });
    body.appendChild(cityGroup);

    // Multi-select groups
    groups.forEach((g) => {
      const grp = document.createElement("div");
      grp.className = "filter-group";
      grp.innerHTML = `<h4>${g.title}</h4><div class="opt-wrap"></div>`;
      g.opts.forEach((val) => {
        const o = document.createElement("button");
        o.className = "opt"; o.textContent = val;
        o.classList.toggle("on", state[g.kind].has(val));
        o.onclick = () => {
          const set = state[g.kind];
          set.has(val) ? set.delete(val) : set.add(val);
          o.classList.toggle("on");
          liveRefresh();
        };
        grp.querySelector(".opt-wrap").appendChild(o);
      });
      body.appendChild(grp);
    });

    // "On now" + time-of-day
    const live = document.createElement("div");
    live.className = "filter-group";
    live.innerHTML = `<h4>What's on</h4>
      <div class="opt-wrap" style="margin-bottom:12px">
        <button class="opt" id="optOnNow">🔴 Only bars with a game on now</button>
        <button class="opt" id="optDemo">Demo mode (all games live)</button>
      </div>
      <div class="slider-row">
        <span style="color:var(--muted);font-size:.8rem">Time</span>
        <input type="range" id="hourRange" min="0" max="23" value="${state.hour}" />
        <span id="hourLbl" style="width:48px;text-align:right">${state.hour}:00</span>
      </div>`;
    body.appendChild(live);

    const optOnNow = live.querySelector("#optOnNow");
    optOnNow.classList.toggle("on", state.onNow);
    optOnNow.onclick = () => { state.onNow = !state.onNow; optOnNow.classList.toggle("on"); liveRefresh(); };

    const optDemo = live.querySelector("#optDemo");
    const hourRange = live.querySelector("#hourRange");
    const hourLbl = live.querySelector("#hourLbl");
    const syncDemo = () => { optDemo.classList.toggle("on", state.demo); hourRange.disabled = state.demo; };
    optDemo.onclick = () => { state.demo = !state.demo; syncDemo(); liveRefresh(); };
    hourRange.oninput = () => { state.hour = +hourRange.value; hourLbl.textContent = `${state.hour}:00`; liveRefresh(); };
    syncDemo();
  }

  function liveRefresh() { syncQuickChips(); renderActive(); render(); }

  function openSheet() { buildSheet(); $("sheetScrim").hidden = false; $("sheet").hidden = false; }
  function closeSheet() { $("sheetScrim").hidden = true; $("sheet").hidden = true; }

  // ---- near / location ----
  function cycleOrigin() {
    const keys = [null, ...Object.keys(DATA.origins)];
    const idx = keys.indexOf(state.originLabel);
    state.originLabel = keys[(idx + 1) % keys.length];
    $("nearLabel").textContent = state.originLabel || "Anywhere";
    render();
  }

  // ---- wire up ----
  function init() {
    buildQuickChips();
    renderActive();
    render();

    const search = $("search");
    search.addEventListener("input", () => {
      state.query = search.value;
      $("clearSearch").hidden = !search.value;
      render();
    });
    $("clearSearch").onclick = () => {
      search.value = ""; state.query = ""; $("clearSearch").hidden = true; search.focus(); render();
    };

    $("nearBtn").onclick = cycleOrigin;
    $("filterBtn").onclick = openSheet;
    $("applyFilters").onclick = closeSheet;
    $("sheetScrim").onclick = closeSheet;
    $("resetFilters").onclick = () => {
      state.teams.clear(); state.sports.clear(); state.carriers.clear();
      state.city = null; state.onNow = false;
      buildSheet(); liveRefresh();
    };
  }

  init();
})();
