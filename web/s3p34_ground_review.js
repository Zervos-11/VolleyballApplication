'use strict';

const API = '/api/u5/s3p34-ground-review';
const $ = id => document.getElementById(id);
const SLOT_KEYS = ['28', '12', '15', '7', '19', '21'];
// BEGIN GENERATED NUMBERED TRACKER BOXES
const TRACKER_BOXES_BY_FRAME = {"36066":[[306,384,398,526],[634,397,704,582],[652,185,730,347],[782,176,842,329],[840,301,908,473],[513,185,576,351]],"36067":[[306,385,397,526],[637,398,708,582],[652,185,730,347],[781,176,843,330],[841,302,910,473],[512,186,576,351]],"36068":[[304,386,396,527],[639,398,712,582],[652,185,729,345],[781,176,842,327],[842,304,912,473],[512,186,575,352]],"36069":[[302,388,396,532],[642,400,716,583],[652,186,730,346],[782,176,843,326],[842,304,914,473],[513,187,575,351]],"36070":[[302,390,396,534],[644,401,720,583],[652,186,730,346],[782,177,845,333],[843,305,916,473],[513,187,575,351]],"36071":[[302,392,396,536],[645,402,723,584],[652,186,730,346],[782,176,845,334],[843,306,917,472],[513,187,574,350]],"36072":[[301,394,395,536],[645,403,726,583],[652,187,730,346],[783,176,847,336],[843,307,918,473],[513,187,574,350]],"36073":[[302,396,395,538],[647,404,730,584],[652,187,730,345],[784,177,849,340],[842,308,919,473],[512,188,573,350]],"36074":[[302,397,395,539],[647,406,732,583],[652,187,730,345],[785,177,850,341],[842,308,919,473],[512,188,572,350]],"36075":[[302,398,396,540],[646,408,733,583],[652,185,730,345],[787,177,851,342],[842,308,920,473],[512,188,572,350]],"36076":[[302,399,396,541],[645,410,734,583],[652,184,730,344],[788,177,852,342],[842,308,920,473],[512,188,572,350]],"36077":[[302,399,397,542],[645,411,735,583],[652,183,730,345],[790,177,853,342],[841,309,921,472],[512,188,572,351]],"36078":[[302,399,397,542],[645,413,736,583],[652,183,730,343],[791,177,854,343],[841,309,921,472],[513,188,573,350]],"36079":[[302,399,397,542],[644,414,738,583],[653,182,730,340],[793,177,855,343],[841,309,921,472],[513,188,573,349]],"36080":[[302,398,397,542],[644,414,739,583],[653,183,730,339],[794,177,856,343],[840,309,922,472],[513,188,573,348]],"36081":[[301,397,397,542],[644,414,740,583],[652,185,731,343],[796,177,857,343],[840,309,922,472],[513,188,572,347]],"36082":[[301,395,398,542],[643,414,741,583],[651,189,732,346],[794,176,856,343],[840,309,922,472],[513,188,572,348]],"36083":[[301,393,398,541],[642,414,741,583],[651,192,734,350],[797,176,858,344],[840,310,922,472],[510,188,570,350]],"36084":[[300,390,398,539],[642,413,742,583],[649,194,734,352],[799,177,860,344],[839,310,922,472],[510,188,561,324]],"36085":[[300,388,398,536],[641,413,742,583],[648,196,734,351],[800,176,860,342],[839,310,923,472],[506,189,564,343]],"36086":[[299,385,395,532],[640,412,743,583],[645,197,731,348],[802,176,860,335],[839,310,923,472],[503,190,560,346]],"36087":[[298,383,393,530],[640,411,744,583],[643,197,727,343],[802,176,861,337],[839,310,922,472],[500,191,556,346]],"36088":[[293,381,388,529],[638,410,744,583],[642,197,725,340],[800,176,861,338],[839,312,922,472],[498,192,553,342]],"36089":[[286,379,382,530],[637,408,744,583],[642,197,726,341],[799,175,860,337],[840,315,923,472],[496,194,550,339]],"36090":[[281,379,378,532],[637,408,744,583],[641,196,727,341],[800,176,857,323],[840,317,924,473],[494,197,548,341]],"36091":[[278,378,376,532],[637,408,744,583],[644,196,729,340],[803,176,860,319],[840,318,925,474],[488,199,543,342]],"36092":[[276,378,375,533],[637,408,744,583],[648,194,734,340],[804,176,862,323],[840,320,927,476],[481,200,538,345]],"36093":[[277,378,376,533],[637,409,744,583],[648,193,735,340],[802,177,863,326],[841,321,930,479],[477,202,535,347]],"36094":[[278,378,377,533],[638,410,744,583],[649,193,735,340],[800,178,863,330],[842,321,934,482],[475,202,535,348]],"36095":[[279,379,378,532],[638,411,744,583],[652,193,736,337],[802,178,865,332],[841,321,936,484],[473,200,534,348]],"36096":[[278,380,378,532],[638,412,744,583],[656,193,739,337],[803,178,867,335],[841,321,939,487],[473,199,535,348]],"36097":[[278,381,376,533],[638,412,744,582],[662,194,740,333],[801,178,866,336],[842,322,940,488],[473,199,536,348]],"36098":[[278,383,375,533],[638,413,744,581],[666,194,741,333],[801,179,866,337],[842,323,942,488],[474,197,540,348]],"36099":[[278,385,374,533],[638,414,743,580],[669,194,743,336],[802,180,867,338],[842,325,942,488],[474,193,542,348]],"36100":[[281,390,373,530],[637,415,741,578],[671,193,744,336],[801,181,866,339],[842,327,942,488],[471,188,541,347]],"36101":[[283,393,374,529],[633,415,739,579],[670,191,744,338],[802,182,867,337],[843,330,942,489],[470,180,541,344]],"36102":[[286,396,376,528],[628,416,736,578],[671,187,743,336],[801,182,865,336],[845,332,944,489],[468,170,543,343]]};
// END GENERATED NUMBERED TRACKER BOXES
const slotNumber = key => SLOT_KEYS.indexOf(key) + 1;
const IDENTITIES = [['', 'Choose…'], ['confirmed', 'Digit matches stored slot key'], ['sequence_only', 'Sequence only'], ['uncertain', 'Uncertain']];
const GROUND = [['', 'Choose…'], ['grounded', 'Grounded'], ['airborne', 'Airborne'], ['occluded', 'Feet occluded'], ['uncertain', 'Uncertain']];
const CANDIDATE = [['', 'Choose…'], ['same_player', 'Same player'], ['wrong_player', 'Wrong player'], ['uncertain', 'Uncertain']];
const FLOOR = [['', 'Choose…'], ['plausible', 'Plausible floor proxy'], ['implausible', 'Implausible floor proxy'], ['uncertain', 'Uncertain']];
let state;
let current = 0;
let dirty = false;
let selectedJersey = null;
let zoomOrigin = null;
const SHOE_COLORS = { '28': '#70d6ff', '12': '#ffcc66', '15': '#b6f37b',
  '7': '#fa8fbb', '19': '#c49eff', '21': '#ff9c70' };
const ZOOM_SOURCE_WIDTH = 320;
const ZOOM_SOURCE_HEIGHT = 240;

function select(name, options, value = '') {
  const label = document.createElement('label');
  label.textContent = name;
  const control = document.createElement('select');
  for (const [key, title] of options) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = title;
    control.append(option);
  }
  control.value = value || '';
  label.append(control);
  control.addEventListener('change', () => { dirty = true; });
  return label;
}

function input(name, value = '', className = '') {
  const label = document.createElement('label');
  label.textContent = name;
  const control = document.createElement('input');
  control.type = name === 'Notes' ? 'text' : 'number';
  if (control.type === 'number') control.step = 'any';
  control.value = value ?? '';
  control.className = className;
  if (name === 'Shoe x (px)' || name === 'Shoe y (px)') {
    control.readOnly = true;
    control.title = 'Click the source image or enlarged crop to fill this coordinate';
  }
  control.addEventListener('input', () => { dirty = true; });
  label.append(control);
  return label;
}

function uncertaintySelect(value) {
  const values = ['', '10', '12', '15', '20', '30', '50'];
  const chosen = value == null ? '' : String(value);
  if (chosen && !values.includes(chosen)) values.push(chosen);
  return select('Uncertainty (px)', values.map(item => [item, item || 'Choose…']), chosen);
}

function card(jersey, fields, kind = 'Player') {
  const article = document.createElement('article');
  article.className = 'player';
  article.dataset.jersey = jersey;
  const title = document.createElement('h3');
  title.textContent = `${kind} ${slotNumber(jersey)} · stored slot ${jersey}`;
  article.append(title);
  const controls = document.createElement('div');
  controls.className = 'controls';
  controls.append(...fields);
  article.append(controls);
  return article;
}

function field(cardNode, name) {
  return [...cardNode.querySelectorAll('label')].find(label => label.firstChild.textContent === name)?.querySelector('input,select');
}

function showStatus(message, error = false) {
  $('status').textContent = message;
  $('status').className = error ? 'error' : 'good';
}

function sourceCard(jersey, saved) {
  const node = card(jersey, [
    select('Identity', IDENTITIES, saved.identity_status || 'confirmed'),
    select('Ground', GROUND, saved.ground_status || 'grounded'),
    input('Shoe x (px)', saved.shoe_midpoint_x_px, 'point'),
    input('Shoe y (px)', saved.shoe_midpoint_y_px, 'point'),
    uncertaintySelect(saved.reading_uncertainty_px),
    input('Notes', saved.notes),
  ]);
  const mark = document.createElement('button');
  mark.type = 'button';
  mark.textContent = `Mark shoe point for player ${slotNumber(jersey)}`;
  mark.addEventListener('click', () => selectMarkPlayer(jersey));
  const clear = document.createElement('button');
  clear.type = 'button';
  clear.textContent = 'Clear point';
  clear.addEventListener('click', () => {
    for (const name of ['Shoe x (px)', 'Shoe y (px)', 'Uncertainty (px)']) field(node, name).value = '';
    dirty = true;
    paintMarkers();
    if (selectedJersey === jersey) $('zoomCanvas').hidden = true;
  });
  const actions = document.createElement('div');
  actions.className = 'controls';
  actions.append(mark, clear);
  node.append(actions);
  field(node, 'Ground').addEventListener('change', () => {
    if (field(node, 'Ground').value === 'grounded') return;
    for (const name of ['Shoe x (px)', 'Shoe y (px)', 'Uncertainty (px)']) field(node, name).value = '';
    if (selectedJersey === jersey) $('zoomCanvas').hidden = true;
    paintMarkers();
  });
  return node;
}

function selectMarkPlayer(jersey) {
  selectedJersey = jersey;
  for (const node of $('sourceRows').querySelectorAll('.player')) {
    node.classList.toggle('selected', node.dataset.jersey === jersey);
  }
  $('markStatus').textContent = `Marking player ${slotNumber(jersey)} (stored slot ${jersey})`;
  const node = [...$('sourceRows').querySelectorAll('.player')].find(item => item.dataset.jersey === jersey);
  const x = Number(field(node, 'Shoe x (px)').value);
  const y = Number(field(node, 'Shoe y (px)').value);
  if (field(node, 'Shoe x (px)').value !== '' && field(node, 'Shoe y (px)').value !== '') {
    openZoom(x, y);
  } else {
    $('zoomCanvas').hidden = true;
  }
  paintMarkers();
}

function paintMarkers() {
  const image = $('sourceImage');
  const canvas = $('sourceOverlay');
  if (!image.naturalWidth || !image.naturalHeight) return;
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext('2d');
  context.font = 'bold 19px system-ui';
  context.lineWidth = 3;
  for (const node of $('sourceRows').querySelectorAll('.player')) {
    const xValue = field(node, 'Shoe x (px)').value;
    const yValue = field(node, 'Shoe y (px)').value;
    if (xValue === '' || yValue === '') continue;
    const x = Number(xValue), y = Number(yValue);
    const jersey = node.dataset.jersey;
    const color = SHOE_COLORS[jersey];
    context.strokeStyle = '#10151b';
    context.fillStyle = color;
    context.beginPath();
    context.arc(x, y, jersey === selectedJersey ? 11 : 8, 0, 2 * Math.PI);
    context.fill();
    context.stroke();
    context.strokeStyle = '#10151b';
    context.lineWidth = 4;
    context.strokeText(String(slotNumber(jersey)), x + 13, y - 10);
    context.fillText(String(slotNumber(jersey)), x + 13, y - 10);
  }
}

function paintTrackerBoxes() {
  const image = $('pairedImage');
  const canvas = $('pairedOverlay');
  if (!image.naturalWidth || !image.naturalHeight) return;
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext('2d');
  const boxes = TRACKER_BOXES_BY_FRAME[String(state.frames[current].frame)] || [];
  for (let index = 0; index < boxes.length; index++) {
    const box = boxes[index];
    if (!box) continue;
    const [x1, y1, x2, y2] = box;
    context.lineJoin = 'round';
    context.strokeStyle = '#10151b';
    context.lineWidth = 8;
    context.strokeRect(x1, y1, x2 - x1, y2 - y1);
    context.strokeStyle = '#ffffff';
    context.lineWidth = 4;
    context.strokeRect(x1, y1, x2 - x1, y2 - y1);
    const badgeX = Math.max(2, Math.min(image.naturalWidth - 50, x1 + 4));
    const badgeY = Math.max(2, Math.min(image.naturalHeight - 46, y1 + 4));
    context.fillStyle = '#10151b';
    context.fillRect(badgeX - 2, badgeY - 2, 46, 42);
    context.fillStyle = '#ffe066';
    context.fillRect(badgeX, badgeY, 42, 38);
    context.fillStyle = '#10151b';
    context.font = 'bold 30px system-ui';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(String(index + 1), badgeX + 21, badgeY + 19);
  }
}

function openZoom(x, y) {
  const image = $('sourceImage');
  if (!image.naturalWidth || !image.naturalHeight) return;
  const left = Math.max(0, Math.min(image.naturalWidth - ZOOM_SOURCE_WIDTH, x - ZOOM_SOURCE_WIDTH / 2));
  const top = Math.max(0, Math.min(image.naturalHeight - ZOOM_SOURCE_HEIGHT, y - ZOOM_SOURCE_HEIGHT / 2));
  zoomOrigin = { left, top };
  const canvas = $('zoomCanvas');
  const context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, left, top, ZOOM_SOURCE_WIDTH, ZOOM_SOURCE_HEIGHT,
    0, 0, canvas.width, canvas.height);
  context.strokeStyle = SHOE_COLORS[selectedJersey] || '#ffffff';
  context.lineWidth = 3;
  context.beginPath();
  context.arc((x - left) * canvas.width / ZOOM_SOURCE_WIDTH,
    (y - top) * canvas.height / ZOOM_SOURCE_HEIGHT, 12, 0, 2 * Math.PI);
  context.stroke();
  canvas.hidden = false;
}

function placeMark(x, y) {
  if (!selectedJersey) {
    showStatus('Choose a “Mark shoe point” button for a player first.', true);
    return;
  }
  const node = [...$('sourceRows').querySelectorAll('.player')]
    .find(item => item.dataset.jersey === selectedJersey);
  if (field(node, 'Ground').value !== 'grounded') {
    showStatus(`Choose Grounded for #${selectedJersey} before placing a shoe point.`, true);
    return;
  }
  const image = $('sourceImage');
  x = Math.max(0, Math.min(image.naturalWidth - 0.1, x));
  y = Math.max(0, Math.min(image.naturalHeight - 0.1, y));
  field(node, 'Shoe x (px)').value = x.toFixed(1);
  field(node, 'Shoe y (px)').value = y.toFixed(1);
  if (!field(node, 'Uncertainty (px)').value) field(node, 'Uncertainty (px)').value = '15';
  dirty = true;
  paintMarkers();
  openZoom(x, y);
  showStatus(`Marked #${selectedJersey} at (${x.toFixed(1)}, ${y.toFixed(1)}) source pixels. Refine in the enlarged crop, then save the frame.`);
}

function render() {
  const item = state.frames[current];
  const frame = item.frame;
  const record = state.draft.frames[String(frame)] || {};
  $('frameSelect').value = String(current);
  $('sourceSection').hidden = false;
  $('sourceImage').src = item.image_url;
  $('sourceImage').alt = `Unboxed source frame ${frame}`;
  $('sourceFull').href = item.image_url;
  $('sourceRows').replaceChildren();
  for (const jersey of state.jerseys) {
    const saved = record.source?.find(row => row.jersey === jersey) || {};
    $('sourceRows').append(sourceCard(jersey, saved));
  }
  $('zoomCanvas').hidden = true;
  zoomOrigin = null;
  $('markStatus').textContent = 'No player selected';
  paintMarkers();
  $('pairedSection').hidden = !record.source;
  $('pairedRows').replaceChildren();
  if (record.source) {
    $('pairedImage').src = item.image_url;
    $('pairedImage').alt = `Source frame ${frame} with high-contrast tracker boxes numbered 1 to 6`;
    $('pairedFull').href = item.paired_url;
    paintTrackerBoxes();
    for (const jersey of state.jerseys) {
      const saved = record.paired?.find(row => row.jersey === jersey) || {};
      $('pairedRows').append(card(jersey, [
        select('Candidate box', CANDIDATE, saved.candidate_alignment || 'same_player'),
        select('Box-bottom floor proxy', FLOOR, saved.proxy_floor_alignment || 'plausible'),
      ], 'Box'));
    }
  }
  const sourceCount = state.frames.filter(item => state.draft.frames[String(item.frame)]?.source).length;
  const pairedCount = state.frames.filter(item => state.draft.frames[String(item.frame)]?.paired).length;
  state.frames.forEach((queueItem, index) => {
    const saved = state.draft.frames[String(queueItem.frame)];
    $('frameSelect').options[index].textContent = `${queueItem.frame} · ${saved?.paired ? 'done' : saved?.source ? 'compare' : 'source'}`;
  });
  $('progress').textContent = `Frame ${frame} (${current + 1}/${state.frames.length}); source stage ${sourceCount}/30, tracker stage ${pairedCount}/30. Current frame: ${record.paired ? 'complete' : record.source ? 'source saved; compare tracker' : 'source pending'}.`;
  $('export').disabled = pairedCount !== 30 || state.completed_csv_exists;
  $('saveSource').disabled = state.completed_csv_exists;
  $('savePaired').disabled = state.completed_csv_exists;
  $('exportStatus').textContent = state.completed_csv_exists
    ? 'A completed CSV already exists. It will not be overwritten.'
    : 'Draft revisions are saved locally in the review packet.';
  dirty = false;
  showStatus('');
}

function go(index) {
  if (dirty && !confirm('Unsaved edits on this frame will be lost. Continue?')) {
    $('frameSelect').value = String(current);
    return;
  }
  current = Math.max(0, Math.min(state.frames.length - 1, index));
  selectedJersey = null;
  render();
}

function numberOrNull(value) {
  return value.trim() === '' ? null : Number(value);
}

async function save(stage) {
  const frame = state.frames[current].frame;
  const rows = [];
  const cards = [...$(stage === 'source' ? 'sourceRows' : 'pairedRows').querySelectorAll('.player')];
  for (const node of cards) {
    const jersey = node.dataset.jersey;
    if (stage === 'source') {
      const identity_status = field(node, 'Identity').value;
      const ground_status = field(node, 'Ground').value;
      if (!identity_status || !ground_status) {
        showStatus(`Choose identity and ground state for #${jersey}.`, true);
        return;
      }
      const x = numberOrNull(field(node, 'Shoe x (px)').value);
      const y = numberOrNull(field(node, 'Shoe y (px)').value);
      const uncertainty = numberOrNull(field(node, 'Uncertainty (px)').value);
      if ([x, y, uncertainty].some(value => value !== null) &&
          (ground_status !== 'grounded' || [x, y, uncertainty].some(value => value === null))) {
        showStatus(`Shoe x, y and uncertainty for #${jersey} must all be entered on a grounded row, or all blank.`, true);
        return;
      }
      rows.push({ jersey, identity_status, ground_status, shoe_midpoint_x_px: x,
        shoe_midpoint_y_px: y, reading_uncertainty_px: uncertainty,
        notes: field(node, 'Notes').value });
    } else {
      const candidate_alignment = field(node, 'Candidate box').value;
      const proxy_floor_alignment = field(node, 'Box-bottom floor proxy').value;
      if (!candidate_alignment || !proxy_floor_alignment) {
        showStatus(`Choose both tracker comparisons for #${jersey}.`, true);
        return;
      }
      rows.push({ jersey, candidate_alignment, proxy_floor_alignment });
    }
  }
  const reviewer_code = $('reviewerCode').value.trim();
  if (stage === 'source' && !reviewer_code) {
    showStatus('Enter a reviewer code before saving.', true);
    return;
  }
  const saved = state.draft.frames[String(frame)]?.[stage];
  if (saved && JSON.stringify(rows) === JSON.stringify(saved)) {
    showStatus(`Frame ${frame} already has these ${stage === 'source' ? 'source judgments' : 'tracker comparisons'} saved.`);
    dirty = false;
    return;
  }
  if (stage === 'source' && state.draft.frames[String(frame)]?.paired &&
      !confirm('Changing source judgments requires checking the tracker comparison for this frame again. Continue?')) return;
  try {
    const payload = { expected_revision: state.draft.revision, rows };
    if (stage === 'source') payload.reviewer_code = reviewer_code;
    const response = await fetch(`${API}/${frame}/${stage}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail?.[0]?.msg || result.detail || `HTTP ${response.status}`);
    state.draft = result.draft;
    selectedJersey = null;
    render();
    showStatus(`Saved ${stage === 'source' ? 'source judgments' : 'tracker comparisons'} for frame ${frame}.`);
  } catch (error) {
    showStatus(`Save failed: ${error.message}`, true);
  }
}

async function exportCsv() {
  try {
    const response = await fetch(`${API}/export`, { method: 'POST' });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    state.completed_csv_exists = true;
    render();
    showStatus(`Exported ${result.rows} rows to ${result.completed_csv}. Run the scorer script to count accepted slots.`);
  } catch (error) {
    showStatus(`Export failed: ${error.message}`, true);
  }
}

async function load() {
  try {
    const response = await fetch(API, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state = await response.json();
    if (state.frames.length !== 30 || state.jerseys.length !== 6) throw new Error('Unexpected review queue');
    $('reviewerCode').value = state.draft.reviewer_code || '';
    state.frames.forEach((item, index) => {
      const option = document.createElement('option');
      option.value = String(index);
      option.textContent = `${item.frame} · ${state.draft.frames[String(item.frame)]?.paired ? 'done' : state.draft.frames[String(item.frame)]?.source ? 'compare' : 'source'}`;
      $('frameSelect').append(option);
    });
    render();
  } catch (error) { showStatus(`Review page could not load: ${error.message}`, true); }
}

$('previous').addEventListener('click', () => go(current - 1));
$('next').addEventListener('click', () => go(current + 1));
$('nextIncomplete').addEventListener('click', () => {
  const index = state.frames.findIndex((item, i) => i > current && !state.draft.frames[String(item.frame)]?.paired);
  go(index < 0 ? state.frames.findIndex(item => !state.draft.frames[String(item.frame)]?.paired) : index);
});
$('frameSelect').addEventListener('change', event => go(Number(event.target.value)));
$('saveSource').addEventListener('click', () => save('source'));
$('savePaired').addEventListener('click', () => save('paired'));
$('export').addEventListener('click', exportCsv);
$('sourceImage').addEventListener('load', paintMarkers);
$('pairedImage').addEventListener('load', paintTrackerBoxes);
$('sourceImage').addEventListener('click', event => {
  const image = event.currentTarget;
  const box = image.getBoundingClientRect();
  placeMark((event.clientX - box.left) * image.naturalWidth / box.width,
    (event.clientY - box.top) * image.naturalHeight / box.height);
});
$('zoomCanvas').addEventListener('click', event => {
  if (!zoomOrigin) return;
  const canvas = event.currentTarget;
  const box = canvas.getBoundingClientRect();
  placeMark(zoomOrigin.left + (event.clientX - box.left) * ZOOM_SOURCE_WIDTH / box.width,
    zoomOrigin.top + (event.clientY - box.top) * ZOOM_SOURCE_HEIGHT / box.height);
});
load();
