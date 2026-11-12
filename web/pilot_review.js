'use strict';
const el = id => document.getElementById(id);
const match = new URLSearchParams(location.search).get('match') || 'yt_FqE5pTJqx8g';
const api = `/api/${encodeURIComponent(match)}`;
el('playerLink').href = `/players?match=${encodeURIComponent(match)}&rally=r1`;
let data, rally, fps, currentFrame = 0, loadedFrame = null, frameRequest = 0, dirty = false, imageUrl, revision = 0;
function status(message) { el('status').textContent = message; }
function time(frame) { const s = frame / fps; return `${Math.floor(s / 60).toString().padStart(2,'0')}:${(s % 60).toFixed(2).padStart(5,'0')}`; }
async function jsonRequest(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail));
  return payload;
}
function change() { revision++; dirty = true; el('reviewState').textContent = 'Unsaved boundary edits'; }
function showIndex() {
  el('frameText').textContent = `${time(currentFrame)} · source frame ${currentFrame}`;
  el('frameRange').value = currentFrame; el('jump').value = currentFrame;
}
async function inspect(index) {
  if (!rally || !Number.isInteger(index)) return;
  index = Math.max(rally.window_start_frame, Math.min(index, rally.window_end_frame_exclusive - 1));
  const token = ++frameRequest;
  el('video').pause(); loadedFrame = null;
  el('markStart').disabled = el('markEnd').disabled = true;
  status(`Loading source frame ${index}…`);
  try {
    const response = await fetch(`${api}/frame/${index}`);
    if (!response.ok) throw new Error(`Could not load frame ${index}`);
    const blob = await response.blob();
    if (token !== frameRequest) return;
    const nextUrl = URL.createObjectURL(blob);
    const image = new Image(); image.src = nextUrl;
    await image.decode();
    if (token !== frameRequest) { URL.revokeObjectURL(nextUrl); return; }
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    imageUrl = nextUrl; el('still').src = imageUrl;
    el('still').hidden = false; el('video').hidden = true;
    currentFrame = index; loadedFrame = index; showIndex();
    el('markStart').disabled = el('markEnd').disabled = false;
    status('Frame loaded. Inspect serve contact or the first frame after the point-ending action.');
  } catch (error) { if (token === frameRequest) status(error.message); }
}
function choose(id) {
  if (el('save').disabled) return;
  if (dirty && !confirm('Discard your unsaved boundary edits?')) return;
  rally = data.selection.rallies.find(r => r.rally_id === id);
  el('playerLink').href = `/players?match=${encodeURIComponent(match)}&rally=${encodeURIComponent(id)}`;
  el('playerLink').textContent = `Open player annotations for ${id} →`;
  const saved = data.reviews[id];
  el('rallyTitle').textContent = `${id}${rally.set_number == null ? '' : ` · set ${rally.set_number}`} · about ${time(rally.start_frame)}`;
  el('context').textContent = rally.notes;
  el('start').value = saved?.start_frame ?? rally.start_frame;
  el('end').value = saved?.end_frame_exclusive ?? rally.end_frame_exclusive;
  el('usable').value = String(saved?.usable ?? true);
  el('notes').value = saved?.notes ?? '';
  if (saved) el('annotator').value = saved.annotator_id;
  el('frameRange').min = rally.window_start_frame; el('frameRange').max = rally.window_end_frame_exclusive - 1;
  document.querySelectorAll('#rallies button').forEach(b => b.classList.toggle('active', b.dataset.rally === id));
  el('reviewState').textContent = saved ? `Saved by ${saved.annotator_id}; independent review pending` : 'Draft estimate — needs your check';
  dirty = false; inspect(Math.max(rally.window_start_frame, Number(el('start').value) - fps));
}
el('steps').addEventListener('click', event => { if (event.target.dataset.step) inspect(currentFrame + Number(event.target.dataset.step)); });
el('go').onclick = () => inspect(Number(el('jump').value));
el('frameRange').onchange = () => inspect(Number(el('frameRange').value));
el('gotoStart').onclick = () => inspect(Number(el('start').value));
el('gotoEnd').onclick = () => inspect(Number(el('end').value));
el('markStart').onclick = () => { if (loadedFrame !== null) { el('start').value = loadedFrame; change(); } };
el('markEnd').onclick = () => { if (loadedFrame !== null) { el('end').value = loadedFrame; change(); } };
el('watch').onclick = async () => {
  ++frameRequest; loadedFrame = null; el('markStart').disabled = el('markEnd').disabled = true;
  el('still').hidden = true; el('video').hidden = false; el('video').currentTime = currentFrame / fps;
  try { await el('video').play(); } catch (error) { status(error.message); }
};
el('inspect').onclick = () => inspect(el('video').hidden ? currentFrame : Math.round(el('video').currentTime * fps));
el('video').ontimeupdate = () => {
  if (el('video').hidden || !rally) return;
  if (el('video').currentTime >= rally.window_end_frame_exclusive / fps) el('video').pause();
  currentFrame = Math.max(0, Math.min(data.source.frame_count - 1, Math.floor(el('video').currentTime * fps))); showIndex();
};
['start','end','annotator','usable','notes'].forEach(id => el(id).addEventListener('input', change));
el('save').onclick = async () => {
  const start = Number(el('start').value), end = Number(el('end').value), annotator = el('annotator').value.trim();
  if (!annotator || !Number.isInteger(start) || !Number.isInteger(end) || !(rally.window_start_frame <= start && start < end && end <= rally.window_end_frame_exclusive)) {
    status('Enter your annotator code and valid, ordered boundaries inside this review window.'); return;
  }
  if (el('usable').value === 'false' && !el('notes').value.trim()) { status('Explain why this rally should be excluded.'); return; }
  el('save').disabled = true;
  const savedRevision = revision;
  try {
    const saved = await jsonRequest(`${api}/rallies/${rally.rally_id}`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({start_frame:start,end_frame_exclusive:end,annotator_id:annotator,usable:el('usable').value === 'true',notes:el('notes').value})});
    data.reviews[rally.rally_id] = saved; dirty = revision !== savedRevision;
    el('reviewState').textContent = dirty ? 'Earlier changes saved; newer edits are unsaved' : `Saved by ${saved.annotator_id}; independent review pending`;
    status('Saved to pilot/boundary_review.json. Previous decisions are retained in pilot/review_history.');
  } catch (error) { status(error.message); }
  finally { el('save').disabled = false; }
};
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
(async () => {
  try {
    data = await jsonRequest(`${api}/pilot`); fps = data.source.camera.fps;
    document.querySelectorAll('#steps button[data-step]').forEach(button => {
      const step = Number(button.dataset.step);
      if (Math.abs(step) === 50) button.dataset.step = String(Math.sign(step) * Math.round(fps));
    });
    el('subtitle').textContent = `${data.source.source_title} · ${data.selection.rallies.length} draft rallies · ${fps} fps`;
    el('video').src = `${api}/video`;
    data.selection.rallies.forEach(r => { const b = document.createElement('button'); b.dataset.rally = r.rally_id; b.textContent = `${r.rally_id}${r.set_number == null ? '' : ` · set ${r.set_number}`} · ${time(r.start_frame)}`; b.onclick = () => choose(r.rally_id); el('rallies').appendChild(b); });
    choose(data.selection.rallies[0].rally_id);
  } catch (error) { status(error.message); }
})();
