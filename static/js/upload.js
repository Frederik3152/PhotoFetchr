// Upload page: a card per photo with its own date, country and people.
// Each photo is analysed as soon as it is added (date from EXIF, faces and suggested
// people from the faces service), and uploaded one at a time.
(function () {
    const people = JSON.parse(document.getElementById('uc-people-data').textContent);
    const nameOf = id => (people.find(p => p.id === id) || {}).name || `#${id}`;

    const $ = id => document.getElementById(id);
    const grid = $('uc-grid');
    const fileInput = $('uc-file-input');
    const countrySelect = $('uc-country');

    let photos = [];
    let nextKey = 1;
    const batch = { dateMode: 'photo', date: '', people: new Set() };

    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

    // ---- Adding and analysing photos -------------------------------------------------

    function addFiles(files) {
        const known = new Set(photos.map(p => p.file.name + ':' + p.file.size));
        for (const file of files) {
            if (!file.type.startsWith('image/') || known.has(file.name + ':' + file.size)) continue;
            photos.push({
                key: nextKey++, file, url: URL.createObjectURL(file), status: 'analysing',
                taken: null, date: '', dateEdited: false, country: '',
                faces: [], facesAvailable: true, extra: new Set(), selected: false,
            });
        }
        render();
        analyseQueue();
    }

    let analysing = 0;
    function analyseQueue() {
        while (analysing < 2) {
            const photo = photos.find(p => p.status === 'analysing' && !p.started);
            if (!photo) return;
            photo.started = true;
            analysing++;
            analyse(photo).finally(() => { analysing--; analyseQueue(); });
        }
    }

    async function analyse(photo) {
        const body = new FormData();
        body.append('photo', photo.file);
        try {
            const res = await fetch('/api/upload/analyze', { method: 'POST', body });
            const data = await res.json();
            photo.taken = data.taken;
            if (!photo.dateEdited) photo.date = data.taken || '';
            photo.facesAvailable = data.faces !== null;
            photo.faces = (data.faces || []).map(f => ({
                box: f.box, suggestion: f.person,
                state: f.person ? 'suggested' : 'unknown', personId: null,
            }));
        } catch (e) {
            photo.facesAvailable = false;
        }
        if (photo.status === 'analysing') photo.status = 'ready';
        render();
    }

    // ---- What a photo will be saved with ---------------------------------------------

    function dateFor(photo) {
        return batch.dateMode === 'same' ? batch.date : photo.date;
    }

    function countryFor(photo) {
        return photo.country || (countrySelect.value !== '__NEW__' ? countrySelect.value : '');
    }

    function tagsFor(photo) {
        const ids = new Set([...batch.people, ...photo.extra]);
        photo.faces.forEach(f => { if (f.personId) ids.add(f.personId); });
        return ids;
    }

    // Faces whose person the uploader confirmed become reference faces for later
    // suggestions. A photo with one face and one person is unambiguous too.
    function assignmentsFor(photo) {
        const out = {};
        photo.faces.forEach((f, i) => { if (f.personId) out[i] = f.personId; });
        const tags = tagsFor(photo);
        if (!Object.keys(out).length && photo.faces.length === 1 && photo.faces[0].state === 'unknown' && tags.size === 1) {
            out[0] = [...tags][0];
        }
        return out;
    }

    // ---- Rendering ------------------------------------------------------------------

    function render() {
        const active = photos.filter(p => p.status !== 'removed');
        const hasPhotos = active.length > 0;
        $('uc-drop').hidden = hasPhotos;
        $('uc-batch').hidden = !hasPhotos;
        $('uc-footer').hidden = !hasPhotos;
        $('uc-add-more').hidden = !hasPhotos;

        const pending = active.filter(p => p.status !== 'done');
        const faces = pending.reduce((n, p) => n + p.faces.length, 0);
        const toCheck = pending.reduce((n, p) => n + p.faces.filter(f => f.state === 'suggested').length, 0);
        const noDate = pending.filter(p => p.status !== 'analysing' && !dateFor(p)).length;
        const analysingCount = pending.filter(p => p.status === 'analysing').length;
        const parts = [plural(pending.length, 'photo', 'photos') + ' ready'];
        if (analysingCount) parts.push(`reading ${analysingCount}…`);
        if (faces) parts.push(plural(faces, 'face', 'faces') + ' found');
        if (toCheck) parts.push(plural(toCheck, 'suggestion', 'suggestions') + ' to check');
        if (noDate) parts.push(plural(noDate, 'photo needs', 'photos need') + ' a date');
        $('uc-summary').textContent = hasPhotos ? parts.join(' · ')
            : 'Add photos, check the date, country and people, then upload.';

        const selected = pending.filter(p => p.selected).length;
        $('uc-bulk').hidden = selected === 0;
        $('uc-bulk-count').textContent = `${selected} selected`;
        $('uc-upload').textContent = pending.length ? `Upload ${plural(pending.length, 'photo', 'photos')}` : 'Upload';
        $('uc-upload').disabled = pending.length === 0 || pending.some(p => p.status === 'analysing' || p.status === 'uploading');

        renderBatchPeople();
        grid.innerHTML = active.map(renderCard).join('');
    }

    function renderBatchPeople() {
        const box = $('uc-batch-people');
        box.querySelectorAll('.uc-chip').forEach(el => el.remove());
        for (const id of batch.people) {
            box.insertAdjacentHTML('afterbegin',
                `<span class="uc-chip uc-chip--kept">${esc(nameOf(id))}<button type="button" data-batch-remove="${id}" aria-label="Remove ${esc(nameOf(id))} from all photos">×</button></span>`);
        }
    }

    function renderCard(p) {
        const done = p.status === 'done';
        const date = dateFor(p);
        let dateNote;
        if (batch.dateMode === 'same') dateNote = '<span class="uc-badge">same for all</span>';
        else if (!date) dateNote = '<span class="uc-badge uc-badge--warn">set a date</span>';
        else if (p.taken && date === p.taken && !p.dateEdited) dateNote = '<span class="uc-badge">from photo</span>';
        else dateNote = '<span class="uc-badge">set by you</span>';

        const countries = [...countrySelect.options].map(o => o.value).filter(v => v && v !== '__NEW__');
        const batchCountry = countrySelect.value && countrySelect.value !== '__NEW__' ? countrySelect.value : '';
        const countryOptions = [`<option value="">${batchCountry ? `As batch (${esc(batchCountry)})` : 'Choose country'}</option>`]
            .concat(countries.map(c => `<option value="${esc(c)}"${c === p.country ? ' selected' : ''}>${esc(c)}</option>`)).join('');

        const unknownFaces = p.faces.map((f, i) => ({ f, i })).filter(({ f }) => f.state === 'unknown' || f.state === 'rejected');
        const chips = [];
        p.faces.forEach((f, i) => {
            if (f.state === 'suggested') {
                const s = f.suggestion;
                chips.push(`<span class="uc-chip ${s.unsure ? 'uc-chip--unsure' : 'uc-chip--suggested'}">
                    <button type="button" data-keep="${i}" aria-label="Keep ${esc(s.name)}">${esc(s.name)}${s.unsure ? '?' : ''}</button>
                    <span class="uc-score">${Math.min(99, Math.round(s.likelihood * 100))}%</span>
                    <button type="button" data-reject="${i}" aria-label="Not ${esc(s.name)}">×</button></span>`);
            } else if (f.personId) {
                chips.push(`<span class="uc-chip uc-chip--kept">${esc(nameOf(f.personId))}
                    <button type="button" data-unassign="${i}" aria-label="Remove ${esc(nameOf(f.personId))}">×</button></span>`);
            }
        });
        for (const id of p.extra) {
            chips.push(`<span class="uc-chip uc-chip--kept">${esc(nameOf(id))}
                <button type="button" data-extra-remove="${id}" aria-label="Remove ${esc(nameOf(id))}">×</button></span>`);
        }
        for (const id of batch.people) {
            chips.push(`<span class="uc-chip uc-chip--batch" title="Added to all photos">${esc(nameOf(id))}</span>`);
        }
        if (unknownFaces.length === 1) {
            chips.push(`<button type="button" class="uc-chip-add uc-chip-add--face" data-name-face="${unknownFaces[0].i}">Who is this?</button>`);
        } else if (unknownFaces.length > 1) {
            chips.push(`<span class="uc-hint">${unknownFaces.length} faces without a name: click a face to name it</span>`);
        }
        chips.push(`<button type="button" class="uc-chip-add" data-add-person>+ Person</button>`);

        const boxes = p.faces.map((f, i) => {
            const [x1, y1, x2, y2] = f.box;
            const named = f.personId || f.state === 'suggested';
            const label = f.personId ? nameOf(f.personId) : f.state === 'suggested' ? f.suggestion.name + (f.suggestion.unsure ? '?' : '') : '?';
            const cls = f.personId ? 'kept' : f.state === 'suggested' ? (f.suggestion.unsure ? 'unsure' : 'suggested') : 'unknown';
            const action = f.state === 'suggested' ? `data-keep="${i}"` : f.personId ? '' : `data-name-face="${i}"`;
            const aria = f.state === 'suggested' ? `Keep ${esc(label)}` : named ? esc(label) : 'Name this face';
            return `<button type="button" class="uc-face uc-face--${cls}" ${action} aria-label="${aria}"
                style="left:${x1 * 100}%;top:${y1 * 100}%;width:${(x2 - x1) * 100}%;height:${(y2 - y1) * 100}%">
                <span>${esc(label)}</span></button>`;
        }).join('');

        let status = '';
        if (p.status === 'analysing') status = '<div class="uc-status">Reading photo…</div>';
        else if (p.status === 'uploading') status = '<div class="uc-status">Uploading…</div>';
        else if (done) status = `<div class="uc-status uc-status--done">Saved as #${p.savedId}</div>`;
        else if (p.status === 'failed') status = `<div class="uc-status uc-status--error">Failed: ${esc(p.error)}</div>`;
        else if (!p.facesAvailable) status = '<div class="uc-status">No people suggestions for this photo</div>';

        return `<article class="uc-card${p.selected ? ' is-selected' : ''}${done ? ' is-done' : ''}" data-key="${p.key}">
            <div class="uc-photo">
                <div class="uc-photo-frame">
                    <img src="${p.url}" alt="${esc(p.file.name)}">
                    ${boxes}
                </div>
                <label class="uc-select"><input type="checkbox" data-select ${p.selected ? 'checked' : ''} ${done ? 'disabled' : ''}> Select</label>
            </div>
            <div class="uc-card-body">
                <div class="uc-file">${esc(p.file.name)}</div>
                <div class="uc-row">
                    <input type="date" class="form-control uc-input" data-date value="${esc(date)}" aria-label="Date taken" ${batch.dateMode === 'same' || done ? 'disabled' : ''}>
                    ${dateNote}
                </div>
                <select class="form-control uc-input" data-country aria-label="Country" ${done ? 'disabled' : ''}>${countryOptions}</select>
                <div class="uc-chips">${chips.join('')}</div>
                ${status}
            </div>
        </article>`;
    }

    // ---- Person picker -----------------------------------------------------------

    const personDialog = $('uc-person-dialog');
    let onPick = null;

    function pickPerson(title, callback) {
        $('uc-person-title').textContent = title;
        $('uc-person-search').value = '';
        onPick = callback;
        renderPersonList('');
        personDialog.showModal();
        $('uc-person-search').focus();
    }

    function renderPersonList(term) {
        const t = term.trim().toLowerCase();
        $('uc-person-list').innerHTML = people.filter(p => p.name.toLowerCase().includes(t))
            .map(p => `<button type="button" class="uc-person" data-pick="${p.id}">${esc(p.name)}</button>`).join('')
            || '<p class="uc-hint">Nobody with that name</p>';
    }

    $('uc-person-search').addEventListener('input', e => renderPersonList(e.target.value));
    $('uc-person-list').addEventListener('click', e => {
        const btn = e.target.closest('[data-pick]');
        if (!btn) return;
        personDialog.close();
        if (onPick) onPick(Number(btn.dataset.pick));
        render();
    });

    // ---- Date / country prompt for bulk edits ----------------------------------------

    function askValue(kind) {
        return new Promise(resolve => {
            const dialog = $('uc-value-dialog');
            $('uc-value-title').textContent = kind === 'date' ? 'Set date for selected photos' : 'Set country for selected photos';
            $('uc-value-input').innerHTML = kind === 'date'
                ? '<input type="date" class="form-control" id="uc-value" required>'
                : `<select class="form-control" id="uc-value">${[...countrySelect.options]
                    .filter(o => o.value && o.value !== '__NEW__').map(o => `<option>${esc(o.value)}</option>`).join('')}</select>`;
            dialog.addEventListener('close', () => resolve(dialog.returnValue === 'ok' ? $('uc-value').value : null), { once: true });
            dialog.showModal();
        });
    }

    // ---- Events ---------------------------------------------------------------------

    const photoFor = el => photos.find(p => p.key === Number(el.closest('[data-key]').dataset.key));

    grid.addEventListener('click', e => {
        const el = e.target.closest('button');
        if (!el || !el.closest('[data-key]')) return;
        const photo = photoFor(el);
        if (photo.status === 'done' || photo.status === 'uploading') return;
        const d = el.dataset;
        if (d.keep !== undefined) {
            const f = photo.faces[Number(d.keep)];
            f.state = 'kept'; f.personId = f.suggestion.id;
        } else if (d.reject !== undefined) {
            photo.faces[Number(d.reject)].state = 'rejected';
        } else if (d.unassign !== undefined) {
            const f = photo.faces[Number(d.unassign)];
            f.state = f.suggestion && f.state === 'kept' ? 'rejected' : 'unknown'; f.personId = null;
        } else if (d.nameFace !== undefined) {
            const f = photo.faces[Number(d.nameFace)];
            pickPerson('Who is this?', id => { f.state = 'assigned'; f.personId = id; });
            return;
        } else if (d.addPerson !== undefined) {
            pickPerson('Add a person to this photo', id => photo.extra.add(id));
            return;
        } else if (d.extraRemove !== undefined) {
            photo.extra.delete(Number(d.extraRemove));
        } else {
            return;
        }
        render();
    });

    grid.addEventListener('change', e => {
        if (!e.target.closest('[data-key]')) return;
        const photo = photoFor(e.target);
        if (e.target.matches('[data-select]')) photo.selected = e.target.checked;
        else if (e.target.matches('[data-date]')) { photo.date = e.target.value; photo.dateEdited = true; }
        else if (e.target.matches('[data-country]')) photo.country = e.target.value;
        render();
    });

    $('uc-browse').addEventListener('click', () => fileInput.click());
    $('uc-add-more').addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => { addFiles([...fileInput.files]); fileInput.value = ''; });

    const drop = $('uc-drop');
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
    drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('dragover'); addFiles([...e.dataTransfer.files]); });
    // Dropping onto the grid works too once photos are showing
    document.addEventListener('dragover', e => { if (photos.length) e.preventDefault(); });
    document.addEventListener('drop', e => { if (photos.length && !drop.contains(e.target)) { e.preventDefault(); addFiles([...e.dataTransfer.files]); } });

    countrySelect.addEventListener('change', () => {
        if (countrySelect.value === '__NEW__') {
            const name = (prompt('New country') || '').trim();
            if (name) {
                const opt = new Option(name, name);
                countrySelect.add(opt, countrySelect.options[countrySelect.options.length - 1]);
                countrySelect.value = name;
            } else {
                countrySelect.value = '';
            }
        }
        render();
    });

    document.querySelectorAll('[data-date-mode]').forEach(btn => btn.addEventListener('click', () => {
        batch.dateMode = btn.dataset.dateMode;
        document.querySelectorAll('[data-date-mode]').forEach(b => b.classList.toggle('active', b === btn));
        $('uc-batch-date').hidden = batch.dateMode !== 'same';
        render();
    }));
    $('uc-batch-date').addEventListener('change', e => { batch.date = e.target.value; render(); });

    $('uc-batch-add-person').addEventListener('click', () => pickPerson('Add a person to every photo', id => batch.people.add(id)));
    $('uc-batch-people').addEventListener('click', e => {
        const btn = e.target.closest('[data-batch-remove]');
        if (btn) { batch.people.delete(Number(btn.dataset.batchRemove)); render(); }
    });

    const keepAll = $('uc-keep-all');
    if (keepAll) keepAll.addEventListener('click', () => {
        photos.forEach(p => p.faces.forEach(f => {
            if (f.state === 'suggested' && !f.suggestion.unsure) { f.state = 'kept'; f.personId = f.suggestion.id; }
        }));
        render();
    });

    $('uc-bulk').addEventListener('click', async e => {
        const action = e.target.closest('[data-bulk]')?.dataset.bulk;
        const selected = photos.filter(p => p.selected && p.status !== 'done' && p.status !== 'removed');
        if (!action) return;
        if (action === 'date') {
            const value = await askValue('date');
            if (value) selected.forEach(p => { p.date = value; p.dateEdited = true; });
        } else if (action === 'country') {
            const value = await askValue('country');
            if (value) selected.forEach(p => { p.country = value; });
        } else if (action === 'person') {
            pickPerson(`Add a person to ${plural(selected.length, 'photo', 'photos')}`, id => selected.forEach(p => p.extra.add(id)));
            return;
        } else if (action === 'remove') {
            selected.forEach(p => { p.status = 'removed'; URL.revokeObjectURL(p.url); });
        } else if (action === 'clear') {
            selected.forEach(p => { p.selected = false; });
        }
        render();
    });

    $('uc-clear').addEventListener('click', () => {
        if (photos.some(p => p.status !== 'done' && p.status !== 'removed') && !confirm('Remove all photos from this upload?')) return;
        photos.forEach(p => URL.revokeObjectURL(p.url));
        photos = [];
        render();
    });

    // ---- Uploading -------------------------------------------------------------------

    $('uc-upload').addEventListener('click', async () => {
        const pending = photos.filter(p => p.status === 'ready' || p.status === 'failed');
        const noCountry = pending.filter(p => !countryFor(p));
        if (noCountry.length) {
            alert(`Choose a country for ${plural(noCountry.length, 'photo', 'photos')} (or one for the whole batch).`);
            return;
        }
        if (batch.dateMode === 'same' && !batch.date) {
            alert('Pick the date for all photos, or switch to "From each photo".');
            return;
        }
        const noDate = pending.filter(p => !dateFor(p)).length;
        if (noDate && !confirm(`${plural(noDate, 'photo has', 'photos have')} no date. Upload with today's date?`)) return;
        const unchecked = pending.reduce((n, p) => n + p.faces.filter(f => f.state === 'suggested').length, 0);
        if (unchecked && !confirm(`${plural(unchecked, 'suggestion is', 'suggestions are')} not kept and won't be tagged. Upload anyway?`)) return;

        for (const photo of pending) {
            photo.status = 'uploading';
            render();
            const body = new FormData();
            body.append('photo', photo.file);
            body.append('country', countryFor(photo));
            if (dateFor(photo)) body.append('date', dateFor(photo));
            tagsFor(photo).forEach(id => body.append('people', id));
            body.append('assignments', JSON.stringify(assignmentsFor(photo)));
            try {
                const res = await fetch('/api/upload/photo', { method: 'POST', body });
                const result = await res.json();
                if (result.success) { photo.status = 'done'; photo.savedId = result.id; photo.selected = false; }
                else { photo.status = 'failed'; photo.error = result.error; }
            } catch (e) {
                photo.status = 'failed'; photo.error = 'Connection error';
            }
            render();
        }
    });

    render();
})();
