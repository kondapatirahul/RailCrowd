(() => {
  "use strict";
  const page = document.querySelector(".advisories-page");
  if (!page) return;
  const cards = [...page.querySelectorAll(".advisory-card")];
  const search = page.querySelector("[data-advisory-search]");
  const severity = page.querySelector("[data-advisory-severity]");
  const count = page.querySelector("[data-advisory-count]");

  function applyFilters() {
    const query = (search?.value || "").trim().toLowerCase();
    const level = severity?.value || "";
    let visible = 0;
    cards.forEach((card) => {
      const matchesQuery = !query || card.textContent.toLowerCase().includes(query);
      const matchesSeverity = !level || card.classList.contains(`advisory-card--${level}`);
      const show = matchesQuery && matchesSeverity;
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (count) count.textContent = `${visible} advisories`;
  }
  search?.addEventListener("input", applyFilters);
  severity?.addEventListener("change", applyFilters);
})();
