(() => {
  "use strict";
  const incidentRoot = document.querySelector(".incident-shell, .incident-detail-page, .incident-form-page, .incident-admin, .watches-page, .advisories-page, .my-reports-page");
  if (!incidentRoot) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const announce = (message) => {
    let live = incidentRoot.querySelector("[data-global-live]");
    if (!live) {
      live = document.createElement("div");
      live.dataset.globalLive = "";
      live.className = "visually-hidden";
      live.setAttribute("aria-live", "polite");
      live.setAttribute("aria-atomic", "true");
      incidentRoot.append(live);
    }
    live.textContent = "";
    window.requestAnimationFrame(() => { live.textContent = message; });
  };
  incidentRoot.querySelectorAll("a,button,input,select,textarea").forEach((control) => {
    if (!control.getAttribute("aria-label") && !control.textContent.trim() && !control.labels?.length) {
      control.setAttribute("aria-label", control.title || "Interactive control");
    }
  });
  if (reduceMotion.matches) incidentRoot.classList.add("prefers-reduced-motion");
  reduceMotion.addEventListener?.("change", (event) => {
    incidentRoot.classList.toggle("prefers-reduced-motion", event.matches);
    announce(event.matches ? "Reduced motion preference enabled." : "Reduced motion preference disabled.");
  });
  incidentRoot.querySelectorAll("form").forEach((form) => {
    form.addEventListener("invalid", (event) => {
      const label = event.target.labels?.[0]?.textContent || event.target.name || "field";
      announce(`Please check ${label}.`);
    }, true);
  });
})();
