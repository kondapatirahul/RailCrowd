(() => {
  "use strict";
  const widget = document.querySelector("[data-incident-history]");
  if (!widget) return;
  const type = widget.dataset.type;
  const key = widget.dataset.key;
  const target = widget.querySelector("[data-history-results]");
  const endpoint = type === "station" ? `/incidents/api/history/station/${encodeURIComponent(key)}` : `/incidents/api/history/train/${encodeURIComponent(key)}`;

  function makeHistory(data) {
    const card = document.createElement("article");
    card.className = "history-signal-card";
    const heading = document.createElement("strong");
    heading.textContent = data.level || "No history";
    const count = document.createElement("span");
    count.textContent = `${data.count || 0} verified community reports in the selected window`;
    const average = document.createElement("small");
    average.textContent = `${data.daily_average || 0} reports per day on average`;
    card.append(heading, count, average);
    const categories = document.createElement("div");
    categories.className = "history-signal-categories";
    (data.categories || []).forEach((item) => {
      const row = document.createElement("span");
      row.textContent = `${item.category.replaceAll("_", " ")}: ${item.count}`;
      categories.append(row);
    });
    card.append(categories);
    return card;
  }

  async function load() {
    if (!target || !key) return;
    target.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(endpoint, { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Historical signal unavailable.");
      target.replaceChildren(makeHistory(payload.history.history || payload.history));
      const notice = document.createElement("p");
      notice.className = "history-signal-notice";
      notice.textContent = payload.history.notice || "Historical community observations do not predict future service conditions.";
      target.append(notice);
    } catch (error) {
      target.textContent = error.message || "Historical signal unavailable.";
    } finally {
      target.removeAttribute("aria-busy");
    }
  }
  load();
})();
