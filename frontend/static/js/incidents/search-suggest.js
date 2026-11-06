(() => {
  "use strict";
  const input = document.querySelector("#incident-query");
  const root = input?.closest(".incident-filter-form");
  if (!input || !root) return;
  const wrapper = input.closest(".filter-search") || input.parentElement;
  const list = document.createElement("div");
  list.className = "incident-search-suggestions";
  list.hidden = true;
  list.setAttribute("role", "listbox");
  wrapper.append(list);
  let timer = null;
  let controller = null;
  let activeIndex = -1;
  let suggestions = [];

  function closeList() {
    list.hidden = true;
    list.replaceChildren();
    activeIndex = -1;
    suggestions = [];
    input.setAttribute("aria-expanded", "false");
  }

  function choose(item) {
    input.value = item.title || "";
    closeList();
    root.requestSubmit();
  }

  function render(items) {
    suggestions = items || [];
    list.replaceChildren();
    suggestions.forEach((item, index) => {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "incident-search-suggestion";
      option.setAttribute("role", "option");
      option.dataset.index = String(index);
      const title = document.createElement("strong");
      title.textContent = item.title;
      const detail = document.createElement("small");
      detail.textContent = `${item.category.replaceAll("_", " ")} · ${item.train_number || item.station_code || "Community report"}`;
      option.append(title, detail);
      option.addEventListener("click", () => choose(item));
      list.append(option);
    });
    list.hidden = suggestions.length === 0;
    input.setAttribute("aria-expanded", String(suggestions.length > 0));
  }

  async function lookup(query) {
    controller?.abort();
    controller = new AbortController();
    try {
      const response = await fetch(`/incidents/api/search?q=${encodeURIComponent(query)}`, {
        headers: { Accept: "application/json" }, signal: controller.signal,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Search suggestions unavailable.");
      render(payload.items.slice(0, 6));
    } catch (error) {
      if (error.name !== "AbortError") closeList();
    }
  }

  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-expanded", "false");
  input.addEventListener("input", () => {
    window.clearTimeout(timer);
    const query = input.value.trim();
    if (query.length < 2) { closeList(); return; }
    timer = window.setTimeout(() => lookup(query), 300);
  });
  input.addEventListener("keydown", (event) => {
    if (list.hidden) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIndex = Math.min(activeIndex + 1, suggestions.length - 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIndex = Math.max(0, activeIndex - 1);
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      choose(suggestions[activeIndex]);
      return;
    } else if (event.key === "Escape") {
      closeList();
      return;
    } else {
      return;
    }
    list.querySelectorAll("button").forEach((button, index) => {
      const active = index === activeIndex;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
    });
  });
  document.addEventListener("click", (event) => {
    if (!wrapper.contains(event.target)) closeList();
  });
})();
