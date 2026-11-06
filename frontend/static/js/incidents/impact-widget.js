(() => {
  "use strict";
  const widgets = [...document.querySelectorAll("[data-train-impact]")];
  if (!widgets.length) return;

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  }

  function render(widget, payload) {
    const impact = payload.impact;
    const target = widget.querySelector("[data-impact-results]");
    if (!target) return;
    target.replaceChildren();
    const summary = element("div", `impact-widget__summary impact-widget__summary--${impact.level}`, `${impact.count} active community reports · ${impact.level} reported impact`);
    target.append(summary);
    if (!impact.items.length) {
      target.append(element("p", "impact-widget__empty", "No active verified community reports match this train in RailCrowd."));
    }
    impact.items.forEach((item) => {
      const card = element("article", "impact-widget__item");
      card.append(element("strong", "", item.title), element("p", "", item.description || ""));
      const link = element("a", "", "View report →");
      link.href = `/incidents/${encodeURIComponent(item.id)}`;
      card.append(link);
      target.append(card);
    });
    (impact.advisories || []).forEach((advisory) => {
      const card = element("article", `impact-widget__advisory impact-widget__advisory--${advisory.severity}`);
      card.append(element("strong", "", advisory.title), element("p", "", advisory.summary));
      target.append(card);
    });
  }

  async function load(widget) {
    const number = widget.dataset.trainImpact;
    const target = widget.querySelector("[data-impact-results]");
    if (!number || !target) return;
    target.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(`/incidents/api/impact/train/${encodeURIComponent(number)}`, { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Impact data unavailable.");
      render(widget, payload);
    } catch (error) {
      target.replaceChildren(element("p", "impact-widget__error", error.message || "Impact data unavailable."));
    } finally {
      target.removeAttribute("aria-busy");
    }
  }
  widgets.forEach(load);
})();
