/* Dialog, checklist and personal journey detail interactions. */
(() => {
    const dialogs = [...document.querySelectorAll('.journey-dialog')];
    if (!dialogs.length) return;
    function openDialog(id) {
        const dialog = document.getElementById(id);
        if (!dialog || typeof dialog.showModal !== 'function') return;
        dialog.showModal();
        dialog.querySelector('input:not([type="hidden"]), textarea, button')?.focus();
    }
    function closeDialog(dialog) {
        if (dialog?.open) dialog.close();
    }
    document.addEventListener('click', (event) => {
        const opener = event.target.closest('[data-open-dialog]');
        if (opener) openDialog(opener.dataset.openDialog);
        const closer = event.target.closest('[data-close-dialog]');
        if (closer) closeDialog(closer.closest('dialog'));
    });
    dialogs.forEach((dialog) => {
        dialog.addEventListener('click', (event) => {
            if (event.target === dialog) closeDialog(dialog);
        });
        dialog.addEventListener('close', () => {
            const opener = document.querySelector(`[data-open-dialog="${dialog.id}"]`);
            opener?.focus();
        });
    });

    const duplicateDate = document.querySelector('#duplicate-date');
    if (duplicateDate) {
        const today = new Date();
        duplicateDate.min = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    }

    document.querySelectorAll('.checklist-check').forEach((button) => {
        button.addEventListener('click', () => {
            button.classList.add('is-submitting');
            button.setAttribute('aria-busy', 'true');
        });
    });

    const noteForms = document.querySelectorAll('.journey-note-form, .notes-card form');
    noteForms.forEach((form) => {
        form.addEventListener('submit', (event) => {
            const required = [...form.querySelectorAll('input[required], textarea[required]')];
            const invalid = required.find((field) => !field.value.trim());
            if (invalid) {
                event.preventDefault();
                invalid.focus();
                invalid.setCustomValidity('Please enter a value before saving.');
                invalid.reportValidity();
                invalid.addEventListener('input', () => invalid.setCustomValidity(''), {once: true});
            }
        });
    });

    document.querySelectorAll('form[action*="/status"]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            const target = form.querySelector('[name="status"]')?.value;
            if (target === 'cancelled' && !window.confirm('Cancel this journey plan? This action cannot be undone.')) {
                event.preventDefault();
            }
            if (target === 'completed' && !window.confirm('Mark this journey as completed?')) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll('.journey-alert__actions button').forEach((button) => {
        button.addEventListener('click', () => {
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
        });
    });

    function escapeCalendarText(value) {
        return String(value ?? '').replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
    }

    function calendarStamp(dateText, clockText, offsetDays = 0) {
        if (!dateText || !clockText || !/^\d{2}:\d{2}$/.test(clockText)) return null;
        const [year, month, day] = dateText.split('-').map(Number);
        const [hour, minute] = clockText.split(':').map(Number);
        const date = new Date(year, month - 1, day + Number(offsetDays || 0), hour, minute, 0);
        const pad = (value) => String(value).padStart(2, '0');
        return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}T${pad(date.getHours())}${pad(date.getMinutes())}00`;
    }

    function downloadCalendar() {
        const journey = window.RAILCROWD_JOURNEY;
        if (!journey || !Array.isArray(journey.legs) || !journey.legs.length) return;
        const first = journey.legs[0];
        const last = journey.legs[journey.legs.length - 1];
        const start = calendarStamp(window.RAILCROWD_TRAVEL_DATE, first.departure, first.departure_offset_days);
        const end = calendarStamp(window.RAILCROWD_TRAVEL_DATE, last.arrival, last.arrival_offset_days);
        if (!start || !end) {
            window.alert('Timetable times are incomplete. Add the journey manually after confirming the schedule.');
            return;
        }
        const now = new Date();
        const pad = (value) => String(value).padStart(2, '0');
        const stamp = `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}T${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}Z`;
        const description = journey.legs.map((leg, index) => `${index + 1}. ${leg.train_number} ${leg.train_name}: ${leg.from.code} ${leg.departure || ''} to ${leg.to.code} ${leg.arrival || ''}`).join('\n');
        const lines = [
            'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//RailCrowd//Journey Workspace//EN',
            'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'BEGIN:VEVENT',
            `UID:railcrowd-${journey.id}-${stamp}@railcrowd.local`, `DTSTAMP:${stamp}`,
            `DTSTART:${start}`, `DTEND:${end}`,
            `SUMMARY:${escapeCalendarText(journey.title)}`,
            `LOCATION:${escapeCalendarText(`${journey.origin.name} to ${journey.destination.name}`)}`,
            `DESCRIPTION:${escapeCalendarText(description)}\nCommunity timetable snapshot only. Verify the official service schedule.`,
            'END:VEVENT', 'END:VCALENDAR', ''
        ];
        const blob = new Blob([lines.join('\r\n')], {type: 'text/calendar;charset=utf-8'});
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `railcrowd-journey-${journey.id}.ics`;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
    }

    document.querySelector('#export-calendar')?.addEventListener('click', downloadCalendar);
    document.querySelector('#print-journey')?.addEventListener('click', () => window.print());

    async function loadReminders() {
        const trigger = document.querySelector('#show-reminders');
        const panel = document.querySelector('#reminder-panel');
        const list = document.querySelector('#reminder-list');
        const notice = document.querySelector('#reminder-notice');
        if (!trigger || !panel || !list) return;
        trigger.disabled = true;
        trigger.textContent = 'Loading…';
        try {
            const response = await fetch(trigger.dataset.remindersUrl, {
                credentials: 'same-origin', headers: {'Accept': 'application/json'}
            });
            const body = await response.json();
            if (!response.ok || !body.ok) throw new Error(body.error || 'Reminders are unavailable.');
            list.replaceChildren();
            (body.schedule.reminders || []).forEach((reminder) => {
                const row = document.createElement('article');
                row.className = `reminder-row reminder-row--${reminder.state}`;
                const copy = document.createElement('div');
                const title = document.createElement('strong');
                title.textContent = reminder.label;
                const description = document.createElement('p');
                description.textContent = reminder.description;
                const time = document.createElement('small');
                time.textContent = new Date(reminder.suggested_at).toLocaleString();
                copy.append(title, description, time);
                const state = document.createElement('span');
                state.textContent = reminder.state === 'upcoming' ? 'Upcoming' : 'Due / passed';
                row.append(copy, state);
                list.append(row);
            });
            notice.textContent = body.schedule.notice || '';
            panel.hidden = false;
            panel.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        } catch (error) {
            notice.textContent = error.message;
            panel.hidden = false;
        } finally {
            trigger.disabled = false;
            trigger.textContent = 'Reminders';
        }
    }
    document.querySelector('#show-reminders')?.addEventListener('click', loadReminders);
    document.querySelector('#close-reminders')?.addEventListener('click', () => {
        document.querySelector('#reminder-panel').hidden = true;
    });

    const hash = window.location.hash;
    if (hash) {
        const target = document.querySelector(hash);
        if (target) setTimeout(() => target.scrollIntoView({behavior: 'smooth', block: 'start'}), 80);
    }
})();
