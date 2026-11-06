(() => {
  "use strict";
  const form = document.querySelector(".advisory-form-page form");
  if (!form) return;
  const trains = form.querySelector("#affected_trains");
  const stations = form.querySelector("#affected_stations");
  const title = form.querySelector("#title");
  const summary = form.querySelector("#summary");
  const body = form.querySelector("#body");
  const buttons = [...form.querySelectorAll('button[type="submit"]')];

  function parseTokens(field, pattern, label) {
    if (!field) return [];
    const values = field.value.split(",").map((value) => value.trim().toUpperCase()).filter(Boolean);
    const invalid = values.filter((value) => !pattern.test(value));
    field.setCustomValidity(invalid.length ? `${label} contains invalid values: ${invalid.join(", ")}` : "");
    const unique = [...new Set(values)];
    if (unique.length !== values.length) field.setCustomValidity(`${label} contains duplicate values.`);
    return unique;
  }

  function renderScopePreview() {
    let preview = form.querySelector("[data-scope-preview]");
    if (!preview) {
      preview = document.createElement("div");
      preview.dataset.scopePreview = "";
      preview.className = "advisory-scope-preview";
      stations?.insertAdjacentElement("afterend", preview);
    }
    const trainValues = parseTokens(trains, /^[0-9]{4,6}$/, "Train numbers");
    const stationValues = parseTokens(stations, /^[A-Z0-9]{2,10}$/, "Station codes");
    preview.textContent = `${trainValues.length} train(s) · ${stationValues.length} station(s) targeted`;
  }

  [trains, stations].filter(Boolean).forEach((field) => field.addEventListener("input", renderScopePreview));
  renderScopePreview();
  form.addEventListener("submit", (event) => {
    parseTokens(trains, /^[0-9]{4,6}$/, "Train numbers");
    parseTokens(stations, /^[A-Z0-9]{2,10}$/, "Station codes");
    if (!title?.value.trim() || !summary?.value.trim() || (body?.value.trim().length || 0) < 10 || !form.checkValidity()) {
      event.preventDefault();
      form.querySelector(":invalid")?.focus();
      return;
    }
    const submitter = event.submitter;
    if (submitter?.value === "publish" && !window.confirm("Publish this RailCrowd advisory to the public advisory feed?")) {
      event.preventDefault();
      return;
    }
    buttons.forEach((button) => { button.disabled = true; });
    if (submitter) submitter.textContent = "Saving advisory…";
  });
})();
