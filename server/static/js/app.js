/* ── Navigation ───────────────────────────────────── */
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        const targetId = link.dataset.target;

        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');

        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.getElementById(targetId).classList.add('active');
    });
});

/* ── Speech-to-Text ──────────────────────────────── */
const speechForm   = document.getElementById('speech-form');
const dropZone     = document.getElementById('drop-zone');
const audioInput   = document.getElementById('audio-file');
const fileInfo     = document.getElementById('file-info');
const fileName     = document.getElementById('file-name');
const clearFileBtn = document.getElementById('clear-file');
const submitBtn    = document.getElementById('speech-submit');
const speechLoading = document.getElementById('speech-loading');
const speechResult  = document.getElementById('speech-result');
const speechError   = document.getElementById('speech-error');

// Click to browse
dropZone.addEventListener('click', () => audioInput.click());

// Drag & drop
dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        audioInput.files = e.dataTransfer.files;
        showFileInfo(e.dataTransfer.files[0]);
    }
});

// File input change
audioInput.addEventListener('change', () => {
    if (audioInput.files.length > 0) {
        showFileInfo(audioInput.files[0]);
    }
});

function showFileInfo(file) {
    const sizeMB = (file.size / 1024 / 1024).toFixed(1);
    fileName.textContent = `${file.name} (${sizeMB} MB)`;
    fileInfo.classList.remove('hidden');
    dropZone.style.display = 'none';
    submitBtn.disabled = false;
}

clearFileBtn.addEventListener('click', () => {
    audioInput.value = '';
    fileInfo.classList.add('hidden');
    dropZone.style.display = '';
    submitBtn.disabled = true;
    speechResult.classList.add('hidden');
    speechError.classList.add('hidden');
    curateResult.classList.add('hidden');
    curateError.classList.add('hidden');
});

// Curate elements
const curateLoading = document.getElementById('curate-loading');
const curateResult  = document.getElementById('curate-result');
const curateError   = document.getElementById('curate-error');

// Submit transcription, then auto-curate
speechForm.addEventListener('submit', async e => {
    e.preventDefault();
    if (!audioInput.files.length) return;

    speechResult.classList.add('hidden');
    speechError.classList.add('hidden');
    curateResult.classList.add('hidden');
    curateError.classList.add('hidden');
    speechLoading.classList.remove('hidden');
    submitBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', audioInput.files[0]);

    let transcribedText = '';

    try {
        const res = await fetch('/api/speech-to-text', {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Server error (${res.status})`);
        }

        const data = await res.json();
        transcribedText = data.text;
        document.getElementById('speech-text').textContent = data.text;
        document.getElementById('speech-duration').textContent = `Duration: ${data.duration_seconds}s`;
        document.getElementById('speech-lang').textContent = `Language: ${data.language}`;
        speechResult.classList.remove('hidden');
    } catch (err) {
        speechError.textContent = err.message;
        speechError.classList.remove('hidden');
        speechLoading.classList.add('hidden');
        submitBtn.disabled = false;
        return;
    }

    speechLoading.classList.add('hidden');

    // Auto-curate the transcribed text
    if (!transcribedText.trim()) {
        submitBtn.disabled = false;
        return;
    }

    curateLoading.classList.remove('hidden');

    try {
        const res = await fetch('/api/curate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: transcribedText }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Curation error (${res.status})`);
        }

        const data = await res.json();
        document.getElementById('curate-text').textContent = data.curated;
        curateResult.classList.remove('hidden');
    } catch (err) {
        curateError.textContent = `Curation failed: ${err.message}`;
        curateError.classList.remove('hidden');
    } finally {
        curateLoading.classList.add('hidden');
        submitBtn.disabled = false;
    }
});

/* ── Template Renderer ───────────────────────────── */
const renderForm    = document.getElementById('render-form');
const varContainer  = document.getElementById('variables-container');
const addVarBtn     = document.getElementById('add-variable');
const renderLoading = document.getElementById('render-loading');
const renderResult  = document.getElementById('render-result');
const renderError   = document.getElementById('render-error');

// Add variable row
addVarBtn.addEventListener('click', () => addVariableRow());

function addVariableRow() {
    const row = document.createElement('div');
    row.className = 'variable-row';
    row.innerHTML = `
        <input type="text" placeholder="Key" class="var-key">
        <input type="text" placeholder="Value" class="var-value">
        <button type="button" class="btn-icon remove-var" title="Remove">&times;</button>
    `;
    varContainer.appendChild(row);
}

// Remove variable row (event delegation)
varContainer.addEventListener('click', e => {
    const removeBtn = e.target.closest('.remove-var');
    if (!removeBtn) return;
    const row = removeBtn.closest('.variable-row');
    if (varContainer.children.length > 1) {
        row.remove();
    } else {
        // Keep the last row but clear it
        row.querySelector('.var-key').value = '';
        row.querySelector('.var-value').value = '';
    }
});

// Submit render
renderForm.addEventListener('submit', async e => {
    e.preventDefault();

    const text = document.getElementById('render-text').value.trim();
    if (!text) return;

    // Collect variables
    const variables = {};
    varContainer.querySelectorAll('.variable-row').forEach(row => {
        const key = row.querySelector('.var-key').value.trim();
        const val = row.querySelector('.var-value').value;
        if (key) variables[key] = val;
    });

    renderResult.classList.add('hidden');
    renderError.classList.add('hidden');
    renderLoading.classList.remove('hidden');

    try {
        const res = await fetch('/api/render-html/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, variables }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Server error (${res.status})`);
        }

        const html = await res.text();
        const iframe = document.getElementById('render-preview');
        iframe.srcdoc = html;
        renderResult.classList.remove('hidden');
    } catch (err) {
        renderError.textContent = err.message;
        renderError.classList.remove('hidden');
    } finally {
        renderLoading.classList.add('hidden');
    }
});
