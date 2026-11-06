/* Route-level accessibility information review. */
(() => {
    const form = document.querySelector('#accessibility-form');
    if (!form) return;
    const results = document.querySelector('#accessibility-results');
    const submit = document.querySelector('#accessibility-submit');
    const travelDate = form.querySelector('[name="travel_date"]');
    if (travelDate) {
        const now = new Date();
        const localToday = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
        travelDate.min = localToday;
        travelDate.value = localToday;
    }
    const create = (tag, className, value) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (value !== undefined) element.textContent = String(value);
        return element;
    };
    function renderSummary(summary) {
        const container = document.querySelector('#accessibility-summary');
        container.replaceChildren();
        const metrics = [
            ['Stations in route', summary.station_count],
            ['Listed available', summary.listed_available],
            ['Limited listings', summary.listed_limited],
            ['No listing', summary.no_listing],
        ];
        metrics.forEach(([label, value]) => {
            const card = create('article', 'accessibility-metric');
            card.append(create('strong', '', value));
            card.append(create('span', '', label));
            container.append(card);
        });
    }
    function renderLegs(legs) {
        const container = document.querySelector('#accessibility-route-legs');
        container.replaceChildren();
        legs.forEach((leg, index) => {
            const card = create('article', 'accessibility-route-leg');
            card.append(create('small', '', `LEG ${index + 1}`));
            card.append(create('strong', '', `${leg.train_number} · ${leg.train_name}`));
            card.append(create('span', '', `${leg.from_code} ${leg.departure || '—'} → ${leg.to_code} ${leg.arrival || '—'}`));
            container.append(card);
        });
    }
    function renderStations(stations) {
        const container = document.querySelector('#accessibility-station-list');
        container.replaceChildren();
        stations.forEach((station) => {
            const card = create('article', `accessibility-station-card accessibility-station-card--${station.overall_status}`);
            const heading = create('header');
            heading.append(create('strong', '', station.station_code));
            heading.append(create('span', '', `${station.listing_count} accessibility listing(s)`));
            card.append(heading);
            const requirements = create('div', 'accessibility-requirement-list');
            station.requirements.forEach((requirement) => {
                const row = create('div', `accessibility-requirement accessibility-requirement--${requirement.status}`);
                row.append(create('strong', '', requirement.label));
                row.append(create('span', '', requirement.status_label || requirement.status.replaceAll('_', ' ')));
                row.append(create('p', '', requirement.explanation));
                row.append(create('p', 'accessibility-requirement__advice', requirement.advice || 'Confirm with station staff.'));
                requirements.append(row);
            });
            card.append(requirements);
            if (station.reminders?.length) {
                const reminders = create('ul', 'accessibility-station-reminders');
                station.reminders.forEach((reminder) => reminders.append(create('li', '', reminder)));
                card.append(reminders);
            }
            if (!station.requirements.length) card.append(create('p', 'empty-inline', 'No specific accessibility needs were selected.'));
            container.append(card);
        });
    }
    function renderQuestions(questions) {
        const container = document.querySelector('#accessibility-followup-list');
        container.replaceChildren();
        questions.forEach((question) => {
            const item = create('article', 'accessibility-followup');
            item.append(create('strong', '', `${question.station_code} · ${question.requirement}`));
            item.append(create('p', '', question.question));
            container.append(item);
        });
        if (!questions.length) container.append(create('p', 'empty-inline', 'No follow-up questions were generated for the selected requirements. Always confirm assistance before travel.'));
    }
    async function search(event) {
        event.preventDefault();
        const origin = form.querySelector('[name="origin"]').value;
        const destination = form.querySelector('[name="destination"]').value;
        if (!origin || !destination || origin === destination) {
            window.alert('Choose two different stations.');
            return;
        }
        const params = new URLSearchParams({origin, destination, travel_date: travelDate?.value || ''});
        form.querySelectorAll('[name="need"]:checked').forEach((input) => params.append('need', input.value));
        submit.disabled = true;
        submit.textContent = 'Checking station information…';
        try {
            const response = await fetch(`${form.dataset.apiUrl}?${params}`, {headers: {'Accept': 'application/json'}});
            const body = await response.json();
            if (!response.ok || !body.ok) throw new Error(body.error || 'Accessibility information could not be loaded.');
            results.hidden = false;
            document.querySelector('#accessibility-route-label').textContent = `${body.origin} → ${body.destination}`;
            const exportLink = document.querySelector('#accessibility-export');
            const exportParams = new URLSearchParams({origin, destination, travel_date: travelDate?.value || ''});
            form.querySelectorAll('[name="need"]:checked').forEach((input) => exportParams.append('need', input.value));
            exportLink.href = `/journeys/api/accessibility/export?${exportParams}`;
            exportLink.hidden = false;
            renderSummary(body.summary);
            renderLegs(body.route || []);
            renderStations(body.stations || []);
            renderQuestions(body.follow_up_questions || []);
            document.querySelector('#accessibility-notice').textContent = [body.summary_text, body.notice, body.route_notice].filter(Boolean).join(' ');
            results.scrollIntoView({behavior: 'smooth', block: 'start'});
        } catch (error) {
            window.alert(error.message);
        } finally {
            submit.disabled = false;
            submit.innerHTML = 'Check station information <span>→</span>';
        }
    }
    form.addEventListener('submit', search);
    const origin = new URLSearchParams(window.location.search).get('origin');
    const destination = new URLSearchParams(window.location.search).get('destination');
    if (origin) form.querySelector('[name="origin"]').value = origin;
    if (destination) form.querySelector('[name="destination"]').value = destination;
})();
