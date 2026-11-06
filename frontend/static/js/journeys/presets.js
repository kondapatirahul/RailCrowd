/* Saved search preset page controls. */
(() => {
    document.querySelectorAll('[data-use-preset]').forEach((link) => {
        link.addEventListener('click', () => {
            link.setAttribute('aria-busy', 'true');
            link.textContent = 'Loading preset…';
        });
    });
    document.querySelectorAll('.preset-card form[action*="/delete"]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (!window.confirm('Delete this saved search preset?')) event.preventDefault();
        });
    });
})();
