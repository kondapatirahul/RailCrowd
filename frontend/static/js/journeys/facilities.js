/* Client-side station facility filters and status explanations. */
(() => {
    const grid = document.querySelector('#facility-grid');
    if (!grid) return;
    const typeFilter = document.querySelector('#facility-type-filter');
    const statusFilter = document.querySelector('#facility-status-filter');
    const accessibleFilter = document.querySelector('#facility-accessible-filter');
    const cards = [...grid.querySelectorAll('.facility-card')];
    const empty = document.createElement('p');
    empty.className = 'empty-inline facility-filter-empty';
    empty.textContent = 'No facilities match these filters. Clear one or more filters to see other listings.';
    empty.hidden = true;
    grid.append(empty);

    function applyFilters() {
        let visible = 0;
        cards.forEach((card) => {
            const matchesType = !typeFilter.value || card.dataset.facilityType === typeFilter.value;
            const matchesStatus = !statusFilter.value || card.dataset.facilityStatus === statusFilter.value;
            const matchesAccess = !accessibleFilter.checked || card.dataset.accessible === 'yes';
            const show = matchesType && matchesStatus && matchesAccess;
            card.hidden = !show;
            visible += Number(show);
        });
        empty.hidden = visible > 0;
        grid.dataset.visibleCount = String(visible);
    }

    [typeFilter, statusFilter, accessibleFilter].forEach((control) => control?.addEventListener('change', applyFilters));
    document.querySelectorAll('.facility-feedback form').forEach((form) => {
        form.addEventListener('submit', (event) => {
            const rating = Number(form.querySelector('[name="rating"]')?.value || 0);
            if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
                event.preventDefault();
                form.querySelector('[name="rating"]')?.focus();
            }
        });
    });
    document.querySelectorAll('.facility-card').forEach((card) => {
        const status = card.dataset.facilityStatus;
        const explanation = {
            available: 'A passenger recently marked this facility as available.',
            limited: 'A passenger reported limited access or service.',
            unavailable: 'A passenger reported that this facility was unavailable.',
            unknown: 'The current operating status has not been confirmed.',
        };
        card.querySelector('.facility-status')?.setAttribute('title', explanation[status] || explanation.unknown);
    });
})();
