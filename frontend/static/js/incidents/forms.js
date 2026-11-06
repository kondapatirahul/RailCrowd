(() => {
  "use strict";
  const form = document.querySelector("[data-incident-form]");
  if (!form) return;
  const title = form.querySelector("#title");
  const description = form.querySelector("#description");
  const train = form.querySelector("#train_number");
  const station = form.querySelector("#station_code");
  const from = form.querySelector("#from_station");
  const to = form.querySelector("#to_station");
  const occurred = form.querySelector("#occurred_at");
  const submit = form.querySelector('[type="submit"]');
  const messages = new Map();

  function showError(field, message) {
    if (!field) return;
    field.setCustomValidity(message || "");
    field.setAttribute("aria-invalid", message ? "true" : "false");
    if (message) messages.set(field.name, message);
    else messages.delete(field.name);
  }

  function validateLocation() {
    const trainValue = train?.value.trim() || "";
    const stationValue = station?.value.trim() || "";
    const valid = Boolean(trainValue || stationValue);
    showError(train, valid ? "" : "Select a train or a station.");
    showError(station, valid ? "" : "Select a train or a station.");
    return valid;
  }

  function validateSegment() {
    const left = from?.value.trim().toUpperCase() || "";
    const right = to?.value.trim().toUpperCase() || "";
    if (left && right && left === right) {
      showError(to, "Choose two different stations.");
      return false;
    }
    showError(to, "");
    return true;
  }

  function updateCounter(field) {
    const counter = form.querySelector(`[data-count-for="${field.id}"]`);
    if (!counter) return;
    const max = Number(field.maxLength) || 0;
    counter.textContent = `${field.value.length} / ${max}`;
    counter.classList.toggle("is-near-limit", max > 0 && field.value.length > max * 0.9);
  }

  function sanitizeStation(field) {
    if (!field) return;
    const cursor = field.selectionStart;
    const before = field.value;
    field.value = before.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 10);
    if (cursor !== null) field.setSelectionRange(Math.min(cursor, field.value.length), Math.min(cursor, field.value.length));
  }

  [title, description].filter(Boolean).forEach((field) => {
    updateCounter(field);
    field.addEventListener("input", () => updateCounter(field));
  });
  [from, to, station].filter(Boolean).forEach((field) => {
    field.addEventListener("input", () => sanitizeStation(field));
    field.addEventListener("blur", () => sanitizeStation(field));
  });
  [train, station].filter(Boolean).forEach((field) => field.addEventListener("change", validateLocation));
  [from, to].filter(Boolean).forEach((field) => field.addEventListener("change", validateSegment));

  function setDefaultTime() {
    if (!occurred || occurred.value) return;
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    occurred.value = now.toISOString().slice(0, 16);
    occurred.max = now.toISOString().slice(0, 16);
  }
  setDefaultTime();

  form.addEventListener("submit", (event) => {
    const locationValid = validateLocation();
    const segmentValid = validateSegment();
    const titleValid = title ? title.value.trim().length > 0 : true;
    const descriptionValid = description ? description.value.trim().length >= 10 : true;
    if (!locationValid || !segmentValid || !titleValid || !descriptionValid || !form.checkValidity()) {
      event.preventDefault();
      form.querySelector(":invalid")?.focus();
      form.classList.add("has-validation-errors");
      return;
    }
    if (submit) {
      submit.disabled = true;
      submit.dataset.originalText = submit.textContent;
      submit.textContent = "Submitting report…";
    }
  });

  form.querySelectorAll("input, textarea, select").forEach((field) => {
    field.addEventListener("input", () => {
      if (field.validity.valid) showError(field, "");
    });
  });
})();
