(() => {
  "use strict";
  const root = document.querySelector("[data-feed-root]");
  if (!root) return;
  const form = root.querySelector("[data-filter-form]");
  const reset = root.querySelector("[data-filter-reset]");
  const search = root.querySelector("#incident-query");
  const cards = [...root.querySelectorAll("[data-incident-card]")];
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const state = { pending: false, lastQuery: "", controller: null, page: 1 };

  function normalize(value) {
    return String(value || "").trim().replace(/\s+/g, " ");
  }

  function updateSearchHint(message) {
    let hint = root.querySelector("[data-search-hint]");
    if (!hint) {
      hint = document.createElement("p");
      hint.dataset.searchHint = "";
      hint.className = "feed-search-hint";
      search?.insertAdjacentElement("afterend", hint);
    }
    hint.textContent = message;
  }

  function resetFilters() {
    if (!form) return;
    form.querySelectorAll("input, select").forEach((field) => {
      if (field.type === "search" || field.type === "text") field.value = "";
      else if (field.tagName === "SELECT") field.selectedIndex = 0;
    });
    form.submit();
  }

  function serializeFilters() {
    const data = new FormData(form);
    const params = new URLSearchParams();
    for (const [key, value] of data.entries()) {
      const cleaned = normalize(value);
      if (cleaned) params.set(key, cleaned);
    }
    return params;
  }

  function makeCard(item) {
    const article = document.createElement("article");
    article.className = `incident-card incident-card--${item.severity || "minor"}`;
    article.dataset.incidentCard = "";
    article.dataset.id = String(item.id);
    const rail = document.createElement("div");
    rail.className = "incident-card__rail";
    const mark = document.createElement("span");
    mark.className = `severity-mark severity-mark--${item.severity || "minor"}`;
    mark.textContent = ["critical", "major"].includes(item.severity) ? "!" : "i";
    rail.append(mark);
    const body = document.createElement("div");
    body.className = "incident-card__body";
    const top = document.createElement("div");
    top.className = "incident-card__top";
    const tags = document.createElement("div");
    tags.className = "incident-tags";
    const category = document.createElement("span");
    category.className = "incident-category";
    category.textContent = String(item.category || "other").replaceAll("_", " ");
    const status = document.createElement("span");
    status.className = `incident-status incident-status--${item.status || "pending"}`;
    status.textContent = String(item.status || "pending").replaceAll("_", " ");
    tags.append(category, status);
    const time = document.createElement("time");
    time.textContent = `${item.age_minutes ?? "—"} min ago`;
    top.append(tags, time);
    const heading = document.createElement("h3");
    const link = document.createElement("a");
    link.href = `/incidents/${encodeURIComponent(item.id)}`;
    link.textContent = item.title || "Untitled incident";
    heading.append(link);
    const description = document.createElement("p");
    description.className = "incident-card__description";
    description.textContent = item.description || "No description provided.";
    const location = document.createElement("div");
    location.className = "incident-card__location";
    const icon = document.createElement("span");
    icon.textContent = "⌁";
    location.append(icon);
    if (item.train_number) {
      const number = document.createElement("strong");
      number.textContent = item.train_number;
      const name = document.createElement("span");
      name.textContent = item.train_name || "Train";
      location.append(number, name);
    }
    if (item.station_code) {
      const code = document.createElement("strong");
      code.textContent = item.station_code;
      const name = document.createElement("span");
      name.textContent = item.station_name || "Station";
      location.append(code, name);
    }
    const bottom = document.createElement("div");
    bottom.className = "incident-card__bottom";
    const confidence = document.createElement("div");
    confidence.className = "confidence-meter";
    const label = document.createElement("span");
    label.textContent = "Community confidence";
    const track = document.createElement("div");
    track.className = "confidence-track";
    const fill = document.createElement("i");
    fill.style.width = `${Math.max(0, Math.min(100, Number(item.confidence) || 0))}%`;
    track.append(fill);
    const percent = document.createElement("strong");
    percent.textContent = `${Number(item.confidence) || 0}%`;
    confidence.append(label, track, percent);
    const counts = document.createElement("div");
    counts.className = "incident-card__counts";
    const yes = document.createElement("span");
    yes.textContent = `✓ ${item.verification_count || 0} confirmed`;
    const no = document.createElement("span");
    no.textContent = `↗ ${item.contradiction_count || 0} disputed`;
    counts.append(yes, no);
    const open = document.createElement("a");
    open.className = "incident-open";
    open.href = link.href;
    open.textContent = "View details →";
    bottom.append(confidence, counts, open);
    const freshness = document.createElement("div");
    freshness.className = `freshness-note freshness-note--${item.freshness || "aging"}`;
    freshness.textContent = `${item.freshness || "Unknown"} community observation`;
    body.append(top, heading, description, location, bottom, freshness);
    article.append(rail, body);
    return article;
  }

  function renderResults(payload) {
    const list = root.querySelector(".incident-card-list");
    const empty = root.querySelector(".incident-empty");
    if (!list) return;
    list.replaceChildren();
    (payload.items || []).forEach((item) => list.append(makeCard(item)));
    if (empty) empty.hidden = Boolean(payload.items?.length);
    const count = root.querySelector(".feed-heading h2 span");
    if (count) count.textContent = String(payload.total || 0);
    updateSearchHint(`${payload.total || 0} matching community reports`);
  }

  async function refreshFeed() {
    if (!form || state.pending) return;
    const params = serializeFilters();
    const query = params.toString();
    if (query === state.lastQuery) return;
    state.lastQuery = query;
    state.pending = true;
    state.controller?.abort();
    state.controller = new AbortController();
    const submit = form.querySelector('[type="submit"]');
    if (submit) submit.disabled = true;
    try {
      const response = await fetch(`/incidents/api/feed?${query}`, {
        headers: { Accept: "application/json", "X-CSRFToken": csrf },
        signal: state.controller.signal,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Could not refresh the feed.");
      renderResults(payload);
    } catch (error) {
      if (error.name !== "AbortError") updateSearchHint(error.message || "Feed refresh failed.");
    } finally {
      state.pending = false;
      if (submit) submit.disabled = false;
    }
  }

  let searchTimer = null;
  search?.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(refreshFeed, 450);
  });
  form?.querySelectorAll("select, input:not([type=search])").forEach((field) => {
    field.addEventListener("change", () => {
      state.lastQuery = "";
      refreshFeed();
    });
  });
  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    state.lastQuery = "";
    refreshFeed();
  });
  reset?.addEventListener("click", resetFilters);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) state.lastQuery = "";
  });
})();
