(() => {
  "use strict";
  const page = document.querySelector(".my-reports-page");
  if (!page) return;
  const forms = [...page.querySelectorAll("[data-withdraw-form]")];
  const summaryUrl = "/incidents/my-reports/api/summary";
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";

  forms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirmed === "true") return;
      event.preventDefault();
      if (!window.confirm("Withdraw this report? It will no longer appear in the public disruption feed.")) return;
      const reason = window.prompt("Optional reason for withdrawing this report:", "");
      if (reason === null) return;
      const field = form.querySelector('[name="reason"]');
      if (field) field.value = reason.slice(0, 1000);
      form.dataset.confirmed = "true";
      const button = form.querySelector("button[type=submit]");
      if (button) { button.disabled = true; button.textContent = "Withdrawing…"; }
      form.submit();
    });
  });

  async function loadContributionSummary() {
    const calendar = page.querySelector("[data-contribution-calendar]");
    if (!calendar) return;
    calendar.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(summaryUrl, { headers: { Accept: "application/json", "X-CSRFToken": csrf } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Activity unavailable.");
      const days = payload.calendar || [];
      calendar.replaceChildren();
      if (!days.length) {
        const empty = document.createElement("p");
        empty.textContent = "Your contribution activity will appear here.";
        calendar.append(empty);
        return;
      }
      const maximum = Math.max(1, ...days.map((day) => day.total));
      days.forEach((day) => {
        const cell = document.createElement("div");
        cell.className = "contribution-day";
        cell.style.setProperty("--activity", String(day.total / maximum));
        cell.title = `${day.date}: ${day.reports} reports, ${day.votes} votes, ${day.updates} updates`;
        cell.setAttribute("aria-label", cell.title);
        calendar.append(cell);
      });
    } catch (error) {
      calendar.textContent = error.message || "Activity data could not be loaded.";
    } finally {
      calendar.removeAttribute("aria-busy");
    }
  }
  loadContributionSummary();
})();
