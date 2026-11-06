/* Station connectivity explorer powered by the public timetable graph API. */
(() => {
    const section = document.querySelector('.station-connections');
    if (!section) return;
    const grid = section.querySelector('#station-connection-grid');
    const count = section.querySelector('#connection-count');
    const notice = section.querySelector('#connection-notice');
    const make = (tag, className, text) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = String(text);
        return element;
    };
    async function load() {
        try {
            const response = await fetch(section.dataset.connectionsUrl, {headers: {'Accept': 'application/json'}});
            const body = await response.json();
            if (!response.ok || !body.ok) throw new Error(body.error || 'Connections are unavailable.');
            const connections = body.connections;
            grid.replaceChildren();
            count.textContent = `${connections.destination_count} destination(s)`;
            connections.destinations.forEach((item) => {
                const card = make('article', 'station-connection-card');
                const heading = make('div', 'station-connection-card__heading');
                heading.append(make('strong', '', item.station_name));
                heading.append(make('span', '', item.station_code));
                const meta = make('p', '', `${item.service_count} listed train service(s)`);
                const fastest = make('div', 'station-connection-card__fastest');
                fastest.append(make('strong', '', item.fastest_duration_label));
                fastest.append(make('small', '', `${item.fastest_train_number} · ${item.fastest_train_name}`));
                const departure = make('small', 'station-connection-card__departure', `Earliest listed departure: ${item.earliest_departure || 'Not available'}`);
                const link = make('a', '', 'Plan a journey →');
                link.href = `/journeys/?origin=${encodeURIComponent(connections.origin)}&destination=${encodeURIComponent(item.station_code)}`;
                card.append(heading, meta, fastest, departure, link);
                grid.append(card);
            });
            if (!connections.destinations.length) grid.append(make('p', 'empty-inline', 'No direct catalogue connections were found for this station.'));
            notice.textContent = connections.notice;
        } catch (error) {
            grid.replaceChildren(make('p', 'empty-inline', error.message));
            count.textContent = 'Unavailable';
        }
    }
    load();
})();
