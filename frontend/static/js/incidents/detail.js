(() => {
  "use strict";
  const root = document.querySelector("[data-incident-detail]");
  if (!root) return;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const id = root.dataset.incidentId;
  const voteButtons = [...root.querySelectorAll("[data-vote]")];
  const watchButton = root.querySelector("[data-watch-scope]");
  const copyButton = root.querySelector("[data-copy-link]");

  function announce(message) {
    let region = root.querySelector("[data-detail-feedback]");
    if (!region) {
      region = document.createElement("p");
      region.dataset.detailFeedback = "";
      region.className = "detail-feedback";
      region.setAttribute("role", "status");
      const panel = root.querySelector(".verification-panel");
      panel?.append(region);
    }
    region.textContent = message;
  }

  function updateVoteTotals(totals) {
    const count = root.querySelector(".verification-count");
    if (count) count.textContent = `${(totals.confirmations || 0) + (totals.contradictions || 0)} votes`;
    const yes = root.querySelector(".verification-legend span:first-child");
    const no = root.querySelector(".verification-legend span:last-child");
    if (yes) yes.textContent = `${totals.confirmations || 0} confirmations`;
    if (no) no.textContent = `${totals.contradictions || 0} contradictions`;
    const confidence = root.querySelector(".detail-confidence strong");
    if (confidence) confidence.innerHTML = `${Number(totals.confidence || 0)}<small>%</small>`;
    const track = root.querySelector(".detail-confidence__track i");
    if (track) track.style.width = `${Number(totals.confidence || 0)}%`;
  }

  async function submitVote(button) {
    if (button.disabled) return;
    const vote = button.dataset.vote;
    const endpoint = button.dataset.url;
    if (!endpoint || !["confirm", "contradict"].includes(vote)) return;
    const body = new URLSearchParams({ vote });
    button.disabled = true;
    button.classList.add("is-loading");
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded", "X-CSRFToken": csrf, Accept: "application/json" },
        body,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Vote could not be saved.");
      updateVoteTotals(payload.totals || {});
      voteButtons.forEach((item) => item.classList.toggle("is-selected", item === button));
      announce("Your community verification vote has been recorded.");
    } catch (error) {
      announce(error.message || "Vote could not be saved.");
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }

  async function toggleWatch() {
    if (!watchButton || watchButton.disabled) return;
    const body = { scope: watchButton.dataset.watchScope, key: watchButton.dataset.watchKey, notify_updates: true, notify_resolution: true };
    watchButton.disabled = true;
    try {
      const response = await fetch(watchButton.dataset.watchUrl, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, Accept: "application/json" }, body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Watch could not be saved.");
      watchButton.textContent = payload.created ? "✓ Watching incident" : "✓ Watch preferences saved";
      watchButton.classList.add("is-watching");
    } catch (error) {
      announce(error.message || "Could not add watch.");
    } finally {
      watchButton.disabled = false;
    }
  }

  async function copyIncidentLink() {
    if (!copyButton) return;
    const feedback = root.querySelector(".copy-feedback");
    try {
      await navigator.clipboard.writeText(window.location.href);
      if (feedback) feedback.textContent = "Link copied.";
    } catch {
      if (feedback) feedback.textContent = `Copy this URL: ${window.location.href}`;
    }
  }

  voteButtons.forEach((button) => button.addEventListener("click", () => submitVote(button)));
  watchButton?.addEventListener("click", toggleWatch);
  copyButton?.addEventListener("click", copyIncidentLink);
  root.querySelectorAll(".incident-update-form textarea").forEach((field) => {
    field.addEventListener("input", () => {
      field.setCustomValidity(field.value.trim().length < 5 ? "Please add a little more detail." : "");
    });
  });
  root.dataset.ready = "true";
})();
