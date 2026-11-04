<script>
  import { onMount } from "svelte";

  // Empty = same origin (served by the API container). Set VITE_API_URL at build
  // time to point a statically hosted build (e.g. GitHub Pages) at the API host.
  const API = import.meta.env.VITE_API_URL || "";

  let stores = [];
  let store = "";
  let week = null;          // null = current week (API default)
  let weekLabel = "";
  let days = [];
  let activeDay = null;
  let error = "";
  let loading = false;

  const todayIsoWeek = () => {
    const d = new Date();
    const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    const day = (t.getUTCDay() + 6) % 7; // Monday = 0
    t.setUTCDate(t.getUTCDate() - day + 3); // Thursday of this week
    const firstThursday = new Date(Date.UTC(t.getUTCFullYear(), 0, 4));
    const fday = (firstThursday.getUTCDay() + 6) % 7;
    firstThursday.setUTCDate(firstThursday.getUTCDate() - fday + 3);
    return 1 + Math.round((t - firstThursday) / (7 * 864e5));
  };
  const currentWeek = todayIsoWeek();

  async function loadStores() {
    const res = await fetch(`${API}/api/stores`);
    stores = await res.json();
    store = stores.find((s) => s.name === "Airbus Finkenwerder")?.name ?? stores[0]?.name ?? "";
  }

  async function loadMenu() {
    if (!store) return;
    loading = true;
    error = "";
    try {
      const params = new URLSearchParams({ store });
      if (week !== null) params.set("week", week);
      const res = await fetch(`${API}/api/menu?${params}`);
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
      weekLabel = body.week;
      days = body.days;
      activeDay = days[0]?.weekday ?? null;
      if (week === null) week = parseInt(body.week.replace(/\D/g, ""), 10);
    } catch (e) {
      error = e.message;
      days = [];
    } finally {
      loading = false;
    }
  }

  $: if (store) loadMenu();
  $: activeMeals = days.find((d) => d.weekday === activeDay)?.meals ?? [];

  onMount(async () => {
    await loadStores();
  });
</script>

<main>
  <header>
    <h1>AirFood</h1>
    <label>
      Store
      <select bind:value={store}>
        {#each stores as s}
          <option value={s.name}>{s.name}</option>
        {/each}
      </select>
    </label>
    <div class="week">
      <button on:click={() => (week = Math.max(1, week - 1))} disabled={loading}>‹</button>
      <span>{weekLabel || `CW ${week ?? currentWeek}`}</span>
      <button on:click={() => (week = Math.min(53, week + 1))} disabled={loading}>›</button>
    </div>
  </header>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if days.length}
    <nav class="days">
      {#each days as d}
        <button class:active={d.weekday === activeDay} on:click={() => (activeDay = d.weekday)}>
          {d.weekday.slice(0, 3)}<small>{d.label.replace(/^[A-Za-z]+\. /, "")}</small>
        </button>
      {/each}
    </nav>
  {/if}

  {#if loading}
    <p>Loading…</p>
  {:else if activeMeals.length}
    {#each activeMeals as meal}
      <article class="dish">
        {#if meal.image_url}<img src={meal.image_url} alt="" loading="lazy" />{/if}
        <div>
          <h2>{meal.name}</h2>
          <p class="meta">
            {meal.category} ·
            {#if meal.price_options?.length > 1}
              {#each meal.price_options as p, i}{#if i > 0} / {/if}{p.label ? p.label + " " : ""}{p.amount} {p.currency}{/each}
            {:else}
              {meal.price ?? "—"} {meal.currency ?? ""}
            {/if}
          </p>
          {#if meal.allergens?.length}<p class="allergens">Allergens: {meal.allergens.join(", ")}</p>{/if}
          {#if meal.tags?.length}<p class="tags">{#each meal.tags as t}<span>{t.name}</span>{/each}</p>{/if}
        </div>
      </article>
    {/each}
  {:else if !loading && !error}
    <p>No menu data for this selection.</p>
  {/if}
</main>

<style>
  :global(body) { margin: 0; font-family: system-ui, sans-serif; color: #222; }
  main { max-width: 640px; margin: 0 auto; padding: 1rem; }
  header { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; justify-content: space-between; }
  h1 { color: #b3202c; font-size: 1.4rem; margin: 0; }
  select { font: inherit; padding: .3rem; }
  .week { display: flex; gap: .5rem; align-items: center; }
  .week button { font: inherit; width: 2rem; }
  .days { display: flex; gap: .25rem; margin: .75rem 0; flex-wrap: wrap; }
  .days button { font: inherit; padding: .4rem .6rem; border: 1px solid #ccc; background: #fff; border-radius: .4rem; cursor: pointer; display: flex; flex-direction: column; }
  .days button small { color: #777; font-size: .7rem; }
  .days button.active { background: #b3202c; color: #fff; border-color: #b3202c; }
  .days button.active small { color: #ffd; }
  .dish { display: flex; gap: .75rem; border: 1px solid #eee; border-radius: .6rem; padding: .6rem; margin-bottom: .6rem; }
  .dish img { width: 72px; height: 72px; object-fit: cover; border-radius: .4rem; }
  .dish h2 { font-size: 1rem; margin: 0 0 .2rem; }
  .meta { margin: 0 0 .2rem; color: #555; font-size: .9rem; }
  .allergens { margin: 0; font-size: .8rem; color: #a55; }
  .tags span { display: inline-block; background: #eef; border-radius: 1rem; padding: .1rem .5rem; font-size: .75rem; margin-right: .25rem; }
  .error { color: #b3202c; }
</style>
