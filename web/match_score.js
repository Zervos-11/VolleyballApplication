'use strict';
const $ = id => document.getElementById(id);
const match = 'yt_FqE5pTJqx8g';
let data, row, frame = 0, loaded = null, request = 0, imageUrl = null, stripUrl = null, stripFrames = [], dirty = false, audioSegment = null;
function key(r) { return `s${r.set}_p${r.point_number}`; }
function tell(message) { $('status').textContent = message; }
function time(n) { const s=n/data.source.fps;return `${Math.floor(s/60)}:${(s%60).toFixed(2).padStart(5,'0')}`; }
function setFrameLabel() { $('frameLabel').textContent=`${time(frame)} · frame ${frame}`;$('scrub').value=frame;$('jump').value=frame; }
async function readJson(url,options) { const response=await fetch(url,options);const body=await response.json();if(!response.ok)throw Error(body.detail||response.statusText);return body; }
function markDirty() { dirty=true;$('reviewState').textContent='Unsaved edits'; }
async function inspect(index) {
  if(!row)return;
  index=Math.max(0,Math.min(data.source.frame_count-1,Math.round(index)));
  const token=++request;loaded=null;$('video').pause();$('markStart').disabled=$('markEnd').disabled=true;
  try {
    const response=await fetch(`/api/${match}/frame/${index}`);if(!response.ok)throw Error(`Frame ${index} could not be decoded`);
    const url=URL.createObjectURL(await response.blob());const image=new Image();image.src=url;await image.decode();
    if(token!==request){URL.revokeObjectURL(url);return;}
    if(imageUrl)URL.revokeObjectURL(imageUrl);imageUrl=url;$('still').src=url;$('still').hidden=false;$('video').hidden=true;
    frame=index;loaded=index;setFrameLabel();$('markStart').disabled=Boolean(row.pilot_rally_id)||$('startVisibility').value!=='source_visible';$('markEnd').disabled=Boolean(row.pilot_rally_id);tell('Exact source frame loaded.');
  } catch(error) { if(token===request)tell(error.message); }
}
function renderList() {
  const list=$('pointList');list.replaceChildren();const set=$('setFilter').value,status=$('statusFilter').value;
  const rows=data.queue.rows.filter(r=>(set==='all'||String(r.set)===set)&&
    (status==='all'||(status==='pending'&&!r.pilot_rally_id&&(!data.saved[key(r)]||data.saved_qc[key(r)]))||
     (status==='checked'&&(r.pilot_rally_id||data.saved[key(r)]&&!data.saved_qc[key(r)]))));
  for(const r of rows){const button=document.createElement('button');button.textContent=`S${r.set} P${r.point_number} · ${r.score_before} → ${r.score_after}${r.pilot_rally_id?' · pilot':data.saved_qc[key(r)]?' · recheck':data.saved[key(r)]&&data.saved[key(r)].start_frame==null?' · partial':data.saved[key(r)]?' · checked':''}`;
    button.classList.toggle('active',row&&key(row)===key(r));button.onclick=()=>select(r);list.appendChild(button);}
  const flagged=Object.keys(data.saved_qc).length;
  const partial=Object.entries(data.saved).filter(([key,record])=>record.start_frame==null&&!data.saved_qc[key]).length;
  const checked=Object.keys(data.saved).length-flagged-partial+data.queue.rows.filter(r=>r.pilot_rally_id).length;
  $('progress').textContent=`${checked}/123 with full saved boundaries${partial?` · ${partial} partial`:''}${flagged?` · ${flagged} needs recheck`:''} · ${rows.length} shown`;
}
function select(r) {
  if(dirty&&!confirm('Discard unsaved boundary edits?'))return;
  row=r;dirty=false;loaded=null;const saved=data.saved[key(r)],candidate=data.source_candidates[key(r)];
  const audioPoint=data.audio_probe?.points?.[key(r)];
  $('audioProbe').pause();audioSegment=audioPoint?data.audio_probe.segments[audioPoint.segment]:null;
  $('audioBox').hidden=!audioPoint;
  if(audioPoint){
    const source=`/api/primary-match/score-review/audio-probe/${audioPoint.segment}`;
    if($('audioProbe').getAttribute('src')!==source)$('audioProbe').src=source;
    $('audioNote').textContent=`Experimental audio, ${audioSegment.start_s}–${audioSegment.end_s} s: tonal cues near ${audioPoint.tone_candidates_s.join(', ')} s. ${audioPoint.visual_context} These have not been confirmed as referee whistles.`;
    $('audioCue').onclick=async()=>{const seek=Math.max(0,audioPoint.tone_candidates_s[0]-audioSegment.start_s-1);$('audioProbe').currentTime=seek;try{await $('audioProbe').play();}catch(error){tell(error.message);}};
  }
  $('filmstrip').hidden=true;stripFrames=[];$('stripTitle').textContent='';
  $('pointTitle').textContent=`Set ${r.set}, point ${r.point_number}: ${r.score_before} → ${r.score_after} (${r.winner})`;
  $('pointContext').textContent=`Score-based seek window ${time(r.seek_from_frame)}–${time(r.seek_to_frame_exclusive)}. This is not a verified rally interval.${r.score_flip_frame==null?` Score evidence: ${r.score_evidence}.`:` Score digit first changes at frame ${r.score_flip_frame}. Review the ending around frames ${r.end_review_from_frame}–${r.end_review_to_frame}; the suggested end subtracts ${r.estimate_graphic_lag_frames} frames for the broadcast delay.`}${candidate?` Source screening: ${candidate.evidence} Candidate end ${candidate.suggested_end_frame_exclusive}.${candidate.start_evidence?` Serve setup: ${candidate.start_evidence} Candidate contact ${candidate.suggested_start_frame}.`:''}`:''}`;
  $('scrub').min=Math.max(0,r.seek_from_frame-750);$('scrub').max=Math.min(data.source.frame_count-1,r.seek_to_frame_exclusive+500);
  const afterFlip=Boolean(data.saved_qc[key(r)]?.includes('saved_end_on_or_after_score_change_recheck_source'));
  const unresolvedCandidate=Boolean(afterFlip&&candidate?.start_status==='serve_contact_not_resolved_in_source_screen');
  const startFlag=Boolean(data.saved_qc[key(r)]?.includes('saved_start_outside_source_screened_range_recheck'));
  const endFlag=Boolean(data.saved_qc[key(r)]?.some(flag=>flag.startsWith('saved_end_')));
  $('startVisibility').value=unresolvedCandidate?'uncertain':startFlag?'source_visible':saved?.serve_contact_status??'source_visible';
  $('start').value=$('startVisibility').value==='source_visible'?(startFlag?candidate.suggested_start_frame:saved?.start_frame??r.serve_contact_frame??r.estimated_start_frame??''):'';
  $('start').disabled=$('startVisibility').value!=='source_visible';$('goStart').disabled=$('start').disabled;
  $('end').value=endFlag&&candidate?candidate.suggested_end_frame_exclusive:saved?.end_frame_exclusive??r.end_frame_exclusive??r.estimated_end_frame_exclusive??'';
  $('annotator').value=saved?.annotator_id??$('annotator').value;$('notes').value=saved?.notes??'';
  $('servePosition').value=saved?.serve_position??'uncertain';
  $('checkedSource').checked=false;
  $('estimateNote').textContent=r.pilot_rally_id?'These are the existing checked pilot boundaries.':startFlag||endFlag?`${startFlag?`Saved start ${saved.start_frame} is outside the source-screened serve-contact range ${candidate.start_contact_interval_frames[0]}–${candidate.start_contact_interval_frames[1]}. `:''}${endFlag&&candidate?`Saved end ${saved.end_frame_exclusive} is outside the source-screened ending range ${candidate.end_contact_interval_frames[0]}–${candidate.end_contact_interval_frames[1]}. `:endFlag?'Saved end conflicts with the score-change timing. ':''}The flagged box shows a candidate where available, not an accepted label. Inspect the source before saving.`:saved?'These are your saved boundaries. Inspect source frames before changing them.':'These prefilled frame numbers are rough estimates from score timing and the five pilot rallies. Check and adjust both against the source video before saving.';
  $('save').disabled=Boolean(r.pilot_rally_id);$('reviewState').textContent=r.pilot_rally_id?'Pilot boundary checked in the pilot workspace':data.saved_qc[key(r)]?'Saved boundary conflicts with source check — recheck this point':saved?'Saved; independent review pending':'Rough estimate — needs source review';
  renderList();inspect(startFlag?candidate.suggested_start_frame:saved?.start_frame??r.serve_contact_frame??r.estimated_start_frame??Math.max(0,r.seek_to_frame_exclusive-500));
}
function nextPending() {
  const index=data.queue.rows.findIndex(r=>row&&key(r)===key(row));
  const later=data.queue.rows.slice(index+1).concat(data.queue.rows.slice(0,index+1));
  const next=later.find(r=>!r.pilot_rally_id&&(!data.saved[key(r)]||data.saved_qc[key(r)]));
  if(next)select(next);else tell('All scored points have a saved boundary check.');
}
document.querySelectorAll('[data-step]').forEach(button=>button.onclick=()=>inspect(frame+Number(button.dataset.step)));
$('go').onclick=()=>inspect(Number($('jump').value));$('scrub').onchange=()=>inspect(Number($('scrub').value));
$('goStart').onclick=()=>{if($('start').value)inspect(Number($('start').value));};
$('goEnd').onclick=()=>{if($('end').value)inspect(Number($('end').value));};
$('markStart').onclick=()=>{if(loaded!==null){$('start').value=loaded;markDirty();}};
$('startVisibility').onchange=()=>{
  const visible=$('startVisibility').value==='source_visible';
  $('start').disabled=!visible;$('goStart').disabled=!visible;$('markStart').disabled=!visible||loaded===null||Boolean(row?.pilot_rally_id);
  $('start').value=visible?(row?.estimated_start_frame??''):'';
  markDirty();
};
$('markEnd').onclick=()=>{if(loaded!==null){$('end').value=loaded;markDirty();}};
async function showStrip(kind) {
  if(!row)return;
  const selected=key(row);
  $('stripTitle').textContent='Loading source frames…';
  try {
    const response=await fetch(`/api/primary-match/score-review/${row.set}/${row.point_number}/filmstrip/${kind}`);
    if(!response.ok)throw Error(`Could not load ${kind} frames`);
    const frames=response.headers.get('X-Frame-Indices');
    const url=URL.createObjectURL(await response.blob());
    if(!row||key(row)!==selected){URL.revokeObjectURL(url);return;}
    if(stripUrl)URL.revokeObjectURL(stripUrl);stripUrl=url;stripFrames=frames.split(',').map(Number);
    $('filmstrip').src=url;$('filmstrip').hidden=false;
    $('stripTitle').textContent=`${kind==='start'?'Serve':'Ending'} sequence · click a frame to inspect it`;
  }catch(error){$('stripTitle').textContent=error.message;}
}
$('showStartStrip').onclick=()=>showStrip('start');
$('showEndStrip').onclick=()=>showStrip('end');
$('filmstrip').onclick=event=>{
  if(stripFrames.length!==9)return;
  const rect=$('filmstrip').getBoundingClientRect();
  const column=Math.min(2,Math.floor((event.clientX-rect.left)/rect.width*3));
  const line=Math.min(2,Math.floor((event.clientY-rect.top)/rect.height*3));
  inspect(stripFrames[line*3+column]);
};
$('nextPending').onclick=nextPending;
$('watch').onclick=async()=>{if(!row)return;++request;loaded=null;$('still').hidden=true;$('video').hidden=false;$('video').currentTime=frame/data.source.fps;try{await $('video').play();}catch(error){tell(error.message);}};
$('inspect').onclick=()=>inspect($('video').hidden?frame:Math.round($('video').currentTime*data.source.fps));
$('video').ontimeupdate=()=>{if($('video').hidden||!row)return;frame=Math.floor($('video').currentTime*data.source.fps);setFrameLabel();};
['start','end','annotator','notes','servePosition','checkedSource'].forEach(id=>$(id).addEventListener('input',markDirty));
['setFilter','statusFilter'].forEach(id=>$(id).onchange=renderList);
$('save').onclick=async()=>{
  if(!row||row.pilot_rally_id)return;
  const visible=$('startVisibility').value==='source_visible';
  const start=visible?Number($('start').value):null,end=Number($('end').value),annotator=$('annotator').value.trim();
  if((visible&&!$('start').value)||!$('end').value||!annotator||(visible&&!Number.isInteger(start))||!Number.isInteger(end)||(visible&&start>=end)){tell('Enter a valid serve state, ordered frame boundaries and an annotator code.');return;}
  if(!$('checkedSource').checked){tell('Inspect the visible boundary frames in the source video, then tick the source-check box.');return;}
  $('save').disabled=true;
  try{const saved=await readJson(`/api/primary-match/score-review/${row.set}/${row.point_number}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({start_frame:start,end_frame_exclusive:end,annotator_id:annotator,notes:$('notes').value,serve_position:$('servePosition').value,serve_contact_status:$('startVisibility').value,source_frames_checked:true})});
    data=await readJson('/api/primary-match/score-review');dirty=false;
    $('reviewState').textContent=data.saved_qc[key(row)]?'Saved; source recheck still required':saved.start_frame==null?'Partial review: serve unobservable':'Saved; independent review pending';
    tell('Saved. Previous version retained in review history.');renderList();nextPending();}
  catch(error){tell(error.message);}finally{$('save').disabled=false;}
};
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
(async()=>{try{data=await readJson('/api/primary-match/score-review');$('video').src=`/api/${match}/video`;select(data.queue.rows.find(r=>!r.pilot_rally_id));}catch(error){tell(error.message);}})();
