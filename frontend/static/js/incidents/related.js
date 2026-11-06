(() => {
  "use strict";
  const page = document.querySelector("[data-incident-detail]");
  const panel = page?.querySelector(".related-card");
  if (!page || !panel) return;
  const incidentId = page.dataset.incidentId;
  const target = document.createElement("div");
  target.className = "related-incident-list";
  target.setAttribute("aria-live", "polite");
  panel.append(target);

  function makeRelated(item) {
    const card = document.createElement("a");
    card.className = "related-incident-item";
    card.href = `/incidents/${encodeURIComponent(item.incident.id)}`;
    const title = document.createElement("strong");
    title.textContent = item.incident.title;
    const details = document.createElement("small");
    details.textContent = `${item.incident.category.replaceAll("_", " ")} · ${item.score}% match`;
    card.append(title, details);
    return card;
  }

  async function loadRelated() {
    target.textContent = "Finding related reports…";
    try {
      const response = await fetch(`/incidents/${encodeURIComponent(incidentId)}/api/related`, { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Related reports unavailable.");
      target.replaceChildren();
      if (!payload.items.length) {
        const empty = document.createElement("p");
        empty.className = "related-incident-empty";
        empty.textContent = "No closely related reports found.";
        target.append(empty);
        return;
      }
      payload.items.forEach((item) => target.append(makeRelated(item)));
    } catch (error) {
      target.textContent = error.message || "Related reports unavailable.";
    }
  }
  loadRelated();
})();
