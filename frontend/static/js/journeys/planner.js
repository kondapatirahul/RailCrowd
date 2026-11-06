/* Search orchestration and passenger-safe save requests. */
(() => {
    const form = document.querySelector('#journey-search-form');
    if (!form) return;
    const resultsSection = document.querySelector('#journey-results');
    const errorBox = document.querySelector('#planner-error');
    const submitButton = document.querySelector('#search-journeys');
    const list = document.querySelector('#journey-results-list');
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || form.querySelector('[name="csrf_token"]')?.value || '';
    let lastQuery = null;
    let lastResult = null;

    function readForm() {
        const data = new FormData(form);
        const payload = Object.fromEntries(data.entries());
        payload.origin = form.querySelector('[name="origin_code"]').value;
        payload.destination = form.querySelector('[name="destination_code"]').value;
        payload.train_types = Array.from(form.querySelectorAll('[name="train_types"]:checked'), (field) => field.value);
        payload.avoid_overnight = form.querySelector('[name="avoid_overnight"]')?.checked || false;
        payload.avoid_high_crowd = form.querySelector('[name="avoid_high_crowd"]')?.checked || false;
        payload.accessibility_required = form.querySelector('[name="accessibility_required"]')?.checked || false;
        payload.departure_window = payload.departure_window === 'any' ? '' : payload.departure_window;
        return payload;
    }

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
        errorBox.focus?.();
    }

    function clearError() {
        errorBox.textContent = '';
        errorBox.hidden = true;
    }

    function setBusy(busy) {
        submitButton.disabled = busy;
        submitButton.classList.toggle('is-loading', busy);
        submitButton.querySelector('span:nth-child(2)').textContent = busy ? 'Finding options…' : 'Find journey options';
        form.setAttribute('aria-busy', String(busy));
    }

    async function postJson(url, payload) {
        const response = await fetch(url, {
            method: 'POST', credentials: 'same-origin',
            headers: {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRFToken': csrf},
            body: JSON.stringify(payload),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok || body.ok === false) {
            const error = new Error(body.error || `Request failed (${response.status}).`);
            error.status = response.status;
            throw error;
        }
        return body;
    }

    async function search(payload) {
        clearError();
        setBusy(true);
        try {
            const body = await postJson(form.dataset.searchUrl, payload);
            lastQuery = payload;
            lastResult = body.result;
            window.RailCrowdJourneyResults?.render(body.options || [], body.result);
            resultsSection.hidden = false;
            resultsSection.scrollIntoView({behavior: 'smooth', block: 'start'});
            document.querySelector('#results-summary').textContent = `${body.result.count} option(s) for ${body.result.origin} → ${body.result.destination} on ${body.result.travel_date}.`;
            const filterNotes = body.result.filter_summary?.explanations || [];
            document.querySelector('#results-notice').textContent = [body.result.notice, ...filterNotes].join(' ');
            document.querySelector('#no-results').hidden = body.result.count > 0;
            list.hidden = body.result.count === 0;
            if (body.result.count === 0 && body.result.filter_summary?.guidance) {
                const guidance = body.result.filter_summary.guidance;
                const empty = document.querySelector('#no-results');
                empty.querySelector('h3').textContent = guidance.headline;
                empty.querySelector('p').textContent = [guidance.next_step, ...(guidance.suggestions || [])].join(' ');
            }
        } catch (error) {
            showError(error.message || 'Journey search could not be completed.');
        } finally {
            setBusy(false);
        }
    }

    async function save(optionId, button) {
        if (!window.RAILCROWD_AUTHENTICATED) {
            const destination = `${window.location.pathname}${window.location.search}`;
            window.location.assign(`${form.dataset.loginUrl}?next=${encodeURIComponent(destination)}`);
            return;
        }
        if (!lastQuery) return;
        button.disabled = true;
        button.classList.add('is-loading');
        try {
            const body = await postJson(form.dataset.saveUrl, {...lastQuery, option_id: optionId});
            window.location.assign(body.redirect_url);
        } catch (error) {
            showError(error.message || 'This journey could not be saved. Search again and retry.');
            button.disabled = false;
            button.classList.remove('is-loading');
        }
    }

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const payload = readForm();
        if (!payload.origin || !payload.destination) {
            showError('Select both stations from the catalogue.');
            return;
        }
        if (!payload.travel_date) {
            showError('Choose a travel date.');
            return;
        }
        search(payload);
    });

    list.addEventListener('click', (event) => {
        const button = event.target.closest('[data-save-option]');
        if (button) save(button.dataset.saveOption, button);
    });

    document.querySelector('#advanced-toggle')?.addEventListener('click', (event) => {
        const button = event.currentTarget;
        const panel = document.querySelector('#advanced-fields');
        const expanded = button.getAttribute('aria-expanded') === 'true';
        button.setAttribute('aria-expanded', String(!expanded));
        panel.hidden = expanded;
        button.querySelector('.advanced-toggle__icon').textContent = expanded ? '＋' : '−';
    });

    document.querySelector('#edit-search')?.addEventListener('click', () => {
        document.querySelector('#journey-search-form').scrollIntoView({behavior: 'smooth'});
        document.querySelector('#journey-origin').focus();
    });

    const dateInput = document.querySelector('#travel-date');
    if (dateInput && !dateInput.value) {
        const today = new Date();
        const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
        dateInput.value = localDate;
        dateInput.min = localDate;
    }
    document.querySelector('#save-preset-form')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const feedback = document.querySelector('#preset-feedback');
        const title = document.querySelector('#preset-title').value.trim();
        if (!lastQuery || !title) {
            feedback.textContent = 'Run a search and enter a preset name first.';
            return;
        }
        feedback.textContent = 'Saving preset…';
        try {
            const response = await fetch('/journeys/presets', {
                method: 'POST', credentials: 'same-origin',
                headers: {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRFToken': csrf},
                body: JSON.stringify({title, criteria: lastQuery}),
            });
            const body = await response.json();
            if (!response.ok || !body.ok) throw new Error(body.error || 'Could not save preset.');
            feedback.textContent = body.message || 'Preset saved.';
            document.querySelector('#preset-title').value = '';
        } catch (error) {
            feedback.textContent = error.message;
        }
    });

    async function selectStationByCode(fieldName, code) {
        const response = await fetch(`${form.dataset.stationUrl}?q=${encodeURIComponent(code)}`, {credentials: 'same-origin'});
        if (!response.ok) return;
        const data = await response.json();
        const station = (data.stations || []).find((item) => item.code.toUpperCase() === code.toUpperCase());
        if (station) window.RailCrowdStations?.set(fieldName, station);
    }

    async function applyCriteria(criteria) {
        if (!criteria || !criteria.origin || !criteria.destination) return;
        await Promise.all([
            selectStationByCode('origin', criteria.origin),
            selectStationByCode('destination', criteria.destination),
        ]);
        ['travel_date', 'passenger_count', 'sort', 'max_transfers', 'min_transfer_minutes', 'departure_window', 'coach_preference', 'max_duration_minutes', 'max_crowd_score'].forEach((key) => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field && criteria[key] !== undefined && criteria[key] !== null) field.value = criteria[key];
        });
        const selectedTypes = new Set(criteria.train_types || []);
        form.querySelectorAll('[name="train_types"]').forEach((field) => { field.checked = selectedTypes.has(field.value); });
        ['avoid_overnight', 'avoid_high_crowd', 'accessibility_required', 'require_crowd_sample', 'avoid_special_services'].forEach((key) => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) field.checked = Boolean(criteria[key]);
        });
    }

    const query = new URLSearchParams(window.location.search);
    const presetId = query.get('preset');
    if (presetId && window.RAILCROWD_AUTHENTICATED) {
        fetch(`/journeys/presets/${encodeURIComponent(presetId)}/use`, {credentials: 'same-origin'})
            .then((response) => response.ok ? response.json() : null)
            .then((body) => body?.criteria && applyCriteria(body.criteria))
            .catch(() => showError('This saved preset could not be loaded.'));
    } else if (query.get('origin') && query.get('destination')) {
        applyCriteria({origin: query.get('origin'), destination: query.get('destination'), travel_date: query.get('travel_date') || dateInput?.value});
    }

    window.RailCrowdJourneyPlanner = {search, applyCriteria, getLastQuery: () => lastQuery, getLastResult: () => lastResult};
})();
