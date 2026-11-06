(() => {
  "use strict";
  const root = document.querySelector(".incident-shell, .incident-detail-page, .incident-admin, .advisories-page");
  if (!root) return;
  const search = document.querySelector("#incident-query, [data-advisory-search]");
  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    const target = event.target;
    if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
    if (event.key === "/" && search) {
      event.preventDefault();
      search.focus();
    }
    if (event.key === "Escape" && document.activeElement === search) {
      search.value = "";
      search.blur();
      search.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
})();
