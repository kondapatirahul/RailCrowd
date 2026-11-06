(() => {
  "use strict";
  const forms = [...document.querySelectorAll("[data-unwatch-form]")];
  if (!forms.length) return;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  forms.forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector("button[type=submit]");
      if (!button || button.disabled) return;
      if (!window.confirm("Remove this watch? You will stop receiving its in-app updates.")) return;
      const payload = Object.fromEntries(new FormData(form).entries());
      button.disabled = true;
      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded", "X-CSRFToken": csrf, Accept: "application/json" },
          body: new URLSearchParams(payload),
        });
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || "Watch could not be removed.");
        form.closest(".watch-row")?.remove();
        const count = document.querySelector(".watches-hero__count strong");
        if (count) count.textContent = String(Math.max(0, Number(count.textContent) - 1));
        if (!document.querySelector(".watch-row")) window.location.reload();
      } catch (error) {
        button.disabled = false;
        button.textContent = error.message || "Try again";
      }
    });
  });
})();
