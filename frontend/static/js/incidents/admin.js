(() => {
  "use strict";
  const board = document.querySelector("[data-admin-board]");
  if (!board) return;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const metricsUrl = "/incidents/admin/api/metrics";
  const refreshButton = board.querySelector("[data-refresh-metrics]");
  const state = { loadedAt: null, loading: false };

  function createMetric(label, value, detail) {
    const tile = document.createElement("article");
    tile.className = "admin-live-metric";
    const title = document.createElement("span");
    title.textContent = label;
    const number = document.createElement("strong");
    number.textContent = String(value ?? 0);
    const note = document.createElement("small");
    note.textContent = detail || "Current count";
    tile.append(title, number, note);
    return tile;
  }

  function renderLiveMetrics(data) {
    let region = board.querySelector("[data-live-metrics]");
    if (!region) {
      region = document.createElement("div");
      region.dataset.liveMetrics = "";
      region.className = "admin-live-metrics";
      board.querySelector(".admin-kpis")?.insertAdjacentElement("afterend", region);
    }
    region.replaceChildren(
      createMetric("Pending reports", data.queue?.pending, "Awaiting moderation"),
      createMetric("Under review", data.queue?.under_review, "Review in progress"),
      createMetric("Critical reports", data.queue?.critical, "Active critical severity"),
      createMetric("Total votes", data.verification?.total_votes, "Community confirmations and disputes"),
    );
    state.loadedAt = new Date();
    region.setAttribute("aria-label", `Metrics refreshed at ${state.loadedAt.toLocaleTimeString()}`);
  }

  async function refreshMetrics() {
    if (state.loading) return;
    state.loading = true;
    if (refreshButton) refreshButton.disabled = true;
    try {
      const response = await fetch(metricsUrl, { headers: { Accept: "application/json", "X-CSRFToken": csrf } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Metrics unavailable.");
      renderLiveMetrics(payload);
    } catch (error) {
      let message = board.querySelector("[data-metric-error]");
      if (!message) {
        message = document.createElement("p");
        message.dataset.metricError = "";
        message.className = "admin-metric-error";
        board.append(message);
      }
      message.textContent = error.message || "Could not refresh metrics.";
    } finally {
      state.loading = false;
      if (refreshButton) refreshButton.disabled = false;
    }
  }

  board.querySelectorAll(".admin-queue-item__actions form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const decision = form.querySelector('[name="decision"]')?.value;
      if (decision === "rejected" && !window.confirm("Reject this passenger report? This action changes its public status.")) {
        event.preventDefault();
      }
      if (decision === "verified" && !window.confirm("Mark this report as verified by RailCrowd moderation?")) {
        event.preventDefault();
      }
    });
  });
  refreshButton?.addEventListener("click", refreshMetrics);
  board.dataset.ready = "true";
})();
