/* ── Weather Widget ──────────────────────────────── */
const wxIcaoLabel   = document.getElementById('weather-icao-label');
const wxFetchBtn    = document.getElementById('weather-fetch');
const wxLoading     = document.getElementById('weather-loading');
const wxError       = document.getElementById('weather-error');
const wxResults     = document.getElementById('weather-results');

function wxVal(v) {
    if (v === null || v === undefined || v === '') return '—';
    return v;
}

function wxWind(w) {
    if (!w) return '—';
    const dir = wxVal(w.direction_deg || w.wind_dir_deg);
    const spd = wxVal(w.speed_kt || w.wind_speed_kt);
    const gust = w.gust_kt || w.wind_gust_kt;
    let s = `${dir}° / ${spd} kt`;
    if (gust) s += ` G${gust}`;
    return s;
}

function wxVis(m) {
    if (!m) return '—';
    if (m.visibility_sm) return `${m.visibility_sm} SM`;
    if (m.visibility) {
        const v = m.visibility;
        if (v.miles) return `${v.miles} mi`;
        if (v.meters) return `${v.meters} m`;
        if (v.value) return `${v.value} ${v.unit || ''}`;
    }
    return '—';
}

function wxClouds(clouds) {
    if (!clouds || clouds.length === 0) return '—';
    return clouds.map(c => {
        const cover = c.cover || c.type || c.code || '';
        const base = c.base_ft || c.altitude_ft || '';
        return base ? `${cover} ${base} ft` : cover;
    }).join(', ');
}

function wxFlightCat(m) {
    const cat = (m.flight_category || m.flight_rules || '').toUpperCase();
    if (!cat) return '';
    const cls = {
        'VFR': 'flight-cat-vfr',
        'MVFR': 'flight-cat-mvfr',
        'IFR': 'flight-cat-ifr',
        'LIFR': 'flight-cat-lifr',
    }[cat] || '';
    return `<span class="flight-cat ${cls}">${cat}</span>`;
}

function wxRenderMetar(metar) {
    if (!metar || metar.error) {
        return `<div class="wx-source-error">${metar ? metar.error : 'Nu sunt date METAR'}</div>`;
    }
    return `
        <div class="wx-section">
            <div class="wx-section-title">METAR ${wxFlightCat(metar)}</div>
            ${metar.raw ? `<div class="wx-raw">${metar.raw}</div>` : ''}
            <div class="wx-fields">
                <div class="wx-field">
                    <span class="wx-field-label">V&acirc;nt</span>
                    <span class="wx-field-value">${wxWind(metar.wind || metar)}</span>
                </div>
                <div class="wx-field">
                    <span class="wx-field-label">Vizibilitate</span>
                    <span class="wx-field-value">${wxVis(metar)}</span>
                </div>
                <div class="wx-field">
                    <span class="wx-field-label">Temperatur&#259;</span>
                    <span class="wx-field-value">${wxVal(metar.temperature_c)}°C</span>
                </div>
                <div class="wx-field">
                    <span class="wx-field-label">Punct de rou&#259;</span>
                    <span class="wx-field-value">${wxVal(metar.dewpoint_c)}°C</span>
                </div>
                <div class="wx-field">
                    <span class="wx-field-label">QNH</span>
                    <span class="wx-field-value">${wxVal(metar.altimeter_hpa || (metar.altimeter && metar.altimeter.hpa) || (metar.altimeter && metar.altimeter.value))} hPa</span>
                </div>
                <div class="wx-field">
                    <span class="wx-field-label">Nori</span>
                    <span class="wx-field-value">${wxClouds(metar.clouds)}</span>
                </div>
            </div>
        </div>`;
}

function wxFormatTime(t) {
    if (!t) return '—';
    if (typeof t === 'number') {
        const d = new Date(t * 1000);
        return d.toISOString().slice(5, 16).replace('T', ' ') + 'Z';
    }
    if (typeof t === 'string' && t.length > 16) {
        return t.slice(5, 16).replace('T', ' ') + 'Z';
    }
    return t;
}

function wxRenderTaf(taf) {
    if (!taf || taf.error) {
        return `<div class="wx-source-error">${taf ? taf.error : 'Nu sunt date TAF'}</div>`;
    }
    const validFrom = wxFormatTime(taf.valid_from || taf.start_time);
    const validTo = wxFormatTime(taf.valid_to || taf.end_time);
    const forecasts = taf.forecasts || [];

    let forecastsHtml = '';
    if (forecasts.length > 0) {
        forecastsHtml = '<div class="wx-forecasts">' + forecasts.map(f => {
            const from = wxFormatTime(f.from || f.start_time);
            const to = wxFormatTime(f.to || f.end_time);
            const change = f.change_indicator ? `<span class="wx-forecast-change">${f.change_indicator}</span>` : '';
            const wind = wxWind(f.wind || f);
            const vis = f.visibility_sm || f.visibility_miles || (f.visibility && (f.visibility.value || f.visibility.miles)) || '';
            const wx = (f.wx_string || (f.wx_codes && f.wx_codes.length > 0 && f.wx_codes.join(' '))) || '';
            let details = `V&acirc;nt: ${wind}`;
            if (vis) details += ` | Vizib: ${vis}`;
            if (wx) details += ` | ${wx}`;
            return `<div class="wx-forecast-row">
                ${change}
                <span class="wx-forecast-time">${from} → ${to}</span>
                <span class="wx-forecast-detail">${details}</span>
            </div>`;
        }).join('') + '</div>';
    }

    return `
        <div class="wx-section">
            <div class="wx-section-title">TAF</div>
            ${taf.raw ? `<div class="wx-raw">${taf.raw}</div>` : ''}
            <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.4rem;">
                Valabil: ${validFrom} → ${validTo}
            </div>
            ${forecastsHtml}
        </div>`;
}

function wxRenderSource(src) {
    if (src.error && !src.metar && !src.taf) {
        return `
            <div class="wx-source-card">
                <div class="wx-source-header" onclick="this.nextElementSibling.classList.toggle('hidden'); this.querySelector('.wx-source-toggle').classList.toggle('open')">
                    <span class="wx-source-name">${src.source}</span>
                    <span class="wx-source-toggle">&#9660;</span>
                </div>
                <div class="wx-source-error">${src.error}</div>
            </div>`;
    }

    const stationHtml = src.station ? `
        <div class="wx-station">
            ${src.station.name || src.station.icao || ''} &mdash;
            ${src.station.country || ''} ${src.station.city || ''}
            ${src.station.elevation_m != null ? ` | Elev: ${src.station.elevation_m} m` : ''}
        </div>` : '';

    return `
        <div class="wx-source-card">
            <div class="wx-source-header" onclick="this.nextElementSibling.classList.toggle('hidden'); this.querySelector('.wx-source-toggle').classList.toggle('open')">
                <span class="wx-source-name">${src.source}</span>
                <span class="wx-source-toggle open">&#9660;</span>
            </div>
            <div class="wx-source-body">
                ${stationHtml}
                ${wxRenderMetar(src.metar)}
                ${wxRenderTaf(src.taf)}
            </div>
        </div>`;
}

async function fetchWeather() {
    const icao = document.getElementById('airport-select').value;
    wxIcaoLabel.textContent = icao;

    wxError.classList.add('hidden');
    wxResults.classList.add('hidden');
    wxLoading.classList.remove('hidden');
    wxFetchBtn.disabled = true;

    try {
        const res = await fetch(`/api/weather/${icao}`);
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Eroare server (${res.status})`);
        }
        const data = await res.json();

        wxResults.innerHTML = data.sources.map(wxRenderSource).join('');
        wxResults.classList.remove('hidden');
    } catch (err) {
        wxError.textContent = `Eroare meteo: ${err.message}`;
        wxError.classList.remove('hidden');
    } finally {
        wxLoading.classList.add('hidden');
        wxFetchBtn.disabled = false;
    }
}

wxFetchBtn.addEventListener('click', fetchWeather);

// Auto-fetch on page load
fetchWeather();

/* ── Airport / Operator selection ─────────────────── */
const airportSelect  = document.getElementById('airport-select');
const operatorSelect = document.getElementById('operator-select');

let airportsData = null;

fetch('/api/airports')
    .then(res => res.json())
    .then(data => { airportsData = data; })
    .catch(() => {});

airportSelect.addEventListener('change', () => {
    // Update operators dropdown
    if (airportsData) {
        const airport = airportsData[airportSelect.value];
        if (airport) {
            operatorSelect.innerHTML = '';
            airport.operators.forEach(op => {
                const option = document.createElement('option');
                option.value = op.code;
                option.textContent = `${op.name} (${op.code})`;
                if (op.code === airport.default_operator) option.selected = true;
                operatorSelect.appendChild(option);
            });
        }
    }
    // Auto-refresh weather for the newly selected airport
    fetchWeather();
});

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
    snowtamResult.classList.add('hidden');
    snowtamError.classList.add('hidden');
});

// Curate elements
const curateLoading = document.getElementById('curate-loading');
const curateResult  = document.getElementById('curate-result');
const curateError   = document.getElementById('curate-error');

// SNOWTAM elements
const snowtamLoading = document.getElementById('snowtam-loading');
const snowtamResult  = document.getElementById('snowtam-result');
const snowtamError   = document.getElementById('snowtam-error');

// Submit transcription, then auto-curate
speechForm.addEventListener('submit', async e => {
    e.preventDefault();
    if (!audioInput.files.length) return;

    speechResult.classList.add('hidden');
    speechError.classList.add('hidden');
    curateResult.classList.add('hidden');
    curateError.classList.add('hidden');
    snowtamResult.classList.add('hidden');
    snowtamError.classList.add('hidden');
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
            throw new Error(err.detail || `Eroare server (${res.status})`);
        }

        const data = await res.json();
        transcribedText = data.text;
        document.getElementById('speech-text').textContent = data.text;
        document.getElementById('speech-duration').textContent = `Durată: ${data.duration_seconds}s`;
        document.getElementById('speech-lang').textContent = `Limbă: ${data.language}`;
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

    let curatedText = '';

    try {
        const res = await fetch('/api/curate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: transcribedText }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Eroare curare (${res.status})`);
        }

        const data = await res.json();
        curatedText = data.curated;
        document.getElementById('curate-text').textContent = data.curated;
        curateResult.classList.remove('hidden');
    } catch (err) {
        curateError.textContent = `Curarea a eșuat: ${err.message}`;
        curateError.classList.remove('hidden');
        curateLoading.classList.add('hidden');
        submitBtn.disabled = false;
        return;
    }

    curateLoading.classList.add('hidden');

    // Auto-extract SNOWTAM from curated text
    if (!curatedText.trim()) {
        submitBtn.disabled = false;
        return;
    }

    snowtamLoading.classList.remove('hidden');

    try {
        const res = await fetch('/api/snowtam', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: curatedText,
                speech_text: transcribedText,
                curated_text: curatedText,
                airport_code: airportSelect.value,
                operator_code: operatorSelect.value,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Eroare SNOWTAM (${res.status})`);
        }

        const data = await res.json();
        lastSnowtamHtml = data.html;
        const iframe = document.getElementById('snowtam-preview');
        iframe.srcdoc = data.html;
        snowtamResult.classList.remove('hidden');
    } catch (err) {
        snowtamError.textContent = `Extragerea SNOWTAM a eșuat: ${err.message}`;
        snowtamError.classList.remove('hidden');
    } finally {
        snowtamLoading.classList.add('hidden');
        submitBtn.disabled = false;
    }
});

/* ── SNOWTAM Export & Email ──────────────────────── */
let lastSnowtamHtml = '';
const emailStatus = document.getElementById('email-status');

document.getElementById('export-pdf').addEventListener('click', async () => {
    if (!lastSnowtamHtml) return;
    try {
        const res = await fetch('/api/snowtam/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ html: lastSnowtamHtml }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Eroare PDF (${res.status})`);
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'SNOWTAM_LROD.pdf';
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        snowtamError.textContent = `Export PDF eșuat: ${err.message}`;
        snowtamError.classList.remove('hidden');
    }
});

document.getElementById('send-email').addEventListener('click', async () => {
    if (!lastSnowtamHtml) return;
    const emailTo = document.getElementById('email-to').value.trim();
    if (!emailTo) {
        emailStatus.textContent = 'Introduceți adresa email a destinatarului.';
        emailStatus.className = 'error';
        emailStatus.classList.remove('hidden');
        return;
    }

    const sendBtn = document.getElementById('send-email');
    sendBtn.disabled = true;
    sendBtn.textContent = 'Se trimite...';
    emailStatus.classList.add('hidden');

    try {
        const res = await fetch('/api/snowtam/send-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to: emailTo, html: lastSnowtamHtml }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Eroare trimitere (${res.status})`);
        }
        emailStatus.textContent = `Email trimis cu succes către ${emailTo}!`;
        emailStatus.className = 'success';
        emailStatus.classList.remove('hidden');
    } catch (err) {
        emailStatus.textContent = `Trimitere eșuată: ${err.message}`;
        emailStatus.className = 'error';
        emailStatus.classList.remove('hidden');
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '&#9993; Trimite pe Email';
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
        <input type="text" placeholder="Cheie" class="var-key">
        <input type="text" placeholder="Valoare" class="var-value">
        <button type="button" class="btn-icon remove-var" title="Șterge">&times;</button>
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
            throw new Error(err.detail || `Eroare server (${res.status})`);
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
