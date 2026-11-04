<script>
  import { onMount } from "svelte";
  // Stub on main; the ghpages branch ships real sample data here.
  import { MOCK_STORES, mockMenu } from "./mock.js";

  // Empty = same origin (served by the API container). Set VITE_API_URL at build
  // time to point a statically hosted build at an API host; VITE_USE_MOCK=true
  // (ghpages branch) serves sample data instead of calling any API.
  const API = import.meta.env.VITE_API_URL || "";
  const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

  const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  let stores = [];
  let store = "";
  let menusByWeek = {};        // week number -> {week: "CW: n", days: [...]}
  let availableDates = new Set();  // ISO dates that have menu data
  let dateToWeek = new Map();      // ISO date -> week number
  let dateToWeekday = new Map();   // ISO date -> weekday name
  let loading = true;
  let error = "";
  let viewMonth = monthOf(new Date());
  let selectedIso = null;

  function monthOf(d) {
    return new Date(d.getFullYear(), d.getMonth(), 1);
  }
  function addMonths(d, n) {
    return new Date(d.getFullYear(), d.getMonth() + n, 1);
  }
  function isoOf(y, m, day) {
    return `${y}-${String(m + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }
  function todayIso() {
    const d = new Date();
    return isoOf(d.getFullYear(), d.getMonth(), d.getDate());
  }
  function isoWeekInfo(d) {
    // ISO-8601 week number; the week's year is the year of its Thursday
    const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = (t.getUTCDay() + 6) % 7; // Monday = 0
    t.setUTCDate(t.getUTCDate() - day + 3);
    const jan4 = new Date(Date.UTC(t.getUTCFullYear(), 0, 4));
    const jan4day = (jan4.getUTCDay() + 6) % 7;
    jan4.setUTCDate(jan4.getUTCDate() - jan4day + 3);
    return { year: t.getUTCFullYear(), week: 1 + Math.round((t - jan4) / (7 * 864e5)) };
  }
  function mondayOfIsoWeek(year, week) {
    const jan4 = new Date(Date.UTC(year, 0, 4));
    jan4.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() + 6) % 7));
    jan4.setUTCDate(jan4.getUTCDate() + (week - 1) * 7);
    return jan4;
  }
  function weeksOfMonth(m) {
    const first = new Date(m.getFullYear(), m.getMonth(), 1);
    const last = new Date(m.getFullYear(), m.getMonth() + 1, 0);
    const keys = new Set();
    for (let d = new Date(first); d <= last; d.setDate(d.getDate() + 1)) {
      const wi = isoWeekInfo(d);
      keys.add(wi.week);
    }
    return [...keys];
  }

  let lastStore = "";
  const inflight = new Set();

  async function initOrNavigate(s, m) {
    if (s !== lastStore) {
      lastStore = s;
      menusByWeek = {};
      availableDates = new Set();
      dateToWeek = new Map();
      dateToWeekday = new Map();
      selectedIso = null;
    }
    await ensureMonth(m);
    if (!selectedIso) {
      const today = todayIso();
      selectedIso = availableDates.has(today) ? today : [...availableDates].sort()[0] ?? null;
    }
  }

  async function fetchWeek(week) {
    if (USE_MOCK) return mockMenu(store, week);
    const params = new URLSearchParams({ store, week });
    const res = await fetch(`${API}/api/menu?${params}`);
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
    return body;
  }

  async function ensureMonth(m) {
    const missing = weeksOfMonth(m).filter((w) => !(w in menusByWeek) && !inflight.has(w));
    if (!missing.length) return;
    for (const w of missing) inflight.add(w);
    loading = true;
    error = "";
    const results = await Promise.allSettled(missing.map((w) => fetchWeek(w).then((body) => [w, body])));
    const dates = new Set(availableDates);
    const toWeek = new Map(dateToWeek);
    const toWeekday = new Map(dateToWeekday);
    let anyOk = false;
    for (const r of results) {
      const w = missing[results.indexOf(r)];
      inflight.delete(w);
      if (r.status !== "fulfilled") continue; // week not offered by the portal
      const body = r.value[1];
      menusByWeek[w] = body;
      anyOk = true;
      for (const day of body.days) {
        if (!day.meals.length) continue; // empty days are not selectable
        const idx = WEEKDAYS.indexOf(day.weekday) + 1; // 1..7 Mon..Sun
        if (idx < 1) continue;
        const d = mondayOfIsoWeek(new Date().getFullYear(), w);
        // boundary: week 1 fetched late in the year belongs to the next ISO year
        if (w === 1 && new Date().getMonth() === 11) d.setUTCFullYear(d.getUTCFullYear() + 1);
        d.setUTCDate(d.getUTCDate() + idx - 1);
        const iso = d.toISOString().slice(0, 10);
        dates.add(iso);
        toWeek.set(iso, w);
        toWeekday.set(iso, day.weekday);
      }
    }
    availableDates = dates;
    dateToWeek = toWeek;
    dateToWeekday = toWeekday;
    if (!anyOk && !Object.keys(menusByWeek).length) error = "Menu unavailable right now.";
    loading = false;
  }

  function selectDay(iso) {
    selectedIso = iso;
  }

  $: initOrNavigate(store, viewMonth);
  $: monthLabel = `${MONTHS[viewMonth.getMonth()]} ${viewMonth.getFullYear()}`;
  $: canGoBack = viewMonth > monthOf(new Date());
  $: cells = buildCells(viewMonth, availableDates);
  $: weekOfSelected = selectedIso ? dateToWeek.get(selectedIso) : null;
  $: activeDays = weekOfSelected != null && menusByWeek[weekOfSelected] ? menusByWeek[weekOfSelected].days : [];
  $: activeDay = selectedIso ? dateToWeekday.get(selectedIso) : null;
  $: activeMeals = activeDays.find((d) => d.weekday === activeDay)?.meals ?? [];
  $: selectedLong = selectedIso
    ? `${dateToWeekday.get(selectedIso)?.slice(0, 3)} ${selectedIso.slice(8)}.${selectedIso.slice(5, 7)}.`
    : "";

  function buildCells(m, avail) {
    const y = m.getFullYear(), mo = m.getMonth();
    const daysInMonth = new Date(y, mo + 1, 0).getDate();
    const offset = (new Date(y, mo, 1).getDay() + 6) % 7; // Monday-first
    const list = [];
    for (let i = 0; i < offset; i++) list.push(null);
    for (let day = 1; day <= daysInMonth; day++) {
      const iso = isoOf(y, mo, day);
      list.push({ iso, day, available: avail.has(iso) });
    }
    return list;
  }

  onMount(async () => {
    if (USE_MOCK) stores = MOCK_STORES;
    else stores = await (await fetch(`${API}/api/stores`)).json();
    store = stores.find((s) => s.name === "Airbus Finkenwerder")?.name ?? stores[0]?.name ?? "";
  });
</script>

<main>
  <header>
    <h1>AirFood</h1>
    <label class="store">
      <span class="visually-hidden">Canteen</span>
      <select bind:value={store}>
        {#each stores as s}
          <option value={s.name}>{s.name}</option>
        {/each}
      </select>
    </label>
  </header>

  <section class="calendar" aria-label="Pick a day">
    <div class="cal-head">
      <button on:click={() => (viewMonth = addMonths(viewMonth, -1))} disabled={!canGoBack} aria-label="Previous month">‹</button>
      <span class="month">{monthLabel}</span>
      <button on:click={() => (viewMonth = addMonths(viewMonth, 1))} aria-label="Next month">›</button>
    </div>
    <div class="grid">
      {#each ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"] as w}
        <span class="dow">{w}</span>
      {/each}
      {#each cells as c}
        {#if c}
          <button
            class:available={c.available}
            class:selected={c.iso === selectedIso}
            class:today={c.iso === todayIso()}
            disabled={!c.available || loading}
            on:click={() => selectDay(c.iso)}
          >{c.day}</button>
        {:else}
          <span></span>
        {/if}
      {/each}
    </div>
  </section>

  {#if loading && !Object.keys(menusByWeek).length}
    <p class="quiet">Loading the menu…</p>
  {:else if error}
    <p class="error">Menu unavailable right now.</p>
    <button class="retry" on:click={() => ensureMonth(viewMonth)}>Retry</button>
  {:else if selectedIso}
    <h2 class="board-title">{selectedLong}</h2>
    {#if activeMeals.length}
      <section class="board">
        {#each activeMeals as meal}
          <article class="dish">
            {#if meal.image_url}<img src={meal.image_url} alt="" loading="lazy" />{/if}
            <div class="line">
              <h3>{meal.name}</h3>
              <p class="price">
                {#if meal.price_options?.length > 1}
                  {#each meal.price_options as p}
                    <span>{p.label ? `${p.label} ` : ""}{p.amount}</span>
                  {/each}
                {:else}
                  <span>{meal.price ?? "—"}</span>
                {/if}
              </p>
            </div>
            <p class="meta">
              {#if meal.category}<span class="cat">{meal.category}</span>{/if}
              {#if meal.allergens?.length}<span class="all">Allergens {meal.allergens.join(" ")}</span>{/if}
              {#each meal.tags ?? [] as t}
                {#if t.name}<span class="tag">{t.name}</span>{/if}
              {/each}
            </p>
          </article>
        {/each}
      </section>
    {:else}
      <p class="quiet">No menu for this day.</p>
    {/if}
  {/if}

  <footer>
    <p>Prices in EUR · allergen codes as shown on the portal</p>
  </footer>
</main>

<style>
  main { max-width: 560px; margin: 0 auto; padding: 1.25rem 1rem 3rem; }

  header { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem .75rem; }
  h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em; margin: 0 auto 0 0; color: #1e5c48; }
  .store select {
    font: inherit; font-size: .9rem; color: #2b2724;
    background: #fff; border: 1px solid #d8d3c8; border-radius: .5rem;
    padding: .35rem 1.5rem .35rem .6rem; max-width: 12rem;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%232b2724' fill='none' stroke-width='1.5'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right .5rem center;
  }

  .calendar { background: #fff; border: 1px solid #e3ded4; border-radius: .75rem; padding: .75rem .9rem .9rem; margin-top: 1rem; }
  .cal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: .5rem; }
  .month { font-weight: 700; font-size: .95rem; }
  .cal-head button {
    font: inherit; font-size: 1rem; line-height: 1; width: 1.8rem; height: 1.8rem;
    border: 1px solid #d8d3c8; background: #fff; border-radius: .5rem; cursor: pointer; color: #2b2724;
  }
  .cal-head button:disabled { opacity: .35; cursor: default; }
  .grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: .2rem; }
  .dow { font-size: .68rem; color: #8a8378; text-align: center; padding: .15rem 0; }
  .grid button {
    font: inherit; font-size: .85rem; padding: .4rem 0; border-radius: .5rem;
    border: none; background: none; color: #c7c1b6; cursor: default;
  }
  .grid button.available { color: #2b2724; font-weight: 600; cursor: pointer; }
  .grid button.available:hover { background: #eef3f0; }
  .grid button.selected { background: #1e5c48; color: #fff; }
  .grid button.today:not(.selected) { box-shadow: inset 0 0 0 1.5px #1e5c48; }

  .board-title { font-size: .85rem; font-weight: 600; color: #8a8378; margin: 1.25rem 0 .5rem; }
  .board { background: #fff; border: 1px solid #e3ded4; border-radius: .75rem; padding: 0 1rem; }
  .dish { padding: .9rem 0; }
  .dish + .dish { border-top: 1px dashed #d8d3c8; }
  .line { display: flex; gap: .75rem; align-items: baseline; justify-content: space-between; }
  .dish img { width: 56px; height: 56px; object-fit: cover; border-radius: .5rem; float: right; margin-left: .75rem; }
  .dish h3 { font-size: 1rem; font-weight: 600; line-height: 1.35; margin: 0; overflow-wrap: anywhere; }
  .price { margin: 0; text-align: right; white-space: nowrap; font-weight: 700; color: #c2410c; font-variant-numeric: tabular-nums; }
  .price span { display: block; font-size: 1.05rem; }
  .price span + span { font-size: .85rem; font-weight: 600; }
  .meta { margin: .35rem 0 0; display: flex; flex-wrap: wrap; gap: .3rem .6rem; align-items: center; font-size: .78rem; color: #8a8378; }
  .cat { font-weight: 600; color: #1e5c48; }
  .tag { border: 1px solid #d8d3c8; border-radius: 1rem; padding: .05rem .5rem; color: #2b2724; }

  .quiet { color: #8a8378; }
  .error { color: #a03123; font-weight: 600; margin-bottom: .5rem; }
  .retry {
    font: inherit; font-weight: 600; cursor: pointer;
    background: #1e5c48; color: #fff; border: none; border-radius: .5rem; padding: .45rem 1.1rem;
  }
  footer { margin-top: 1.5rem; }
  footer p { font-size: .72rem; color: #b0a99c; margin: 0; }

  .visually-hidden {
    position: absolute; width: 1px; height: 1px; margin: -1px;
    clip: rect(0 0 0 0); overflow: hidden; white-space: nowrap;
  }
</style>
