/* Safe DOM rendering and local sorting for journey option cards. */
(() => {
    const list = document.querySelector('#journey-results-list');
    if (!list) return;
    let options = [];
    const compared = new Set();
    const node = (tag, className, text) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined && text !== null) element.textContent = String(text);
        return element;
    };

    function formatRupees(value) {
        return new Intl.NumberFormat('en-IN', {maximumFractionDigits: 0}).format(Number(value) || 0);
    }

    function crowdClass(crowd) {
        if (!crowd || crowd.average_score === null || crowd.average_score === undefined) return 'unknown';
        if (crowd.average_score < 1.6) return 'low';
        if (crowd.average_score < 2.6) return 'moderate';
        if (crowd.average_score < 3.6) return 'high';
        return 'very-high';
    }

    function buildStationPoint(clock, name, code, end = false) {
        const point = node('div', `timeline-point${end ? ' timeline-point--end' : ''}`);
        point.append(node('strong', '', clock || 'Time unavailable'));
        point.append(node('span', '', name || code || 'Station'));
        point.append(node('small', '', code || ''));
        return point;
    }

    function buildTimeline(option) {
        const timeline = node('div', 'journey-option__timeline');
        const first = option.legs[0];
        const last = option.legs[option.legs.length - 1];
        timeline.append(buildStationPoint(option.departure, first.origin_name, first.origin_code));
        const track = node('div', 'timeline-track');
        track.append(node('span', 'timeline-track__line'));
        track.append(node('span', 'timeline-track__label', option.duration_label));
        track.append(node('span', 'timeline-track__node'));
        timeline.append(track);
        timeline.append(buildStationPoint(option.arrival, last.destination_name, last.destination_code, true));
        return timeline;
    }

    function buildLeg(leg, index, option) {
        const wrapper = node('div', 'option-leg');
        const train = node('div', 'option-leg__train');
        train.append(node('strong', '', leg.train_number));
        train.append(node('span', '', leg.train_name));
        const route = node('div', 'option-leg__route');
        route.append(node('span', '', `${leg.origin_code} · ${leg.departure || 'Time unavailable'}`));
        route.append(node('span', '', `${leg.destination_code} · ${leg.arrival || 'Time unavailable'}`));
        const crowd = node('div', 'option-leg__crowd');
        crowd.append(node('span', `crowd-dot crowd-dot--${crowdClass(leg.crowd)}`));
        crowd.append(node('span', '', leg.crowd?.label || 'No recent report'));
        crowd.append(node('small', '', leg.crowd?.sample_size ? `${leg.crowd.sample_size} reports` : 'No sample'));
        wrapper.append(train, route, crowd);
        if (index < option.legs.length - 1) {
            const transfer = node('div', 'transfer-strip');
            transfer.append(node('span', '', '↳'));
            const wait = option.transfer_minutes ? ` · ${option.transfer_minutes} min total connection time` : '';
            transfer.append(document.createTextNode(`Change at ${leg.destination_name}${wait}`));
            return [wrapper, transfer];
        }
        return [wrapper];
    }

    function buildExplanation(option) {
        const panel = node('div', 'option-explanation');
        panel.dataset.optionExplanation = option.id;
        panel.hidden = true;
        const decision = option.decision_explanation || {};
        panel.append(node('h4', '', decision.headline || 'Planning notes'));
        const reasons = node('ul', 'option-explanation__reasons');
        (decision.reasons || option.explanation || []).forEach((line) => reasons.append(node('li', '', line)));
        panel.append(reasons);
        if (decision.legs?.length) {
            panel.append(node('h5', '', 'Segment details'));
            decision.legs.forEach((leg) => {
                const row = node('div', 'option-explanation__leg');
                row.append(node('strong', '', `${leg.train} · ${leg.segment}`));
                row.append(node('small', '', `${leg.duration} · ${leg.crowd_title}`));
                row.append(node('p', '', leg.crowd_note));
                row.append(node('p', '', leg.type_guidance));
                panel.append(row);
            });
        }
        if (option.accessibility?.station_count) {
            panel.append(node('h5', '', 'Accessibility information'));
            panel.append(node('p', '', `${option.accessibility.stations_with_listings} of ${option.accessibility.station_count} station(s) have community accessibility listings (${option.accessibility.coverage_percent}% listing coverage).`));
            panel.append(node('p', '', option.accessibility.notice || 'Confirm all assistance directly with the station.'));
        }
        if (decision.transfers?.length) {
            panel.append(node('h5', '', 'Connection review'));
            decision.transfers.forEach((transfer) => {
                const row = node('div', 'option-explanation__transfer');
                row.append(node('strong', '', `Transfer ${transfer.number} · ${transfer.label}`));
                row.append(node('p', '', transfer.reason));
                panel.append(row);
            });
        }
        if (decision.caveats?.length) {
            panel.append(node('h5', '', 'Important caveats'));
            const caveats = node('ul');
            decision.caveats.forEach((line) => caveats.append(node('li', '', line)));
            panel.append(caveats);
        }
        panel.append(node('p', '', decision.ranking_note || 'Options are ranked using the selected preference and catalogue data.'));
        panel.append(node('p', '', option.fare?.disclaimer || 'Fare information is indicative only.'));
        return panel;
    }

    function buildCard(option) {
        const card = node('article', 'journey-option');
        card.dataset.optionId = option.id;
        card.dataset.duration = option.duration_minutes;
        card.dataset.transfers = option.transfer_count;
        card.dataset.crowd = option.crowd?.average_score ?? 9;
        const top = node('div', 'journey-option__top');
        top.append(node('div', 'journey-option__rank', `#${option.rank}`));
        const badges = node('div', 'journey-option__badges');
        if (option.recommended) badges.append(node('span', 'option-badge option-badge--recommended', 'Best match'));
        (option.highlights || []).slice(0, 2).forEach((label) => badges.append(node('span', 'option-badge', label)));
        badges.append(node('span', 'option-badge', option.transfer_count === 0 ? 'Direct' : `${option.transfer_count} transfer(s)`));
        top.append(badges, node('span', 'journey-option__duration', option.duration_label));
        card.append(top, buildTimeline(option));
        const legs = node('div', 'journey-option__legs');
        option.legs.forEach((leg, index) => buildLeg(leg, index, option).forEach((element) => legs.append(element)));
        card.append(legs);
        const bottom = node('div', 'journey-option__bottom');
        const fare = node('div', 'option-fare');
        fare.append(node('span', '', 'Indicative fare band'));
        fare.append(node('strong', '', `₹${formatRupees(option.fare?.low)}–₹${formatRupees(option.fare?.high)}`));
        fare.append(node('small', '', `For ${option.fare?.passengers || 1} passenger(s); not official`));
        const explain = node('button', 'btn-option-details', 'Why this option? ＋');
        explain.type = 'button';
        explain.dataset.expandOption = option.id;
        explain.setAttribute('aria-expanded', 'false');
        const compareLabel = node('label', 'option-compare-choice');
        const compareInput = node('input');
        compareInput.type = 'checkbox';
        compareInput.checked = compared.has(option.id);
        compareInput.dataset.compareOption = option.id;
        const compareText = node('span', '', 'Compare');
        compareLabel.append(compareInput, compareText);
        const save = node('button', 'btn-save-option', 'Save journey →');
        save.type = 'button';
        save.dataset.saveOption = option.id;
        bottom.append(fare, compareLabel, explain, save);
        card.append(bottom, buildExplanation(option));
        return card;
    }

    function render(nextOptions, metadata) {
        options = Array.isArray(nextOptions) ? nextOptions.slice() : [];
        compared.clear();
        list.replaceChildren();
        options.forEach((option) => list.append(buildCard(option)));
        updateComparison();
        const summary = document.querySelector('#results-summary');
        if (summary && metadata) {
            const quality = metadata.route_quality || metadata.routeQuality || {};
            const types = [quality.has_direct ? 'direct options' : '', quality.has_connecting ? 'connecting options' : ''].filter(Boolean).join(' and ');
            const minimum = quality.duration_range?.minimum;
            const maximum = quality.duration_range?.maximum;
            const duration = minimum !== null && maximum !== null ? ` Duration range: ${minimum}–${maximum} minutes.` : '';
            summary.textContent = `${metadata.count} option(s) for ${metadata.origin} → ${metadata.destination} on ${metadata.travel_date}.${types ? ` Includes ${types}.` : ''}${duration}`;
        }
    }

    function sortOptions(mode) {
        const sorted = options.slice();
        if (mode === 'duration') sorted.sort((a, b) => a.duration_minutes - b.duration_minutes);
        if (mode === 'transfers') sorted.sort((a, b) => a.transfer_count - b.transfer_count || a.duration_minutes - b.duration_minutes);
        if (mode === 'crowd') sorted.sort((a, b) => (a.crowd?.average_score ?? 9) - (b.crowd?.average_score ?? 9));
        if (mode === 'rank') sorted.sort((a, b) => a.rank - b.rank);
        list.replaceChildren();
        sorted.forEach((option) => list.append(buildCard(option)));
    }

    function updateComparison() {
        const panel = document.querySelector('#journey-compare');
        const table = document.querySelector('#journey-compare-table');
        if (!panel || !table) return;
        const selected = options.filter((item) => compared.has(item.id));
        panel.hidden = selected.length < 2;
        table.replaceChildren();
        if (selected.length < 2) return;
        const columns = [
            ['Overall time', (item) => item.duration_label],
            ['Transfers', (item) => String(item.transfer_count)],
            ['Departure', (item) => item.departure || '—'],
            ['Arrival', (item) => item.arrival || '—'],
            ['Crowd sample', (item) => item.crowd?.observed_legs ? `${item.crowd.observed_legs} leg(s)` : 'No recent sample'],
            ['Fare estimate', (item) => `₹${formatRupees(item.fare?.low)}–₹${formatRupees(item.fare?.high)}`],
        ];
        const tableNode = node('table', 'compare-table');
        const head = node('thead');
        const headerRow = node('tr');
        headerRow.append(node('th', '', 'Metric'));
        selected.forEach((item) => headerRow.append(node('th', '', `Option ${item.rank}`)));
        head.append(headerRow);
        tableNode.append(head);
        const body = node('tbody');
        columns.forEach(([label, getter]) => {
            const row = node('tr');
            row.append(node('th', '', label));
            selected.forEach((item) => row.append(node('td', '', getter(item))));
            body.append(row);
        });
        tableNode.append(body);
        table.append(tableNode);
        panel.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    }

    list.addEventListener('change', (event) => {
        const input = event.target.closest('[data-compare-option]');
        if (!input) return;
        if (input.checked) {
            if (compared.size >= 3) {
                input.checked = false;
                window.alert('Compare up to three journey options at a time.');
                return;
            }
            compared.add(input.dataset.compareOption);
        } else {
            compared.delete(input.dataset.compareOption);
        }
        updateComparison();
    });

    document.querySelector('#clear-compare')?.addEventListener('click', () => {
        compared.clear();
        list.querySelectorAll('[data-compare-option]').forEach((input) => { input.checked = false; });
        updateComparison();
    });

    list.addEventListener('click', (event) => {
        const button = event.target.closest('[data-expand-option]');
        if (!button) return;
        const panel = list.querySelector(`[data-option-explanation="${CSS.escape(button.dataset.expandOption)}"]`);
        if (!panel) return;
        panel.hidden = !panel.hidden;
        button.setAttribute('aria-expanded', String(!panel.hidden));
        button.textContent = panel.hidden ? 'Why this option? ＋' : 'Hide details −';
    });

    document.querySelector('#results-sort')?.addEventListener('change', (event) => sortOptions(event.target.value));
    window.RailCrowdJourneyResults = {render, sortOptions, getOptions: () => options.slice(), updateComparison};
})();
