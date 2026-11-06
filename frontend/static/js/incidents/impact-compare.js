(() => {
  "use strict";
  const form = document.querySelector("[data-alternative-search]");
  if (!form) return;
  const output = form.querySelector("[data-alternative-results]");
  const origin = form.querySelector('[name="from"]');
  const destination = form.querySelector('[name="to"]');
  const exclude = form.querySelector('[name="exclude"]');
  const button = form.querySelector("button[type=submit]");

  function makeOption(item) {
    const row = document.createElement("article");
    row.className = "alternative-option";
    const heading = document.createElement("strong");
    heading.textContent = `${item.number} · ${item.name}`;
    const times = document.createElement("span");
    times.textContent = `${item.departure_time || "Time unavailable"} → ${item.arrival_time || "Time unavailable"}`;
    const impact = document.createElement("small");
    impact.textContent = `${item.reported_impact} reported impact · ${item.incident_count} active report(s)`;
    row.append(heading, times, impact);
    return row;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const from = origin?.value.trim().toUpperCase();
    const to = destination?.value.trim().toUpperCase();
    if (!from || !to || from === to) {
      output.textContent = "Choose two different station codes.";
      return;
    }
    button.disabled = true;
    output.textContent = "Comparing catalogue routes and community reports…";
    try {
      const params = new URLSearchParams({ from, to });
      if (exclude?.value) params.set("exclude", exclude.value);
      const response = await fetch(`/incidents/api/alternatives?${params}`, { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Alternative routes unavailable.");
      output.replaceChildren();
      if (!payload.items.length) {
        output.textContent = "No matching active train routes were found in the current catalogue.";
      }
      payload.items.forEach((item) => output.append(makeOption(item)));
      const notice = document.createElement("p");
      notice.className = "alternative-notice";
      notice.textContent = payload.notice;
      output.append(notice);
    } catch (error) {
      output.textContent = error.message || "Alternative routes unavailable.";
    } finally {
      button.disabled = false;
    }
  });
})();
