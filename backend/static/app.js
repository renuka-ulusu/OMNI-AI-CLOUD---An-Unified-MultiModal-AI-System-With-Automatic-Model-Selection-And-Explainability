const configElement = document.getElementById('omniai-config');
const config = configElement ? JSON.parse(configElement.textContent) : { languageNames: {}, translationCodes: [] };

const form = document.getElementById('analysisForm');
const modeFile = document.getElementById('modeFile');
const modeText = document.getElementById('modeText');
const fileInputSection = document.getElementById('fileInputSection');
const textInputSection = document.getElementById('textInputSection');
const fileDropZone = document.getElementById('fileDropZone');
const fileMeta = document.getElementById('fileMeta');
const fileInput = document.getElementById('fileInput');
const textInput = document.getElementById('textInput');
const textMetrics = document.getElementById('textMetrics');
const sampleTextBtn = document.getElementById('sampleTextBtn');
const clearTextBtn = document.getElementById('clearTextBtn');
const resetAllBtn = document.getElementById('resetAllBtn');
const sourceLanguage = document.getElementById('sourceLanguage');
const targetLanguage = document.getElementById('targetLanguage');
const autoDetectSource = document.getElementById('autoDetectSource');
const statusPanel = document.getElementById('statusPanel');
const resultsContainer = document.getElementById('resultsContainer');
const overviewCards = document.getElementById('overviewCards');
const selectedModels = document.getElementById('selectedModels');
const analysisResults = document.getElementById('analysisResults');
const explanation = document.getElementById('explanation');
const analyzeBtn = document.getElementById('analyzeBtn');
const progressSection = document.getElementById('analysisProgress');
const progressBar = document.getElementById('progressBar');
const progressPercent = document.getElementById('progressPercent');
const progressStages = document.getElementById('progressStages');
const loadingOverlay = document.getElementById('loadingOverlay');
const overlayMessage = document.getElementById('overlayMessage');
const liveClock = document.getElementById('liveClock');
const resultSearch = document.getElementById('resultSearch');
const expandAllBtn = document.getElementById('expandAllBtn');
const collapseAllBtn = document.getElementById('collapseAllBtn');
const copySummaryBtn = document.getElementById('copySummaryBtn');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');
const recentRuns = document.getElementById('recentRuns');
const toastContainer = document.getElementById('toastContainer');

const ANALYSIS_STAGES = [
  'Validating input',
  'Selecting AI models',
  'Running model inference',
  'Compiling insights',
  'Rendering output'
];

let progressTimer = null;
let progressValue = 0;
let activeFilter = 'all';
let latestResult = null;
const RECENT_RUNS_KEY = 'omniai_recent_runs_v1';
const TEXT_DRAFT_KEY = 'omniai_text_draft_v1';

function setStatus(message, type = 'info') {
  statusPanel.className = `alert alert-${type}`;
  statusPanel.textContent = message;
  statusPanel.classList.remove('d-none');
}

function showToast(message, type = 'info') {
  const toastId = `toast-${Date.now()}`;
  const typeClass = type === 'success' ? 'text-bg-success' : type === 'danger' ? 'text-bg-danger' : 'text-bg-primary';
  const toast = document.createElement('div');
  toast.id = toastId;
  toast.className = `toast align-items-center ${typeClass} border-0`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  toastContainer.appendChild(toast);
  if (window.bootstrap && window.bootstrap.Toast) {
    const bsToast = new window.bootstrap.Toast(toast, { delay: 2200 });
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
  } else {
    setTimeout(() => toast.remove(), 2400);
  }
}

function clearStatus() {
  statusPanel.classList.add('d-none');
  statusPanel.textContent = '';
}

function setAnalyzingState(isAnalyzing) {
  const btnText = analyzeBtn.querySelector('.btn-text');
  const btnSpinner = analyzeBtn.querySelector('.btn-spinner');

  analyzeBtn.classList.toggle('loading', isAnalyzing);
  analyzeBtn.disabled = isAnalyzing;

  if (isAnalyzing) {
    btnText.textContent = 'Analyzing...';
    btnSpinner.classList.remove('d-none');
    loadingOverlay.classList.remove('d-none');
  } else {
    btnText.textContent = 'Analyze';
    btnSpinner.classList.add('d-none');
    loadingOverlay.classList.add('d-none');
  }
}

function initProgressSection() {
  progressSection.classList.remove('d-none');
  progressBar.style.width = '0%';
  progressPercent.textContent = '0%';
  progressValue = 0;
  progressStages.innerHTML = ANALYSIS_STAGES
    .map((stage, index) => `<span class="stage-chip" data-stage="${index}">${stage}</span>`)
    .join('');
  overlayMessage.textContent = ANALYSIS_STAGES[0];
}

function advanceProgress(target = 85) {
  if (progressTimer) {
    clearInterval(progressTimer);
  }

  progressTimer = setInterval(() => {
    const increment = progressValue < 45 ? 3 : (progressValue < 70 ? 2 : 1);
    progressValue = Math.min(target, progressValue + increment);
    progressBar.style.width = `${progressValue}%`;
    progressPercent.textContent = `${progressValue}%`;

    const stageIndex = Math.min(
      ANALYSIS_STAGES.length - 1,
      Math.floor((progressValue / 100) * ANALYSIS_STAGES.length)
    );
    const chips = [...progressStages.querySelectorAll('.stage-chip')];
    chips.forEach((chip, idx) => {
      chip.classList.toggle('active', idx === stageIndex);
      chip.classList.toggle('done', idx < stageIndex);
    });
    overlayMessage.textContent = ANALYSIS_STAGES[stageIndex];

    if (progressValue >= target) {
      clearInterval(progressTimer);
      progressTimer = null;
    }
  }, 280);
}

function completeProgress() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }

  progressValue = 100;
  progressBar.style.width = '100%';
  progressPercent.textContent = '100%';
  overlayMessage.textContent = 'Finalizing results...';

  const chips = [...progressStages.querySelectorAll('.stage-chip')];
  chips.forEach((chip) => {
    chip.classList.remove('active');
    chip.classList.add('done');
  });
}

function resetProgress() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  progressSection.classList.add('d-none');
  progressStages.innerHTML = '';
}

function toggleMode() {
  const isFileMode = modeFile.checked;
  fileInputSection.classList.toggle('d-none', !isFileMode);
  textInputSection.classList.toggle('d-none', isFileMode);
}

function updateFileMeta() {
  const file = fileInput.files?.[0];
  if (!file) {
    fileMeta.textContent = 'No file selected';
    return;
  }
  const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
  fileMeta.textContent = `${file.name} • ${sizeMb} MB`;
}

function updateTextMetrics() {
  const text = textInput.value || '';
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  textMetrics.textContent = `${text.length} characters • ${words} words`;
}

function saveDraft() {
  localStorage.setItem(TEXT_DRAFT_KEY, textInput.value || '');
}

function loadDraft() {
  const draft = localStorage.getItem(TEXT_DRAFT_KEY);
  if (draft) {
    textInput.value = draft;
    updateTextMetrics();
  }
}

function languageDisplay(code) {
  if (!code) return 'N/A';
  return config.languageNames[code.toLowerCase()] || code.toUpperCase();
}

function fillLanguageSelects() {
  sourceLanguage.innerHTML = '';
  targetLanguage.innerHTML = '';

  const autoOption = document.createElement('option');
  autoOption.value = 'auto';
  autoOption.textContent = 'Auto Detect';
  sourceLanguage.appendChild(autoOption);

  config.translationCodes.forEach((code) => {
    const sourceOpt = document.createElement('option');
    sourceOpt.value = code;
    sourceOpt.textContent = languageDisplay(code);
    sourceLanguage.appendChild(sourceOpt);

    const targetOpt = document.createElement('option');
    targetOpt.value = code;
    targetOpt.textContent = languageDisplay(code);
    targetLanguage.appendChild(targetOpt);
  });

  sourceLanguage.value = 'auto';
  targetLanguage.value = config.translationCodes.includes('en') ? 'en' : (config.translationCodes[0] || 'en');
  sourceLanguage.disabled = autoDetectSource.checked;
}

function renderOverview(metadata = {}) {
  overviewCards.innerHTML = '';
  const cards = [
    { label: 'Input Type', value: (metadata.input_type || 'N/A').toUpperCase() },
    { label: 'File Extension', value: (metadata.file_extension || 'N/A').toUpperCase() },
    { label: 'Language', value: languageDisplay(metadata.language || 'unknown') }
  ];

  cards.forEach((card) => {
    const col = document.createElement('div');
    col.className = 'col-md-4 fade-in';
    col.innerHTML = `
      <div class="metric-card">
        <div class="label">${card.label}</div>
        <div class="value">${card.value}</div>
      </div>
    `;
    overviewCards.appendChild(col);
  });
}

function renderModels(models = []) {
  selectedModels.innerHTML = '';
  if (!models.length) {
    selectedModels.textContent = 'No models selected.';
    return;
  }
  models.forEach((model) => {
    const chip = document.createElement('span');
    chip.className = 'badge-chip fade-in';
    chip.textContent = model;
    selectedModels.appendChild(chip);
  });
}

function createBlock(title, bodyHtml, category = 'text') {
  const block = document.createElement('div');
  block.className = `result-block ${category}`;
  block.setAttribute('data-category', category);
  block.setAttribute('data-search', `${title} ${bodyHtml.replace(/<[^>]*>/g, ' ')}`.toLowerCase());
  block.innerHTML = `
    <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
      <div class="result-title mb-0">${title}</div>
      <div class="d-flex gap-2">
        <button class="result-toggle" type="button">Collapse</button>
        <button class="copy-btn" type="button" data-copy="${title}">Copy</button>
      </div>
    </div>
    <div class="result-body">${bodyHtml}</div>`;
  return block;
}

function renderResults(results = {}) {
  analysisResults.innerHTML = '';

  if (results.image_classification) {
    const ic = results.image_classification;
    analysisResults.appendChild(createBlock(
      'Image Classification',
      `<div>Label: <strong>${ic.label || 'N/A'}</strong></div><div>Confidence: ${Number(ic.confidence || 0).toFixed(2)}%</div>`,
      'vision'
    ));
  }

  if (results.object_detection) {
    const od = results.object_detection;
    const detections = (od.detections || []).map((det, index) => `
      <li>${index + 1}. ${det.label} — ${Number(det.confidence || 0).toFixed(2)}% — bbox: ${JSON.stringify(det.bbox)}</li>
    `).join('');
    analysisResults.appendChild(createBlock(
      'Object Detection',
      `<div>Total Objects: ${od.object_count || 0}</div><ul>${detections}</ul>`,
      'vision'
    ));
  }

  if (results.ocr) {
    analysisResults.appendChild(createBlock(
      'OCR Extracted Text',
      `<pre>${(results.ocr.text || '').replace(/[<>&]/g, (ch) => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[ch]))}</pre>`,
      'document'
    ));
  }

  if (results.translation) {
    const tr = results.translation;
    analysisResults.appendChild(createBlock(
      'Translation',
      `<div>${languageDisplay(tr.source_language)} → ${languageDisplay(tr.target_language)}</div><pre>${(tr.translated_text || '').replace(/[<>&]/g, (ch) => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[ch]))}</pre>`,
      'text'
    ));
  }

  if (results.text_analytics) {
    const ta = results.text_analytics;
    const entities = (ta.entities || []).map((entity) => `<li>${entity.text} → ${entity.label}</li>`).join('');
    analysisResults.appendChild(createBlock(
      'Sentiment & Entities',
      `<div>Sentiment: <strong>${ta.sentiment || 'N/A'}</strong></div><div>Confidence: ${ta.sentiment_confidence || 0}%</div><ul>${entities}</ul>`,
      'text'
    ));
  }

  if (results.caption) {
    analysisResults.appendChild(createBlock(
      'Image Caption',
      `<pre>${(results.caption.caption || '').replace(/[<>&]/g, (ch) => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[ch]))}</pre>`,
      'vision'
    ));
  }

  if (results.document) {
    const doc = results.document;
    const safeSummary = (doc.summary || 'Summary unavailable for this document.').replace(/[<>&]/g, (ch) => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[ch]));
    let docHtml = `<div>Document Type: <strong>${doc.type || 'N/A'}</strong></div>`;
    docHtml += `<div>Extraction Method: <strong>${doc.extraction_method || 'N/A'}</strong></div>`;
    docHtml += `<div class="mt-2">Summary:</div><pre>${safeSummary}</pre>`;
    if (doc.extracted_text) {
      docHtml += `<div class="mt-2">Extracted Text:</div><pre>${doc.extracted_text.replace(/[<>&]/g, (ch) => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[ch]))}</pre>`;
    }
    analysisResults.appendChild(createBlock('Document Analysis', docHtml, 'document'));
  }

  applyResultFilter(activeFilter);
}

function applyResultFilter(filterValue = 'all') {
  activeFilter = filterValue;
  const blocks = [...analysisResults.querySelectorAll('.result-block')];
  blocks.forEach((block) => {
    const category = block.getAttribute('data-category');
    const visible = filterValue === 'all' || filterValue === category;
    block.classList.toggle('d-none', !visible);
  });
}

function applySearchFilter() {
  const query = (resultSearch.value || '').trim().toLowerCase();
  const blocks = [...analysisResults.querySelectorAll('.result-block')];
  blocks.forEach((block) => {
    const text = block.getAttribute('data-search') || '';
    const visibleByFilter = activeFilter === 'all' || block.getAttribute('data-category') === activeFilter;
    const visibleBySearch = !query || text.includes(query);
    block.classList.toggle('d-none', !(visibleByFilter && visibleBySearch));
  });
}

function setAllBlocksCollapsed(collapsed) {
  analysisResults.querySelectorAll('.result-block').forEach((block) => {
    block.classList.toggle('collapsed', collapsed);
    const toggleBtn = block.querySelector('.result-toggle');
    if (toggleBtn) {
      toggleBtn.textContent = collapsed ? 'Expand' : 'Collapse';
    }
  });
}

function setupCopyHandlers() {
  analysisResults.querySelectorAll('.copy-btn').forEach((button) => {
    button.addEventListener('click', async () => {
      const block = button.closest('.result-block');
      const text = block ? block.innerText.replace('Copy', '').trim() : '';
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        const original = button.textContent;
        button.textContent = 'Copied';
        setTimeout(() => { button.textContent = original; }, 900);
        showToast('Result block copied', 'success');
      } catch (_error) {
        setStatus('Clipboard access denied by browser.', 'warning');
      }
    });
  });

  analysisResults.querySelectorAll('.result-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const block = button.closest('.result-block');
      if (!block) return;
      block.classList.toggle('collapsed');
      button.textContent = block.classList.contains('collapsed') ? 'Expand' : 'Collapse';
    });
  });
}

function updateRecentRunsUI() {
  const runs = JSON.parse(localStorage.getItem(RECENT_RUNS_KEY) || '[]');
  if (!runs.length) {
    recentRuns.innerHTML = '<div class="text-muted">No recent analyses yet.</div>';
    return;
  }

  recentRuns.innerHTML = runs
    .map((run) => `
      <div class="recent-item">
        <div><strong>${run.inputType}</strong> • ${run.models} models</div>
        <div class="recent-meta">${run.time} • ${run.language}</div>
      </div>
    `)
    .join('');
}

function pushRecentRun(data) {
  const metadata = data.metadata || {};
  const models = data.selected_modules || [];
  const runs = JSON.parse(localStorage.getItem(RECENT_RUNS_KEY) || '[]');
  runs.unshift({
    inputType: (metadata.input_type || 'unknown').toUpperCase(),
    models: models.length,
    language: languageDisplay(metadata.language || 'unknown'),
    time: new Date().toLocaleString(),
  });
  localStorage.setItem(RECENT_RUNS_KEY, JSON.stringify(runs.slice(0, 6)));
  updateRecentRunsUI();
}

function downloadLatestResult() {
  if (!latestResult) {
    showToast('No analysis result available yet', 'danger');
    return;
  }
  const blob = new Blob([JSON.stringify(latestResult, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `omniai-result-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast('Result JSON downloaded', 'success');
}

async function copyExplainability() {
  const text = explanation.innerText || '';
  if (!text.trim()) {
    showToast('No explainability text to copy', 'danger');
    return;
  }
  await navigator.clipboard.writeText(text);
  showToast('Explainability copied', 'success');
}

function resetAll() {
  fileInput.value = '';
  updateFileMeta();
  textInput.value = '';
  updateTextMetrics();
  saveDraft();
  clearStatus();
  resultsContainer.classList.add('d-none');
  latestResult = null;
  showToast('UI reset complete', 'success');
}

function refreshClock() {
  liveClock.textContent = new Date().toLocaleTimeString();
}

async function submitFile() {
  const file = fileInput.files?.[0];
  if (!file) {
    setStatus('Please select a file first.', 'danger');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  setStatus('Analyzing file...', 'info');
  const response = await fetch('/api/analyze/file', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'File analysis failed');
  }

  return data;
}

async function submitText() {
  const text = textInput.value.trim();
  if (!text) {
    setStatus('Please enter text first.', 'danger');
    return;
  }

  const formData = new FormData();
  formData.append('text', text);
  formData.append('source_language', sourceLanguage.value);
  formData.append('target_language', targetLanguage.value);
  formData.append('auto_detect_source', String(autoDetectSource.checked));

  setStatus('Analyzing text...', 'info');
  const response = await fetch('/api/analyze/text', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Text analysis failed');
  }

  return data;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearStatus();
  resultsContainer.classList.add('d-none');
  initProgressSection();
  setAnalyzingState(true);
  advanceProgress(86);

  try {
    const data = modeFile.checked ? await submitFile() : await submitText();
    if (!data) {
      setAnalyzingState(false);
      resetProgress();
      return;
    }

    completeProgress();

    renderOverview(data.metadata || {});
    renderModels(data.selected_modules || []);
    renderResults(data.results || {});
    explanation.innerHTML = (data.explanation || 'No explanation generated.').replace(/\n/g, '<br>');
    setupCopyHandlers();
    latestResult = data;
    pushRecentRun(data);
    applySearchFilter();

    resultsContainer.classList.remove('d-none');
    resultsContainer.classList.add('fade-in');
    setTimeout(() => resultsContainer.classList.remove('fade-in'), 550);
    setStatus('Analysis completed successfully.', 'success');
    setTimeout(() => {
      setAnalyzingState(false);
      resetProgress();
    }, 400);
  } catch (error) {
    setAnalyzingState(false);
    resetProgress();
    setStatus(error.message || 'Unexpected error occurred.', 'danger');
  }
});

modeFile.addEventListener('change', toggleMode);
modeText.addEventListener('change', toggleMode);
autoDetectSource.addEventListener('change', () => {
  sourceLanguage.disabled = autoDetectSource.checked;
  if (autoDetectSource.checked) {
    sourceLanguage.value = 'auto';
  }
});

document.querySelectorAll('.result-filter').forEach((radio) => {
  radio.addEventListener('change', () => {
    if (radio.checked) {
      applyResultFilter(radio.value);
      applySearchFilter();
    }
  });
});

resultSearch.addEventListener('input', applySearchFilter);
expandAllBtn.addEventListener('click', () => setAllBlocksCollapsed(false));
collapseAllBtn.addEventListener('click', () => setAllBlocksCollapsed(true));
downloadJsonBtn.addEventListener('click', downloadLatestResult);
copySummaryBtn.addEventListener('click', async () => {
  try {
    await copyExplainability();
  } catch (_error) {
    showToast('Clipboard not available', 'danger');
  }
});

sampleTextBtn.addEventListener('click', () => {
  textInput.value = 'OmniAI Cloud is a unified multimodal AI platform for document intelligence, image understanding, OCR, translation, and explainable analytics.';
  updateTextMetrics();
  saveDraft();
  showToast('Sample text added', 'success');
});

clearTextBtn.addEventListener('click', () => {
  textInput.value = '';
  updateTextMetrics();
  saveDraft();
});

resetAllBtn.addEventListener('click', resetAll);
textInput.addEventListener('input', () => {
  updateTextMetrics();
  saveDraft();
});

textInput.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault();
    form.requestSubmit();
  }
});

fileInput.addEventListener('change', updateFileMeta);

['dragenter', 'dragover'].forEach((eventName) => {
  fileDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    fileDropZone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach((eventName) => {
  fileDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    fileDropZone.classList.remove('dragover');
  });
});

fileDropZone.addEventListener('drop', (event) => {
  const files = event.dataTransfer?.files;
  if (files && files.length) {
    fileInput.files = files;
    updateFileMeta();
    showToast('File selected from drag-and-drop', 'success');
  }
});

analyzeBtn.addEventListener('click', (event) => {
  const ripple = document.createElement('span');
  const rect = analyzeBtn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  ripple.style.position = 'absolute';
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
  ripple.style.background = 'rgba(255,255,255,0.25)';
  ripple.style.borderRadius = '50%';
  ripple.style.transform = 'scale(0)';
  ripple.style.transition = 'transform 0.5s ease, opacity 0.5s ease';
  analyzeBtn.appendChild(ripple);
  requestAnimationFrame(() => {
    ripple.style.transform = 'scale(2.2)';
    ripple.style.opacity = '0';
  });
  setTimeout(() => ripple.remove(), 520);
});

fillLanguageSelects();
toggleMode();
loadDraft();
updateTextMetrics();
updateFileMeta();
updateRecentRunsUI();
refreshClock();
setInterval(refreshClock, 1000);
