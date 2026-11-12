'use strict';

const START = 21050;
const END = 21464;
const FPS = 50;
const PLAYERS = ['9', '10', '11', '12', '13', '20'];
const REVIEW_FRAMES = [...new Set([
  ...Array.from({ length: Math.ceil((END - START) / 10) }, (_, i) => START + i * 10),
  21064, 21065, 21099, 21132, 21245, 21250, 21265,
  21304, 21308, 21310, 21311, 21313, 21316, 21340, 21423, END - 1,
])].filter(frame => frame >= START && frame < END).sort((a, b) => a - b);
const P20_GROUND_BREAKPOINT_FRAMES = [21333, 21338, 21343, 21393, 21397,
  21402, 21430, 21440, 21457, 21460, 21463];
const matchId = 'yt_FqE5pTJqx8g';
const video = document.getElementById('preview');
const image = document.getElementById('sourceFrame');
const canvas = document.getElementById('boxOverlay');
const zoomCanvas = document.getElementById('floorZoom');
const netLineButton = document.getElementById('toggleNetLine');
const shoeCueButton = document.getElementById('toggleShoeCues');
const shoeCueStatus = document.getElementById('shoeCueStatus');
const footCentreDistance = document.getElementById('footCentreDistance');
const pointSummaryStatus = document.getElementById('pointSummaryStatus');
const pointSummaryPlayers = document.getElementById('pointSummaryPlayers');
const holdButton = document.getElementById('toggleHolds');
const slider = document.getElementById('frameSlider');
const frameLabel = document.getElementById('frameLabel');
const caption = document.getElementById('sourceCaption');
const slotsBody = document.getElementById('slots');
const status = document.getElementById('status');
const floorPlayer = document.getElementById('floorPlayer');
const floorState = document.getElementById('floorState');
const floorNote = document.getElementById('floorNote');
const floorPointLabel = document.getElementById('floorPoint');
const floorStatus = document.getElementById('floorStatus');
const reviewerCode = document.getElementById('reviewerCode');
const floorProgress = document.getElementById('floorProgress');
const queueProgress = document.getElementById('queueProgress');
let frames = null;
let selectedFrame = START;
let showBoxes = true;
let showNetLine = false;
let showHolds = false;
let showShoeCues = false;
let netLine = null;
let displayHolds = {};
let shoeCueFrames = new Map();
let floorRecords = {};
let pendingPoint = null;
let shownFrame = null;
let zoomRect = null;
const colors = { '9': '#35d24e', '10': '#e4d350', '11': '#ffae2e',
  '12': '#ca6ecf', '13': '#e56879', '20': '#4bdcdb' };

function drawBoxes() {
  const width = image.clientWidth;
  const height = image.clientHeight;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const context = canvas.getContext('2d');
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  if (!frames || !image.naturalWidth || !width) return;
  const record = frames[selectedFrame - START];
  const sx = width / image.naturalWidth;
  const sy = height / image.naturalHeight;
  context.lineWidth = 2;
  context.font = 'bold 16px system-ui';
  if (showNetLine && netLine) {
    context.strokeStyle = '#ff5f59';
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(netLine[0] * sx, netLine[1] * sy);
    context.lineTo(netLine[2] * sx, netLine[3] * sy);
    context.stroke();
  }
  if (showBoxes) {
    for (const player of PLAYERS) {
      const candidate = record.players[player];
      if (candidate.box_status !== 'raw_box_candidate' || !candidate.bbox_px) continue;
      const [x1, y1, x2, y2] = candidate.bbox_px;
      const x = x1 * sx;
      const y = y1 * sy;
      context.strokeStyle = colors[player];
      context.strokeRect(x, y, (x2 - x1) * sx, (y2 - y1) * sy);
      const label = `#${player}?`;
      const top = Math.max(17, y - 5);
      context.lineWidth = 4;
      context.strokeStyle = '#111';
      context.strokeText(label, x, top);
      context.fillStyle = colors[player];
      context.fillText(label, x, top);
      context.lineWidth = 2;
    }
  }
  if (showHolds) {
    for (const [player, held] of Object.entries(displayHolds[String(selectedFrame)] || {})) {
      if (record.players[player]?.box_status !== 'missing' || !held.display_anchor_px) continue;
      const x = held.display_anchor_px[0] * sx;
      const y = held.display_anchor_px[1] * sy;
      context.strokeStyle = colors[player];
      context.lineWidth = 3;
      context.setLineDash([5, 5]);
      context.beginPath();
      context.arc(x, y, 14, 0, 2 * Math.PI);
      context.stroke();
      context.setLineDash([]);
      context.lineWidth = 4;
      context.strokeStyle = '#111';
      context.strokeText(`#${player} last seen`, x + 17, y - 8);
      context.fillStyle = colors[player];
      context.fillText(`#${player} last seen`, x + 17, y - 8);
    }
  }
  if (showShoeCues && floorPlayer.value === '20') {
    const shoeRow = shoeCueFrames.get(selectedFrame);
    const regions = shoeRow?.selected_regions || [];
    for (const [index, region] of regions.entries()) {
      const [px, py] = region.sole_cue_px;
      const x = px * sx;
      const y = py * sy;
      context.strokeStyle = '#0b1d2a';
      context.lineWidth = 5;
      context.beginPath();
      context.arc(x, y, 10, 0, 2 * Math.PI);
      context.stroke();
      context.strokeStyle = '#84dcff';
      context.lineWidth = 2;
      context.stroke();
      context.fillStyle = '#84dcff';
      context.font = 'bold 13px system-ui';
      context.fillText(`S${index + 1}?`, x + 13, y - 8);
    }
    const playerBox = record.players['20'];
    if (playerBox?.box_status === 'raw_box_candidate' && playerBox.bbox_px) {
      const [x1, , x2, y2] = playerBox.bbox_px;
      const middle = regions.length === 2
        ? [(regions[0].sole_cue_px[0] + regions[1].sole_cue_px[0]) / 2,
           Math.max(regions[0].sole_cue_px[1], regions[1].sole_cue_px[1])]
        : [(x1 + x2) / 2, y2];
      const x = middle[0] * sx;
      const y = middle[1] * sy;
      context.fillStyle = '#15202b';
      context.fillRect(x - 8, y - 8, 16, 16);
      context.fillStyle = '#ffd166';
      context.fillRect(x - 5, y - 5, 10, 10);
      context.font = 'bold 13px system-ui';
      context.fillText('centre proxy', x + 12, y + 5);
    }
  }
  for (const player of PLAYERS) {
    const saved = floorRecords[String(selectedFrame)]?.[player];
    const point = player === floorPlayer.value
      ? (floorState.value === 'grounded_contact_visible' ? pendingPoint : null)
      : saved?.footpoint_px;
    if (!point) continue;
    const x = point[0] * sx;
    const y = point[1] * sy;
    context.strokeStyle = '#10151b';
    context.lineWidth = 5;
    context.beginPath();
    context.moveTo(x - 7, y); context.lineTo(x + 7, y);
    context.moveTo(x, y - 7); context.lineTo(x, y + 7);
    context.stroke();
    context.strokeStyle = colors[player];
    context.lineWidth = 2;
    context.stroke();
  }
}

function renderZoom() {
  if (!pendingPoint || !image.naturalWidth || shownFrame !== selectedFrame) {
    zoomRect = null;
    zoomCanvas.hidden = true;
    return;
  }
  const cropWidth = Math.min(240, image.naturalWidth);
  const cropHeight = Math.min(180, image.naturalHeight);
  const left = Math.max(0, Math.min(image.naturalWidth - cropWidth, pendingPoint[0] - cropWidth / 2));
  const top = Math.max(0, Math.min(image.naturalHeight - cropHeight, pendingPoint[1] - cropHeight / 2));
  zoomRect = { left, top, width: cropWidth, height: cropHeight };
  const ctx = zoomCanvas.getContext('2d');
  ctx.clearRect(0, 0, zoomCanvas.width, zoomCanvas.height);
  ctx.drawImage(image, left, top, cropWidth, cropHeight, 0, 0, zoomCanvas.width, zoomCanvas.height);
  if (showNetLine && netLine) {
    ctx.strokeStyle = '#ff5f59';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo((netLine[0] - left) * zoomCanvas.width / cropWidth,
      (netLine[1] - top) * zoomCanvas.height / cropHeight);
    ctx.lineTo((netLine[2] - left) * zoomCanvas.width / cropWidth,
      (netLine[3] - top) * zoomCanvas.height / cropHeight);
    ctx.stroke();
  }
  const x = (pendingPoint[0] - left) * zoomCanvas.width / cropWidth;
  const y = (pendingPoint[1] - top) * zoomCanvas.height / cropHeight;
  ctx.strokeStyle = '#10151b';
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(x - 10, y); ctx.lineTo(x + 10, y);
  ctx.moveTo(x, y - 10); ctx.lineTo(x, y + 10);
  ctx.stroke();
  ctx.strokeStyle = '#ffe15a';
  ctx.lineWidth = 2;
  ctx.stroke();
  zoomCanvas.hidden = false;
}

function updateFloorForm() {
  const saved = floorRecords[String(selectedFrame)]?.[floorPlayer.value];
  pendingPoint = saved?.footpoint_px || null;
  floorState.value = saved?.state || 'uncertain';
  floorNote.value = saved?.note || '';
  floorPointLabel.textContent = pendingPoint
    ? `Floor point: ${pendingPoint[0]}, ${pendingPoint[1]} px`
    : 'No floor point';
  floorStatus.textContent = saved
    ? `Saved ${saved.state} for #${floorPlayer.value} at frame ${selectedFrame}.`
    : `No saved floor review for #${floorPlayer.value} at frame ${selectedFrame}.`;
  if (selectedFrame === 21064 && ['11', '12'].includes(floorPlayer.value)) {
    floorStatus.textContent += ' Near-net shoe point: inspect the enlarged crop before using its projected court position.';
  }
  drawBoxes();
  updateShoeCueStatus();
  renderZoom();
}

function updateShoeCueStatus() {
  if (shoeCueButton.disabled) return;
  if (!showShoeCues) {
    shoeCueStatus.textContent = '#20 shoe cues are hidden. Show them to inspect unverified colour regions.';
  } else if (floorPlayer.value !== '20') {
    shoeCueStatus.textContent = 'Select #20 in the floor review to display her shoe cues.';
  } else {
    const row = shoeCueFrames.get(selectedFrame);
    shoeCueStatus.textContent = row
      ? `${row.selected_regions.length} unverified #20 shoe cue(s) at frame ${selectedFrame}. ${row.parent_box_status === 'raw_box_candidate' ? 'Gold square: two-shoe centre at lower shoe height, or box-bottom centre fallback.' : 'No usable player box; centre proxy is unknown.'}`
      : `No #20 shoe trial at frame ${selectedFrame}; gold square uses the box-bottom centre if its box is valid.`;
  }
}

function updateFloorProgress() {
  const reviewedFrames = Object.keys(floorRecords);
  let savedStates = 0;
  let contacts = 0;
  const groundedFrames = Object.fromEntries(PLAYERS.map(player => [player, new Set()]));
  for (const [frame, players] of Object.entries(floorRecords)) {
    for (const [player, record] of Object.entries(players)) {
      savedStates += 1;
      if (record.state === 'grounded_contact_visible' && record.footpoint_px && groundedFrames[player]) {
        contacts += 1;
        groundedFrames[player].add(frame);
      }
    }
  }
  const eligible = PLAYERS.filter(player => groundedFrames[player].size >= 2);
  floorProgress.textContent = `${contacts} shoe contacts across ${reviewedFrames.length} source frame(s); ${savedStates} saved player-frame states. ${eligible.length} player(s) have contacts on two or more distinct frames. Two contacts alone do not validate a movement path.`;
  updateQueueProgress();
}

function updateQueueProgress() {
  const player = floorPlayer.value;
  const planned = reviewFramesForPlayer(player);
  const completed = planned.filter(frame => floorRecords[String(frame)]?.[player]).length;
  queueProgress.textContent = `${completed}/${planned.length} planned frames reviewed for #${player}`;
}

function reviewFramesForPlayer(player) {
  return player === '20'
    ? [...new Set([...REVIEW_FRAMES, ...P20_GROUND_BREAKPOINT_FRAMES])].sort((a, b) => a - b)
    : REVIEW_FRAMES;
}

function nextUnreviewedFrame() {
  video.pause();
  const player = floorPlayer.value;
  const planned = reviewFramesForPlayer(player);
  const next = planned.find(frame => frame > selectedFrame && !floorRecords[String(frame)]?.[player])
    ?? planned.find(frame => !floorRecords[String(frame)]?.[player]);
  if (next === undefined) {
    floorStatus.textContent = `All ${planned.length} planned frames have a saved state for #${player}. Review other frames as needed.`;
    return;
  }
  renderFrame(next, true);
}

function clampFrame(value) {
  return Math.max(START, Math.min(END - 1, Number(value) || START));
}

function renderFrame(value, seekVideo = false) {
  const frame = clampFrame(value);
  const changed = frame !== selectedFrame;
  selectedFrame = frame;
  if (changed) {
    shownFrame = null;
    zoomRect = null;
    zoomCanvas.hidden = true;
  }
  slider.value = String(frame);
  frameLabel.textContent = `Frame ${frame} · +${((frame - START) / FPS).toFixed(2)} s`;
  caption.textContent = `Original source frame ${frame}; exact frame index.`;
  canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  image.src = `/api/${matchId}/frame/${frame}`;
  if (seekVideo && Math.abs(video.currentTime - (frame - START) / FPS) > 0.011) {
    video.currentTime = (frame - START) / FPS;
  }
  if (!frames) return;
  const record = frames[frame - START];
  slotsBody.replaceChildren();
  for (const player of PLAYERS) {
    const candidate = record.players[player];
    const held = displayHolds[String(frame)]?.[player];
    const tr = document.createElement('tr');
    const name = document.createElement('th');
    const box = document.createElement('td');
    const track = document.createElement('td');
    name.textContent = `#${player}`;
    box.textContent = candidate.box_status === 'raw_box_candidate'
      ? 'Candidate box'
      : candidate.box_status === 'invalid_truncated'
        ? 'Truncated box withheld'
        : held
          ? `No box; possible crossing, last seen ${held.hold_age_frames} frame(s) ago`
        : 'No usable box';
    box.className = candidate.box_status === 'raw_box_candidate' ? 'candidate' : 'missing';
    track.textContent = candidate.raw_track_id == null ? '—' : `T${candidate.raw_track_id}`;
    tr.append(name, box, track);
    slotsBody.append(tr);
  }
  if (changed) updateFloorForm();
  else updateShoeCueStatus();
}

async function loadRecord() {
  try {
    const response = await fetch('/api/case-studies/r1/record', { cache: 'no-store' });
    if (!response.ok) throw new Error(`Record request returned ${response.status}`);
    const data = await response.json();
    if (data.match_id !== matchId || data.rally_id !== 'r1' ||
        data.frame_records?.length !== END - START ||
        data.frame_records.some((row, i) => row.frame !== START + i ||
          PLAYERS.some(player => !row.players?.[player]))) {
      throw new Error('The six-slot record has an unexpected frame range or roster');
    }
    frames = data.frame_records;
    status.textContent = 'Candidate boxes are shown for inspection only. All court positions remain unknown.';
    await loadHolds().catch(() => { holdButton.title = 'Crossing holds unavailable'; });
    await loadNetLine().catch(() => { netLineButton.title = 'Recorded net line unavailable'; });
    await loadShoeCues().catch(error => {
      shoeCueStatus.textContent = `#20 shoe cues unavailable: ${error.message}`;
    });
    await loadFootCentreDistance().catch(error => {
      footCentreDistance.textContent = `#20 estimate unavailable: ${error.message}`;
    });
    await loadPointSummary().catch(error => {
      pointSummaryStatus.textContent = `Point summary unavailable: ${error.message}`;
    });
    const requested = Number(new URLSearchParams(location.search).get('frame'));
    renderFrame(requested >= START && requested < END ? requested : START, true);
    await loadFloorReview().catch(error => {
      floorStatus.textContent = `Could not load saved floor reviews: ${error.message}`;
    });
  } catch (error) {
    status.textContent = `Could not load the six-slot record: ${error.message}`;
  }
}

async function loadHolds() {
  const response = await fetch('/api/case-studies/r1/occlusion-holds', { cache: 'no-store' });
  if (!response.ok) throw new Error(`Crossing-hold request returned ${response.status}`);
  const data = await response.json();
  if (data.match_id !== matchId || data.rally_id !== 'r1' || data.status !== 'visual_occlusion_display_aid_not_tracking') {
    throw new Error('Invalid crossing-hold record');
  }
  displayHolds = data.holds || {};
  holdButton.disabled = false;
  holdButton.textContent = 'Show last-seen markers';
}

async function loadNetLine() {
  const response = await fetch('/api/case-studies/r1/net-line', { cache: 'no-store' });
  if (!response.ok) throw new Error(`Net-line request returned ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data.net_line_px) || data.net_line_px.length !== 4 ||
      !data.net_line_px.every(Number.isFinite)) throw new Error('Invalid net line');
  netLine = data.net_line_px;
  netLineButton.disabled = false;
}

async function loadShoeCues() {
  const response = await fetch('/api/case-studies/r1/shoe-cues', { cache: 'no-store' });
  if (!response.ok) throw new Error(`request returned ${response.status}`);
  const data = await response.json();
  if (data.status !== 'body_box_conditioned_white_shoe_contact_cue_trial' ||
      data.player_id !== '20' || data.frames?.length !== 164 ||
      data.frames.some((row, index) => row.frame !== 21300 + index ||
        row.verified_floor_contact_px !== null || row.court_position_m !== null ||
        !Array.isArray(row.selected_regions) ||
        row.selected_regions.some(region => !Array.isArray(region.sole_cue_px) ||
          region.sole_cue_px.length !== 2 || !region.sole_cue_px.every(Number.isFinite)))) {
    throw new Error('trial record has unexpected frames or certified positions');
  }
  shoeCueFrames = new Map(data.frames.map(row => [row.frame, row]));
  shoeCueButton.disabled = false;
  updateShoeCueStatus();
}

async function loadFootCentreDistance() {
  const response = await fetch('/api/case-studies/r1/foot-centre-distance', { cache: 'no-store' });
  if (!response.ok) throw new Error(`request returned ${response.status}`);
  const data = await response.json();
  const full = data.distance_proxy_m_by_interval_and_window?.full_candidate_point;
  if (data.status !== 'development_foot_level_center_distance_proxy' ||
      data.player_id !== '20' || data.frames_inclusive?.[0] !== START ||
      data.frames_inclusive?.[1] !== END - 1 || data.per_frame?.length !== END - START ||
      data.physical_distance_released !== false ||
      ![full?.['5'], full?.['15'], full?.['31']].every(Number.isFinite)) {
    throw new Error('invalid estimate record');
  }
  const lower = Math.min(full['5'], full['31']);
  const upper = Math.max(full['5'], full['31']);
  footCentreDistance.textContent = `${full['15'].toFixed(1)} m approximate over the 8.28 s candidate point (50 fps). Five- to 31-frame smoothing gives ${lower.toFixed(1)}–${upper.toFixed(1)} m. This is a development case-study estimate for #20.`;
}

async function loadPointSummary() {
  const response = await fetch('/api/case-studies/r1/point-summary', { cache: 'no-store' });
  if (!response.ok) throw new Error(`request returned ${response.status}`);
  const data = await response.json();
  if (data.status !== 'bounded_single_reviewer_development_point_summary' ||
      data.match_id !== matchId || data.rally_id !== 'r1' ||
      data.frames_inclusive?.[0] !== START || data.frames_inclusive?.[1] !== END - 1 ||
      data.players?.length !== PLAYERS.length ||
      data.players.some((player, index) => player.player_id !== PLAYERS[index] ||
        player.valid_box_frames + player.invalid_truncated_box_frames +
        player.missing_box_frames !== END - START)) {
    throw new Error('invalid point summary');
  }
  pointSummaryStatus.textContent = `${data.summary.all_six_usable_box_frames}/${END - START} frames have six usable candidate boxes; ${data.summary.valid_player_box_slots}/${data.summary.total_player_box_slots} player-frame box slots are usable.`;
  pointSummaryPlayers.replaceChildren();
  for (const player of data.players) {
    const tr = document.createElement('tr');
    const values = [player.display_name,
      `${player.valid_box_frames}/${END - START} (${player.box_coverage_percent.toFixed(1)}%)`,
      `${player.missing_box_frames} missing${player.invalid_truncated_box_frames ? `; ${player.invalid_truncated_box_frames} truncated` : ''}`,
      player.approximate_distance_m == null ? '—' :
        `${player.approximate_distance_m.toFixed(['10', '12'].includes(player.player_id) ? 2 : 1)} m`,
      player.distance_note || ''];
    for (const value of values) {
      const cell = document.createElement('td');
      cell.textContent = value;
      tr.append(cell);
    }
    pointSummaryPlayers.append(tr);
  }
}

async function loadFloorReview() {
  const response = await fetch('/api/case-studies/r1/floor-review', { cache: 'no-store' });
  if (!response.ok) throw new Error(`Floor-review request returned ${response.status}`);
  floorRecords = (await response.json()).records || {};
  updateFloorProgress();
  updateFloorForm();
}

async function saveFloorReview() {
  const frame = selectedFrame;
  const player = floorPlayer.value;
  const reviewer = reviewerCode.value.trim();
  const state = floorState.value;
  const point = state === 'grounded_contact_visible' ? pendingPoint : null;
  if (!reviewer) { floorStatus.textContent = 'Enter your reviewer code before saving.'; return; }
  if (state === 'grounded_contact_visible' && !point) {
    floorStatus.textContent = 'Click a shoe-floor contact on the exact source image before saving.';
    return;
  }
  try {
    const response = await fetch(`/api/case-studies/r1/floor-review/${frame}/${player}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer_id: reviewer, state, footpoint_px: point, note: floorNote.value.trim() }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Save returned ${response.status}`);
    }
    const saved = (await response.json()).saved;
    if (!floorRecords[String(frame)]) floorRecords[String(frame)] = {};
    floorRecords[String(frame)][player] = saved;
    updateFloorProgress();
    if (frame === selectedFrame && player === floorPlayer.value) updateFloorForm();
  } catch (error) {
    floorStatus.textContent = `Could not save: ${error.message}`;
  }
}

slider.addEventListener('input', () => renderFrame(slider.value, true));
document.getElementById('previous').addEventListener('click', () => renderFrame(Number(slider.value) - 1, true));
document.getElementById('next').addEventListener('click', () => renderFrame(Number(slider.value) + 1, true));
document.getElementById('toggleBoxes').addEventListener('click', event => {
  showBoxes = !showBoxes;
  event.currentTarget.setAttribute('aria-pressed', String(showBoxes));
  event.currentTarget.textContent = showBoxes ? 'Hide candidate boxes' : 'Show candidate boxes';
  drawBoxes();
});
holdButton.addEventListener('click', () => {
  if (holdButton.disabled) return;
  showHolds = !showHolds;
  holdButton.setAttribute('aria-pressed', String(showHolds));
  holdButton.textContent = showHolds ? 'Hide last-seen markers' : 'Show last-seen markers';
  drawBoxes();
});
netLineButton.addEventListener('click', () => {
  if (!netLine) return;
  showNetLine = !showNetLine;
  netLineButton.setAttribute('aria-pressed', String(showNetLine));
  netLineButton.textContent = showNetLine ? 'Hide recorded net-floor line' : 'Show recorded net-floor line';
  drawBoxes();
  renderZoom();
});
shoeCueButton.addEventListener('click', () => {
  if (shoeCueButton.disabled) return;
  showShoeCues = !showShoeCues;
  shoeCueButton.setAttribute('aria-pressed', String(showShoeCues));
  shoeCueButton.textContent = showShoeCues ? 'Hide #20 shoe cues' : 'Show #20 shoe cues';
  drawBoxes();
  updateShoeCueStatus();
});
video.addEventListener('timeupdate', () => renderFrame(START + Math.floor(video.currentTime * FPS), false));
image.addEventListener('load', () => {
  const match = new URL(image.currentSrc).pathname.match(/\/frame\/(\d+)$/);
  shownFrame = match ? Number(match[1]) : null;
  drawBoxes();
  renderZoom();
});
image.addEventListener('error', () => { caption.textContent = 'Could not load this source frame.'; });
image.addEventListener('click', event => {
  video.pause();
  if (!frames || !image.naturalWidth || shownFrame !== selectedFrame) {
    floorStatus.textContent = 'Wait for the exact source frame to load before choosing a point.';
    return;
  }
  const rect = image.getBoundingClientRect();
  pendingPoint = [Math.round((event.clientX - rect.left) * image.naturalWidth / rect.width * 10) / 10,
    Math.round((event.clientY - rect.top) * image.naturalHeight / rect.height * 10) / 10];
  floorState.value = 'grounded_contact_visible';
  floorPointLabel.textContent = `Floor point: ${pendingPoint[0]}, ${pendingPoint[1]} px`;
  floorStatus.textContent = 'Point selected; save to record it.';
  drawBoxes();
  renderZoom();
});
zoomCanvas.addEventListener('click', event => {
  video.pause();
  if (!zoomRect || shownFrame !== selectedFrame) return;
  const rect = zoomCanvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width;
  const y = (event.clientY - rect.top) / rect.height;
  pendingPoint = [Math.round((zoomRect.left + x * zoomRect.width) * 10) / 10,
    Math.round((zoomRect.top + y * zoomRect.height) * 10) / 10];
  floorState.value = 'grounded_contact_visible';
  floorPointLabel.textContent = `Floor point: ${pendingPoint[0]}, ${pendingPoint[1]} px`;
  floorStatus.textContent = 'Refined point selected; save to record it.';
  drawBoxes();
  renderZoom();
});
floorPlayer.addEventListener('change', () => { video.pause(); updateFloorForm(); updateQueueProgress(); });
document.getElementById('nextReview').addEventListener('click', nextUnreviewedFrame);
floorState.addEventListener('change', () => {
  video.pause();
  if (floorState.value !== 'grounded_contact_visible') {
    pendingPoint = null;
    floorPointLabel.textContent = 'No floor point';
    drawBoxes();
    renderZoom();
  }
});
document.getElementById('saveFloor').addEventListener('click', saveFloorReview);
new ResizeObserver(drawBoxes).observe(image);
loadRecord();
