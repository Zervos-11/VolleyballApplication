const source = '/api/yt_D79JrsJsFgs/frame/';
const $ = (id) => document.getElementById(id);
const image = $('frameImage');
const overlay = $('overlay');
const video = $('video');
let record = null;
let selectedFrame = 80;
let imageRequest = 0;

function seek(frame, syncVideo = true) {
  selectedFrame = Math.max(40, Math.min(336, Math.round(frame)));
  $('slider').value = selectedFrame;
  $('frameLabel').textContent = `Frame ${selectedFrame}`;
  overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height);
  const request = ++imageRequest;
  const nextImage = new Image();
  nextImage.onload = () => {
    if (request !== imageRequest) return;
    image.src = nextImage.src;
  };
  nextImage.onerror = () => {
    if (request === imageRequest) $('frameCaption').textContent = 'Source frame could not be loaded.';
  };
  nextImage.src = `${source}${selectedFrame}`;
  if (syncVideo && Number.isFinite(video.duration)) video.currentTime = selectedFrame / 60;
  renderSlots();
}

function draw() {
  if (!record || !image.naturalWidth) return;
  overlay.width = image.naturalWidth;
  overlay.height = image.naturalHeight;
  const ctx = overlay.getContext('2d');
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  const players = record.frames[String(selectedFrame)];
  if (!players) return;
  for (const id of record.player_order) {
    const player = players[id];
    if (!player.position_px) continue;
    const [x, y] = player.position_px;
    const held = player.status === 'held_assumption';
    ctx.strokeStyle = held ? '#ffb74d' : '#65e48d';
    ctx.fillStyle = held ? '#ffb74d' : '#65e48d';
    ctx.lineWidth = 3;
    ctx.setLineDash(held ? [7, 5] : []);
    if (player.bbox) {
      const [x1, y1, x2, y2] = player.bbox;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    }
    ctx.beginPath();
    ctx.arc(x, y, held ? 15 : 5, 0, 2 * Math.PI);
    held ? ctx.stroke() : ctx.fill();
    ctx.setLineDash([]);
    ctx.font = 'bold 22px system-ui';
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#10202a';
    ctx.strokeText(`#${id}${held ? ' last seen' : ''}`, x + 12, y - 15);
    ctx.fillText(`#${id}${held ? ' last seen' : ''}`, x + 12, y - 15);
  }
}

function renderSlots() {
  if (!record) return;
  const players = record.frames[String(selectedFrame)];
  const setup = selectedFrame < 80;
  $('frameCaption').textContent = setup
    ? `Source frame ${selectedFrame}: pre-rally identity setup. No tracker position is claimed here.`
    : `Source frame ${selectedFrame}: green is an accepted box-bottom proxy; orange is last seen.`;
  $('status').textContent = setup
    ? 'Use these clear frames to read jerseys before the point.'
    : `${Object.values(players).filter(p => p.status === 'observed_proxy').length} accepted proxies · ${Object.values(players).filter(p => p.status === 'held_assumption').length} held identities · ${Object.values(players).filter(p => p.status === 'airborne_excluded').length} excluded`;
  $('slots').replaceChildren();
  if (!players) return;
  for (const id of record.player_order) {
    const player = players[id];
    const row = document.createElement('tr');
    const state = player.status === 'observed_proxy' ? 'Accepted box proxy'
      : player.status === 'held_assumption' ? 'Last seen; current position unknown'
      : 'Airborne serve; position excluded';
    const cls = player.status === 'observed_proxy' ? 'observed'
      : player.status === 'held_assumption' ? 'held' : 'excluded';
    row.innerHTML = `<th scope="row">#${id}${id === '4' ? ' (jersey 14?)' : ''}</th><td class="${cls}">${state}</td><td>${player.raw_track_id ?? '—'}</td>`;
    $('slots').append(row);
  }
}

async function load() {
  try {
    const response = await fetch('/api/case-studies/d79/seeded-holds', {cache: 'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    record = await response.json();
    renderEstimates();
    seek(selectedFrame);
  } catch (error) {
    $('status').textContent = `Identity record could not be loaded: ${error.message}`;
  }
}

function renderEstimates() {
  $('estimates').replaceChildren();
  for (const id of record.player_order) {
    const estimate = record.endpoint_estimates[id];
    const [start, end] = estimate.scope_frames_inclusive;
    const row = document.createElement('tr');
    const metres = estimate.metres === null ? 'Withheld' : `≈ ${estimate.metres.toFixed(2)} m`;
    const gap = estimate.unclosed_hold_at_point_end_frames;
    row.innerHTML = `<th scope="row">#${id}</th><td>${metres}</td><td>${start}–${end}</td><td>≈ ${estimate.full_point_hold_scenario_m.toFixed(2)} m${estimate.clamped_proxy_points ? ' *' : ''}</td><td>${gap ? `${gap} frames without a return` : 'None'}</td>`;
    $('estimates').append(row);
  }
  $('teamScenario').textContent = `Six-player full-point stationary-hold scenario: ≈ ${record.team_stationary_hold_scenario_m.toFixed(2)} m. This is a model-based proxy total.`;
}

for (const [button, frame] of [['seed40', 40], ['seed55', 55], ['point80', 80],
                                ['overlap148', 148], ['return289', 289]]) {
  $(button).addEventListener('click', () => seek(frame));
}
$('previous').addEventListener('click', () => seek(selectedFrame - 1));
$('next').addEventListener('click', () => seek(selectedFrame + 1));
$('slider').addEventListener('input', event => seek(Number(event.target.value)));
video.addEventListener('timeupdate', () => {
  const frame = Math.round(video.currentTime * 60);
  if (!video.paused && frame >= 40 && frame <= 336 && frame !== selectedFrame) seek(frame, false);
});
video.addEventListener('loadedmetadata', () => { video.currentTime = selectedFrame / 60; });
image.addEventListener('load', draw);
load();
