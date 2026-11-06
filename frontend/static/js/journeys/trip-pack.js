/* Print-friendly trip pack actions. */
(() => {
    const button = document.querySelector('#print-trip-pack');
    button?.addEventListener('click', () => {
        button.disabled = true;
        window.print();
        window.setTimeout(() => { button.disabled = false; }, 500);
    });
    window.addEventListener('afterprint', () => {
        if (button) button.disabled = false;
    });
})();
