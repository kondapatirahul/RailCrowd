/* Station autocomplete: accessible keyboard and pointer interaction. */
(() => {
    const form = document.querySelector('#journey-search-form');
    if (!form) return;
    const endpoint = form.dataset.stationUrl;
    const fields = ['origin', 'destination'];
    const state = new Map();
    const debounceTimers = new Map();

    const byId = (id) => document.getElementById(id);
    const safeText = (value) => String(value ?? '');

    function fieldElements(name) {
        return {
            input: byId(`journey-${name}`),
            code: byId(`journey-${name}-code`),
            list: document.querySelector(`[data-suggestions="${name}"]`),
            hint: byId(`${name}-hint`),
        };
    }

    function closeList(name) {
        const elements = fieldElements(name);
        elements.list.hidden = true;
        elements.list.replaceChildren();
        elements.input.removeAttribute('aria-activedescendant');
        elements.input.setAttribute('aria-expanded', 'false');
        state.set(name, {items: [], active: -1});
    }

    function setSelection(name, station) {
        const elements = fieldElements(name);
        elements.input.value = `${station.name} (${station.code})`;
        elements.code.value = station.code;
        elements.input.dataset.selectedName = station.name;
        elements.input.setAttribute('aria-expanded', 'false');
        elements.input.classList.add('has-selection');
        elements.hint.textContent = [station.city, station.state].filter(Boolean).join(', ') || 'Station selected from catalogue.';
        closeList(name);
        elements.input.dispatchEvent(new CustomEvent('station:selected', {bubbles: true, detail: station}));
    }

    function renderSuggestions(name, items) {
        const elements = fieldElements(name);
        elements.list.replaceChildren();
        state.set(name, {items, active: -1});
        if (!items.length) {
            const empty = document.createElement('div');
            empty.className = 'station-suggestion-empty';
            empty.textContent = 'No station found. Try a station code or city.';
            elements.list.append(empty);
            elements.list.hidden = false;
            return;
        }
        items.forEach((station, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'station-suggestion';
            button.id = `${name}-suggestion-${index}`;
            button.setAttribute('role', 'option');
            button.setAttribute('aria-selected', 'false');
            const code = document.createElement('strong');
            code.className = 'station-suggestion__code';
            code.textContent = safeText(station.code);
            const details = document.createElement('span');
            details.className = 'station-suggestion__details';
            const stationName = document.createElement('strong');
            stationName.textContent = safeText(station.name);
            const location = document.createElement('small');
            location.textContent = [station.city, station.state].filter(Boolean).join(', ');
            details.append(stationName, location);
            button.append(code, details);
            button.addEventListener('mousedown', (event) => event.preventDefault());
            button.addEventListener('click', () => setSelection(name, station));
            elements.list.append(button);
        });
        elements.list.hidden = false;
        elements.input.setAttribute('aria-expanded', 'true');
    }

    async function fetchStations(name, query) {
        const elements = fieldElements(name);
        const requestId = Symbol('station-request');
        const current = state.get(name) || {};
        state.set(name, {...current, requestId});
        if (query.trim().length < 2) {
            closeList(name);
            return;
        }
        elements.list.classList.add('is-loading');
        try {
            const response = await fetch(`${endpoint}?q=${encodeURIComponent(query.trim())}`, {
                headers: {'Accept': 'application/json'}, credentials: 'same-origin',
            });
            if (!response.ok) throw new Error('Station lookup failed.');
            const data = await response.json();
            if ((state.get(name) || {}).requestId !== requestId) return;
            renderSuggestions(name, data.stations || []);
        } catch (error) {
            if ((state.get(name) || {}).requestId !== requestId) return;
            elements.list.replaceChildren();
            const message = document.createElement('div');
            message.className = 'station-suggestion-empty';
            message.textContent = 'Station search is temporarily unavailable.';
            elements.list.append(message);
            elements.list.hidden = false;
        } finally {
            elements.list.classList.remove('is-loading');
        }
    }

    function activate(name, index) {
        const elements = fieldElements(name);
        const current = state.get(name) || {items: [], active: -1};
        if (!current.items.length) return;
        const next = Math.max(0, Math.min(current.items.length - 1, index));
        current.active = next;
        state.set(name, current);
        elements.list.querySelectorAll('[role="option"]').forEach((node, position) => {
            const selected = position === next;
            node.setAttribute('aria-selected', String(selected));
            node.classList.toggle('is-active', selected);
        });
        elements.input.setAttribute('aria-activedescendant', `${name}-suggestion-${next}`);
        elements.list.querySelector(`#${name}-suggestion-${next}`)?.scrollIntoView({block: 'nearest'});
    }

    fields.forEach((name) => {
        const elements = fieldElements(name);
        elements.input.setAttribute('role', 'combobox');
        elements.input.setAttribute('aria-autocomplete', 'list');
        elements.input.setAttribute('aria-expanded', 'false');
        elements.input.setAttribute('aria-controls', `${name}-suggestions`);
        elements.list.id = `${name}-suggestions`;
        state.set(name, {items: [], active: -1});
        elements.input.addEventListener('input', () => {
            elements.code.value = '';
            delete elements.input.dataset.selectedName;
            elements.input.classList.remove('has-selection');
            elements.hint.textContent = 'Choose a station from the catalogue.';
            clearTimeout(debounceTimers.get(name));
            debounceTimers.set(name, setTimeout(() => fetchStations(name, elements.input.value), 220));
        });
        elements.input.addEventListener('keydown', (event) => {
            const current = state.get(name) || {items: [], active: -1};
            if (event.key === 'ArrowDown' && !elements.list.hidden) {
                event.preventDefault();
                activate(name, current.active + 1);
            } else if (event.key === 'ArrowUp' && !elements.list.hidden) {
                event.preventDefault();
                activate(name, current.active - 1);
            } else if (event.key === 'Enter' && current.active >= 0 && current.items[current.active]) {
                event.preventDefault();
                setSelection(name, current.items[current.active]);
            } else if (event.key === 'Escape') {
                closeList(name);
            }
        });
        elements.input.addEventListener('blur', () => setTimeout(() => closeList(name), 120));
        document.querySelector(`[data-clear-station="${name}"]`)?.addEventListener('click', () => {
            elements.input.value = '';
            elements.code.value = '';
            elements.input.classList.remove('has-selection');
            elements.input.focus();
            closeList(name);
        });
    });

    window.RailCrowdStations = {set: setSelection, close: closeList};

    document.getElementById('swap-stations')?.addEventListener('click', () => {
        const origin = fieldElements('origin');
        const destination = fieldElements('destination');
        const first = {text: origin.input.value, code: origin.code.value, name: origin.input.dataset.selectedName};
        const second = {text: destination.input.value, code: destination.code.value, name: destination.input.dataset.selectedName};
        origin.input.value = second.text;
        origin.code.value = second.code;
        destination.input.value = first.text;
        destination.code.value = first.code;
        if (second.name) origin.input.dataset.selectedName = second.name;
        else delete origin.input.dataset.selectedName;
        if (first.name) destination.input.dataset.selectedName = first.name;
        else delete destination.input.dataset.selectedName;
        [origin, destination].forEach((item) => {
            item.input.classList.toggle('has-selection', Boolean(item.code.value));
            closeList(item.input.id.includes('origin') ? 'origin' : 'destination');
        });
    });

    form.addEventListener('submit', (event) => {
        const origin = fieldElements('origin');
        const destination = fieldElements('destination');
        if (!origin.code.value || !destination.code.value) {
            event.preventDefault();
            const missing = !origin.code.value ? origin : destination;
            missing.hint.textContent = 'Select a station from the suggestions before searching.';
            missing.input.focus();
        }
    });
})();
