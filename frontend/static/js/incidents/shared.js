(() => {
  "use strict";
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const watchButtons = [...document.querySelectorAll("[data-watch-scope]")];
  const status = (button, message) => {
    let region = button.parentElement.querySelector("[data-watch-status]");
    if (!region) {
      region = document.createElement("span");
      region.dataset.watchStatus = "";
      region.setAttribute("role", "status");
      button.insertAdjacentElement("afterend", region);
    }
    region.textContent = message;
  };
  watchButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const response = await fetch(button.dataset.watchUrl || "/incidents/watch", {
          method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, Accept: "application/json" },
          body: JSON.stringify({ scope: button.dataset.watchScope, key: button.dataset.watchKey, notify_updates: true, notify_resolution: true }),
        });
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || "Could not save watch.");
        status(button, result.created ? "Watch added." : "Watch preferences updated.");
        button.textContent = "✓ Watching";
      } catch (error) {
        status(button, error.message || "Could not save watch.");
      } finally {
        button.disabled = false;
      }
    });
  });
  document.querySelectorAll("[data-acknowledge]").forEach((button) => {
    button.addEventListener("click", async () => {
      const { type, id, url } = button.dataset;
      button.disabled = true;
      try {
        const response = await fetch(url || `/incidents/acknowledge/${type}/${id}`, {
          method: "POST", headers: { "X-CSRFToken": csrf, Accept: "application/json" },
        });
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || "Acknowledgement failed.");
        button.textContent = "Acknowledged";
        button.classList.add("is-acknowledged");
      } catch (error) {
        button.textContent = error.message || "Try again";
        button.disabled = false;
      }
    });
  });
})();
