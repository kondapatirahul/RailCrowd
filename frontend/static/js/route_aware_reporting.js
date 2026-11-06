(() => {
  "use strict";

  const form = document.getElementById("rc-route-report-form");
  if (!form) return;

  const trainSelect = document.getElementById("rc-train-number");
  const fromSelect = document.getElementById("rc-from-station");
  const toSelect = document.getElementById("rc-to-station");
  const help = document.getElementById("rc-route-help");
  const template = form.dataset.routeUrlTemplate;
  const searchUrl = form.dataset.searchUrl;
  const searchInput = document.getElementById("rc-report-train-query");
  const searchButton = document.getElementById("rc-report-train-search-button");
  const results = document.getElementById("rc-report-train-results");

  function setOptions(select, stations, placeholder) {
    const previous = select.value;
    select.replaceChildren();
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = placeholder;
    select.appendChild(empty);
    stations.forEach((station) => {
      const option = document.createElement("option");
      option.value = station.code;
      option.textContent = station.label;
      select.appendChild(option);
    });
    if (stations.some((station) => station.code === previous)) select.value = previous;
  }

  async function loadRoute() {
    const trainNumber = trainSelect.value;
    if (!trainNumber) {
      setOptions(fromSelect, [], "Select a train first");
      setOptions(toSelect, [], "Select a train first");
      help.textContent = "Choose a train to load its route.";
      return;
    }
    trainSelect.disabled = true;
    help.textContent = "Loading route stations…";
    try {
      const url = template.replace("__TRAIN__", encodeURIComponent(trainNumber));
      const response = await fetch(url, {
        headers: { "Accept": "application/json" }, credentials: "same-origin"
      });
      if (!response.ok) throw new Error("Route could not be loaded.");
      const data = await response.json();
      setOptions(fromSelect, data.stations, "Choose boarding station");
      setOptions(toSelect, data.stations, "Choose destination station");
      help.textContent = `${data.train.name} · ${data.stations.length} route station(s)`;
    } catch (_error) {
      setOptions(fromSelect, [], "Route unavailable");
      setOptions(toSelect, [], "Route unavailable");
      help.textContent = "Unable to load this route. Refresh the page and try again.";
    } finally {
      trainSelect.disabled = false;
    }
  }

  function showSearchMessage(message, kind = "muted") {
    results.replaceChildren();
    const note = document.createElement("p");
    note.className = `rc-report-search-message is-${kind}`;
    note.textContent = message;
    results.appendChild(note);
  }

  function renderResults(trains) {
    results.replaceChildren();
    if (!trains.length) {
      showSearchMessage("No matching trains found. Try another number, name, or station.");
      return;
    }
    const heading = document.createElement("p");
    heading.className = "rc-report-search-message";
    heading.textContent = `${trains.length} matching train(s). Select one to load its route.`;
    results.appendChild(heading);

    const list = document.createElement("div");
    list.className = "rc-report-search-list";
    trains.forEach((train) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "rc-report-search-result";
      const title = document.createElement("strong");
      title.textContent = `${train.number} — ${train.name}`;
      const route = document.createElement("span");
      route.textContent = `${train.source} (${train.source_code}) → ${train.destination} (${train.destination_code})`;
      button.append(title, route);
      button.addEventListener("click", () => {
        const optionExists = Array.from(trainSelect.options).some((option) => option.value === train.number);
        if (!optionExists) {
          showSearchMessage("This train is no longer available in the report catalogue. Refresh and try again.", "error");
          return;
        }
        trainSelect.value = train.number;
        trainSelect.dispatchEvent(new Event("change", { bubbles: true }));
        searchInput.value = `${train.number} — ${train.name}`;
        showSearchMessage(`Selected ${train.number} — ${train.name}. Choose your journey stations below.`, "success");
      });
      list.appendChild(button);
    });
    results.appendChild(list);
  }

  async function searchTrains() {
    const query = searchInput.value.trim();
    if (!query) {
      showSearchMessage("Enter a train number, train name, or station to search.", "error");
      searchInput.focus();
      return;
    }
    searchButton.disabled = true;
    searchButton.textContent = "Searching…";
    showSearchMessage("Searching the active train catalogue…");
    try {
      const url = new URL(searchUrl, window.location.origin);
      url.searchParams.set("q", query);
      const response = await fetch(url.toString(), {
        headers: { "Accept": "application/json" }, credentials: "same-origin"
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Train search failed.");
      renderResults(data.trains || []);
    } catch (error) {
      showSearchMessage(error.message || "Unable to search trains. Please try again.", "error");
    } finally {
      searchButton.disabled = false;
      searchButton.textContent = "Search train";
    }
  }

  trainSelect.addEventListener("change", loadRoute);
  searchButton.addEventListener("click", searchTrains);
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchTrains();
    }
  });
  loadRoute();
})();
