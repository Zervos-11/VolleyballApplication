'use strict';

const API = document.body.dataset.api || '/api/u5/s3p34-calibration-review';
const $ = id => document.getElementById(id);
let state;
let current = 0;
let selectedCode = null;
let zoomOrigin = null;
let dirty = false;
const ZOOM_WIDTH = 320;
const ZOOM_HEIGHT = 240;

function status(message, error = false) {
  $('status').textContent = message;
  $('status').className = error ? 'error' : 'good';
}

function field(node, name) {
  return node.querySelector(`[data-field="${name}"]`);
}

function makeCard(landmark, saved) {
  const node = document.createElement('article');
  node.className = 'landmark';
  node.dataset.code = landmark.code;
  const number = state.landmarks.indexOf(landmark) + 1;
  const heading = document.createElement('h3');
  heading.textContent = `${number}. ${landmark.label}`;
  node.append(heading);
  const physical = document.createElement('p');
  physical.className = 'small';
  physical.textContent = `Court coordinate (${landmark.court_m.join(', ')}) m`;
  node.append(physical);
  const choose = document.createElement('label');
  choose.textContent = 'Visibility';
  const selection = document.createElement('select');
  selection.dataset.field = 'status';
  for (const [value, label] of [['', 'Choose…'], ['marked', 'Marked'],
    ['uncertain', 'Uncertain'], ['occluded', 'Occluded']]) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    selection.append(option);
  }
  selection.value = saved.status || '';
  selection.addEventListener('change', () => {
    dirty = true;
    if (selection.value === 'uncertain' || selection.value === 'occluded') {
      field(node, 'x').value = '';
      field(node, 'y').value = '';
      paintMarkers();
      if (selectedCode === landmark.code) $('zoom').hidden = true;
    }
  });
  choose.append(selection);
  node.append(choose);
  const buttons = document.createElement('div');
  buttons.className = 'controls';
  const mark = document.createElement('button');
  mark.type = 'button';
  mark.textContent = `Click point ${number}`;
  mark.addEventListener('click', () => selectLandmark(landmark.code));
  const clear = document.createElement('button');
  clear.type = 'button';
  clear.textContent = 'Clear';
  clear.addEventListener('click', () => {
    field(node, 'x').value = '';
    field(node, 'y').value = '';
    selection.value = '';
    dirty = true;
    paintMarkers();
    if (selectedCode === landmark.code) $('zoom').hidden = true;
  });
  buttons.append(mark, clear);
  node.append(buttons);
  const coordinates = document.createElement('div');
  coordinates.className = 'controls';
  for (const [key, labelText] of [['x', 'Source x (px)'], ['y', 'Source y (px)']]) {
    const label = document.createElement('label');
    label.textContent = labelText;
    const input = document.createElement('input');
    input.className = 'point';
    input.dataset.field = key;
    input.readOnly = true;
    input.value = saved[`${key}_px`] ?? '';
    label.append(input);
    coordinates.append(label);
  }
  node.append(coordinates);
  const noteLabel = document.createElement('label');
  noteLabel.textContent = 'Note (optional)';
  const note = document.createElement('input');
  note.className = 'note';
  note.maxLength = 1000;
  note.dataset.field = 'note';
  note.value = saved.note || '';
  note.addEventListener('input', () => { dirty = true; });
  noteLabel.append(note);
  node.append(noteLabel);
  return node;
}

function selectLandmark(code) {
  selectedCode = code;
  const landmark = state.landmarks.find(item => item.code === code);
  const number = state.landmarks.indexOf(landmark) + 1;
  $('marking').textContent = `Mark point ${number}: ${landmark.label}. Click the image, then refine in the enlarged crop.`;
  for (const node of $('rows').querySelectorAll('.landmark')) {
    node.classList.toggle('selected', node.dataset.code === code);
    if (node.dataset.code === code && field(node, 'x').value !== '' && field(node, 'y').value !== '') {
      openZoom(Number(field(node, 'x').value), Number(field(node, 'y').value));
    }
  }
  paintMarkers();
}

function paintMarkers() {
  const image = $('source');
  const canvas = $('overlay');
  if (!image.naturalWidth || !image.naturalHeight || !state) return;
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext('2d');
  context.font = 'bold 30px system-ui';
  context.lineWidth = 5;
  for (const node of $('rows').querySelectorAll('.landmark')) {
    const x = field(node, 'x').value, y = field(node, 'y').value;
    if (x === '' || y === '') continue;
    const number = state.landmarks.findIndex(item => item.code === node.dataset.code) + 1;
    context.strokeStyle = '#10151b';
    context.fillStyle = '#ffe066';
    context.beginPath();
    context.arc(Number(x), Number(y), node.dataset.code === selectedCode ? 12 : 9, 0, 2 * Math.PI);
    context.fill();
    context.stroke();
    context.strokeText(String(number), Number(x) + 15, Number(y) - 12);
    context.fillText(String(number), Number(x) + 15, Number(y) - 12);
  }
}

function openZoom(x, y) {
  const image = $('source');
  if (!image.naturalWidth || !image.naturalHeight) return;
  const left = Math.max(0, Math.min(image.naturalWidth - ZOOM_WIDTH, x - ZOOM_WIDTH / 2));
  const top = Math.max(0, Math.min(image.naturalHeight - ZOOM_HEIGHT, y - ZOOM_HEIGHT / 2));
  zoomOrigin = {left, top};
  const canvas = $('zoom');
  const context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, left, top, ZOOM_WIDTH, ZOOM_HEIGHT, 0, 0, canvas.width, canvas.height);
  context.strokeStyle = '#ffe066';
  context.lineWidth = 4;
  context.beginPath();
  context.arc((x - left) * canvas.width / ZOOM_WIDTH,
    (y - top) * canvas.height / ZOOM_HEIGHT, 12, 0, 2 * Math.PI);
  context.stroke();
  canvas.hidden = false;
}

function placeMark(x, y) {
  if (!selectedCode) { status('Choose a Click point button first.', true); return; }
  const image = $('source');
  x = Math.max(0, Math.min(image.naturalWidth - 0.1, x));
  y = Math.max(0, Math.min(image.naturalHeight - 0.1, y));
  const node = [...$('rows').querySelectorAll('.landmark')]
    .find(item => item.dataset.code === selectedCode);
  field(node, 'status').value = 'marked';
  field(node, 'x').value = x.toFixed(1);
  field(node, 'y').value = y.toFixed(1);
  if (field(node, 'note').value.startsWith('copied_from_frame_1759')) {
    field(node, 'note').value = '';
  }
  dirty = true;
  paintMarkers();
  openZoom(x, y);
  status(`Point ${state.landmarks.findIndex(item => item.code === selectedCode) + 1} marked at (${x.toFixed(1)}, ${y.toFixed(1)}) px.`);
}

function render() {
  const item = state.frames[current];
  const saved = state.draft.frames[String(item.frame)]?.rows || [];
  $('frameSelect').value = String(current);
  $('source').src = item.image_url;
  $('full').href = item.image_url;
  $('rows').replaceChildren();
  state.landmarks.forEach((landmark, index) => $('rows').append(makeCard(landmark, saved[index] || {})));
  $('zoom').hidden = true;
  zoomOrigin = null;
  selectedCode = null;
  $('marking').textContent = 'Choose a court intersection below, then click its centre in the source image.';
  paintMarkers();
  const savedCount = state.frames.filter(row => state.draft.frames[String(row.frame)]).length;
  $('progress').textContent = `Frame ${item.frame} (${current + 1}/2). ${savedCount}/2 source frames saved.`;
  state.frames.forEach((row, index) => {
    $('frameSelect').options[index].textContent = `${row.frame} · ${state.draft.frames[String(row.frame)] ? 'saved' : 'open'}`;
  });
  $('save').disabled = state.completed_csv_exists;
  const copiedCount = document.body.dataset.api?.includes('s1p6')
    ? Object.values(state.draft.frames).flatMap(frame => frame.rows)
      .filter(row => row.note?.startsWith('copied_from_frame_1759')).length
    : 0;
  $('export').disabled = savedCount !== 2 || state.completed_csv_exists || copiedCount > 0;
  $('exportStatus').textContent = state.completed_csv_exists
    ? 'The completed CSV is frozen; the page is read-only.'
    : copiedCount > 0
      ? `${copiedCount} copied points still need a click on this source image before freezing.`
      : 'The 12-point review is frozen only after you choose the export button.';
  const copy = $('copyFirst');
  if (copy) copy.hidden = current !== 1 || state.completed_csv_exists ||
    !state.draft.frames[String(state.frames[0].frame)];
  dirty = false;
  status('');
}

function copyFirstFrame() {
  const first = state.draft.frames[String(state.frames[0].frame)]?.rows;
  if (!first || current !== 1 || state.completed_csv_exists) return;
  for (const [index, landmark] of state.landmarks.entries()) {
    const node = [...$('rows').querySelectorAll('.landmark')][index];
    const saved = first[index];
    if (saved.code !== landmark.code) return;
    field(node, 'status').value = saved.status;
    field(node, 'x').value = saved.x_px ?? '';
    field(node, 'y').value = saved.y_px ?? '';
    field(node, 'note').value = `copied_from_frame_1759; verify on this image`;
  }
  dirty = true;
  paintMarkers();
  status('Starting points copied. Check each intersection against this image and click it to record an independent mark.');
}

function go(index) {
  if (dirty && !confirm('Unsaved marks on this frame will be lost. Continue?')) {
    $('frameSelect').value = String(current);
    return;
  }
  current = Math.max(0, Math.min(state.frames.length - 1, index));
  render();
}

async function save() {
  const rows = [];
  for (const node of $('rows').querySelectorAll('.landmark')) {
    const choice = field(node, 'status').value;
    const x = field(node, 'x').value;
    const y = field(node, 'y').value;
    if (!choice || (choice === 'marked' && (x === '' || y === ''))) {
      status(`Finish point ${state.landmarks.findIndex(item => item.code === node.dataset.code) + 1} or mark it uncertain/occluded.`, true);
      return;
    }
    rows.push({code: node.dataset.code, status: choice,
      x_px: choice === 'marked' ? Number(x) : null,
      y_px: choice === 'marked' ? Number(y) : null,
      note: field(node, 'note').value});
  }
  const reviewer_code = $('reviewer').value.trim();
  if (!reviewer_code) { status('Enter your reviewer code before saving.', true); return; }
  const frame = state.frames[current].frame;
  const previous = state.draft.frames[String(frame)]?.rows;
  if (previous && JSON.stringify(previous) === JSON.stringify(rows)) {
    status(`Frame ${frame} already has these marks saved.`);
    dirty = false;
    return;
  }
  try {
    const response = await fetch(`${API}/${frame}`, {method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({expected_revision: state.draft.revision, reviewer_code, rows})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail?.[0]?.msg || result.detail || `HTTP ${response.status}`);
    state.draft = result.draft;
    render();
    status(`Saved six source landmarks on frame ${frame}.`);
  } catch (error) { status(`Save failed: ${error.message}`, true); }
}

async function exportReview() {
  if (document.body.dataset.api?.includes('s1p6')) {
    for (const frame of Object.values(state.draft.frames)) {
      if (frame.rows.some(row => row.note?.startsWith('copied_from_frame_1759'))) {
        status('Click each copied intersection on the second image and save it before freezing.', true);
        return;
      }
    }
  }
  try {
    const response = await fetch(`${API}/export`, {method: 'POST'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    state.completed_csv_exists = true;
    render();
    status(`Froze ${result.rows} landmark rows. The calibration audit can now be run.`);
  } catch (error) { status(`Export failed: ${error.message}`, true); }
}

async function load() {
  try {
    const response = await fetch(API, {cache: 'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state = await response.json();
    if (state.frames.length !== 2 || state.landmarks.length !== 6) throw new Error('Unexpected protocol');
    $('reviewer').value = state.draft.reviewer_code || '';
    state.frames.forEach((item, index) => {
      const option = document.createElement('option');
      option.value = String(index);
      $('frameSelect').append(option);
    });
    render();
  } catch (error) { status(`Review page could not load: ${error.message}`, true); }
}

$('previous').addEventListener('click', () => go(current - 1));
$('next').addEventListener('click', () => go(current + 1));
if ($('copyFirst')) $('copyFirst').addEventListener('click', copyFirstFrame);
$('frameSelect').addEventListener('change', event => go(Number(event.target.value)));
$('save').addEventListener('click', save);
$('export').addEventListener('click', exportReview);
$('source').addEventListener('load', paintMarkers);
$('source').addEventListener('click', event => {
  const image = event.currentTarget, box = image.getBoundingClientRect();
  placeMark((event.clientX - box.left) * image.naturalWidth / box.width,
    (event.clientY - box.top) * image.naturalHeight / box.height);
});
$('zoom').addEventListener('click', event => {
  if (!zoomOrigin) return;
  const canvas = event.currentTarget, box = canvas.getBoundingClientRect();
  placeMark(zoomOrigin.left + (event.clientX - box.left) * ZOOM_WIDTH / box.width,
    zoomOrigin.top + (event.clientY - box.top) * ZOOM_HEIGHT / box.height);
});
load();
