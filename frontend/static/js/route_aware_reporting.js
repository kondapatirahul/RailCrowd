(() => {
  "use strict";

  const form = document.getElementById("rc-route-report-form");
  if (!form) return;

  const trainSelect = document.getElementById("rc-train-number");
  const fromSelect = document.getElementById("rc-from-station");
  const toSelect = document.getElementById("rc-to-station");
  const help = document.getElementById("rc-route-help");
  const template = form.dataset.routeUrlTemplate;

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

    if (stations.some((station) => station.code === previous)) {
      select.value = previous;
    }
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
        headers: { "Accept": "application/json" },
        credentials: "same-origin"
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

  trainSelect.addEventListener("change", loadRoute);
  loadRoute();
})();
