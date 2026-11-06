/* Search history page confirmations and repeat-route affordances. */
(() => {
    const form = document.querySelector('[data-confirm-clear]');
    form?.addEventListener('submit', (event) => {
        if (!window.confirm('Clear all recent journey searches from your account?')) event.preventDefault();
    });
    document.querySelectorAll('.history-repeat').forEach((link) => {
        link.addEventListener('click', () => {
            link.setAttribute('aria-busy', 'true');
            link.textContent = 'Opening planner…';
        });
    });
})();
