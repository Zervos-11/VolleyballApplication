'use strict';
const $ = id => document.getElementById(id);
const query = new URLSearchParams(location.search);
const match = query.get('match') || 'yt_FqE5pTJqx8g', rally = query.get('rally') || 'r1';
const side = query.get('side') === 'far' ? 'far' : 'near';
const api = `/api/${encodeURIComponent(match)}`, endpointBase = `${api}/players/${encodeURIComponent(rally)}`;
const endpoint = `${endpointBase}?side=${side}`;
const canvas = $('canvas'), ctx = canvas.getContext('2d');
let data, frame, image, included = [], pending, selected = -1, mode = 'select', drag = null;
let dirty = false, formDirty = false, busy = false, requestIndex = 0;
let denseIndices = [];
let proposalExposure = false;
const clone = value => JSON.parse(JSON.stringify(value));
const message = text => $('status').textContent = text;
const frameReviewed = index => !!data?.review_attestation &&
  index >= data.review_attestation.first_frame && index <= data.review_attestation.last_frame;
function block(value) { busy = value; document.querySelectorAll('button,input,select,textarea').forEach(e => e.disabled = value); }
function emptyPlayer() { return {player_id:'',team_id:'unknown',bbox:null,occlusion:'none',position_status:'uncertain',footpoint:null,origin_proposal_id:null,notes:''}; }
function discardForm() { return !formDirty || confirm('Discard the current player edit?'); }
function fill(player, index=-1) {
  pending = clone(player); selected = index; formDirty = false;
  $('playerId').value = pending.player_id; $('team').value = pending.team_id;
  $('occlusion').value = pending.occlusion; $('position').value = pending.position_status; $('playerNotes').value = pending.notes;
  geometry(); draw();
}
function geometry() { $('geometry').textContent = `Box: ${pending?.bbox?.map(Math.round).join(', ') || 'empty'} · Foot: ${pending?.footpoint?.map(Math.round).join(', ') || 'empty'}`; }
function drawBox(box, color, label) {
  if (!box) return;
  const [x1,y1,x2,y2] = box; ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.strokeRect(x1,y1,x2-x1,y2-y1);
  if (label) { ctx.font = '22px sans-serif'; ctx.fillStyle = '#101722'; const width = ctx.measureText(label).width+10; ctx.fillRect(x1,Math.max(0,y1-28),width,27); ctx.fillStyle = color; ctx.fillText(label,x1+4,Math.max(22,y1-6)); }
}
function dot(point, color) { if (!point) return; ctx.fillStyle=color;ctx.beginPath();ctx.arc(point[0],point[1],7,0,Math.PI*2);ctx.fill(); }
function draw() {
  if (!image) return;
  ctx.drawImage(image,0,0,canvas.width,canvas.height);
  if ($('showProposals').checked && frame.proposals.length) {
    proposalExposure = true;
    frame.proposals.forEach(p => drawBox(p.bbox,'#a4aab2',''));
  }
  included.forEach(p => { drawBox(p.bbox,'#63e8ad',p.player_id);dot(p.footpoint,'#63e8ad'); });
  if (pending) { drawBox(pending.bbox,'#ffe271',pending.player_id || 'edit');dot(pending.footpoint,'#ffe271'); }
  geometry();
}
function listPlayers() {
  $('people').replaceChildren(); $('count').textContent=`Included players: ${included.length}`;
  included.forEach((person,i) => { const button=document.createElement('button');const state=!person.bbox && person.occlusion==='partial'?'partly visible / no box':person.position_status;button.textContent=`${person.player_id} · ${state}`;button.onclick=()=>{if(!busy && discardForm())fill(person,i);};$('people').appendChild(button); });
}
function updateDenseProgress() {
  if (!denseIndices.length) return;
  const saved = denseIndices.filter(i => data.saved.frames[String(data.draft.frames[i].frame_index)]);
  const complete = saved.filter(i => data.saved.frames[String(data.draft.frames[i].frame_index)].all_players_accounted_for);
  $('denseProgress').textContent = `Dense slice: ${saved.length}/${denseIndices.length} saved, ${complete.length} marked complete`;
}
function coordinates(event) { const rect=canvas.getBoundingClientRect();return [Math.max(0,Math.min(canvas.width-0.01,(event.clientX-rect.left)*canvas.width/rect.width)),Math.max(0,Math.min(canvas.height-0.01,(event.clientY-rect.top)*canvas.height/rect.height))]; }
function contains(box,p) { return box && box[0]<=p[0] && p[0]<=box[2] && box[1]<=p[1] && p[1]<=box[3]; }
document.querySelectorAll('[data-mode]').forEach(button => button.onclick=()=>{mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b===button));});
canvas.onpointerdown = event => {
  if (busy || !image) return;
  const point=coordinates(event);
  if(mode==='select') {
    if(!discardForm())return;
    const index=included.findIndex(p=>contains(p.bbox,point));
    if(index>=0){fill(included[index],index);return;}
    if(!$('showProposals').checked)return;
    const candidates=frame.proposals.filter(p=>contains(p.bbox,point)).sort((a,b)=>(a.bbox[2]-a.bbox[0])*(a.bbox[3]-a.bbox[1])-(b.bbox[2]-b.bbox[0])*(b.bbox[3]-b.bbox[1]));
    if(candidates.length){fill({...emptyPlayer(),bbox:candidates[0].bbox,origin_proposal_id:candidates[0].proposal_id});message('Assign a stable player ID, check visibility and mark feet if visible. Then include this player.');}
  } else if(mode==='foot') {
    if(!pending)fill(emptyPlayer());pending.footpoint=point;pending.position_status='visible';$('position').value='visible';formDirty=true;draw();
  } else {
    if(!pending)fill(emptyPlayer());drag=point;canvas.setPointerCapture(event.pointerId);
  }
};
canvas.onpointermove = event => {if(!drag || busy)return;const p=coordinates(event);pending.bbox=[Math.min(drag[0],p[0]),Math.min(drag[1],p[1]),Math.max(drag[0],p[0]),Math.max(drag[1],p[1])];formDirty=true;draw();};
canvas.onpointerup = event => {if(drag){drag=null;if(pending.occlusion==='full'){pending.occlusion='partial';$('occlusion').value='partial';}if(pending.position_status==='out_of_frame'){pending.position_status='uncertain';$('position').value='uncertain';}draw();if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);}};
canvas.onpointercancel = ()=>{drag=null;};
['playerId','team','playerNotes'].forEach(id=>$(id).oninput=()=>{formDirty=true;});
$('occlusion').onchange=()=>{pending.occlusion=$('occlusion').value;if(pending.occlusion==='full'){pending.bbox=null;pending.footpoint=null;pending.position_status='occluded';$('position').value='occluded';}formDirty=true;draw();};
$('position').onchange=()=>{pending.position_status=$('position').value;if(pending.position_status!=='visible')pending.footpoint=null;if(pending.position_status==='out_of_frame'){pending.bbox=null;pending.occlusion='none';$('occlusion').value='none';}formDirty=true;draw();};
$('clearFoot').onclick=()=>{pending.footpoint=null;pending.position_status='uncertain';$('position').value='uncertain';formDirty=true;draw();};
$('showProposals').onchange=draw;
$('newPlayer').onclick=()=>{if(discardForm())fill(emptyPlayer());};
$('copyPrevious').onclick=()=>{
  if(busy || !frame || data.saved.frames[String(frame.frame_index)] || included.length)return;
  const index=data.draft.frames.indexOf(frame);
  if(index<1)return;
  const previous=data.saved.frames[String(data.draft.frames[index-1].frame_index)];
  if(!previous)return;
  included=clone(previous.players).map(p=>({...p,origin_proposal_id:null}));
  proposalExposure = proposalExposure || !!previous.proposal_displayed || previous.players.some(p=>p.origin_proposal_id);
  dirty=true;fill(emptyPlayer());listPlayers();
  message('Copied previous labels as a starting point. Check and correct every box and visibility before saving this frame.');
};
$('apply').onclick=()=>{
  const person={...clone(pending),player_id:$('playerId').value.trim(),team_id:$('team').value,occlusion:$('occlusion').value,position_status:$('position').value,notes:$('playerNotes').value};
  if(!/^[A-Za-z0-9_-]{1,60}$/.test(person.player_id)){message('Use a stable player ID such as near_p01, with letters, numbers, underscores or hyphens.');return;}
  if(included.some((p,i)=>i!==selected && p.player_id===person.player_id)){message('This player ID already exists on this frame.');return;}
  if(person.position_status==='out_of_frame' && (person.bbox || person.footpoint || person.occlusion!=='none')){message('An out-of-frame player has no box, footpoint, or occlusion.');return;}
  if(person.occlusion!=='full' && person.position_status!=='out_of_frame' && !person.bbox && !(person.occlusion==='partial' && person.position_status==='occluded')){message('Draw a valid visible-body box, or mark partial occlusion with feet occluded.');return;}
  if(person.bbox && (person.bbox[2]<=person.bbox[0] || person.bbox[3]<=person.bbox[1])){message('Draw a valid visible-body box.');return;}
  if(person.position_status==='visible' && !person.footpoint){message('Click the visible floor-contact point, or mark it unobservable.');return;}
  if(person.occlusion==='full' && person.position_status==='visible'){message('A fully occluded player cannot have a visible contact point.');return;}
  if(selected<0){included.push(person);selected=included.length-1;}else included[selected]=person;
  if(![...$('knownIds').options].some(option=>option.value===person.player_id)){$('knownIds').appendChild(new Option(person.player_id,person.player_id));}
  dirty=true;fill(emptyPlayer());listPlayers();
  mode='select';document.querySelectorAll('[data-mode]').forEach(button=>button.classList.toggle('active',button.dataset.mode==='select'));
  message('Player included. Select the next person.');
};
document.addEventListener('keydown',event=>{
  const key=event.key.toLowerCase();
  if(!['q','w'].includes(key) || event.repeat || event.altKey || event.ctrlKey || event.metaKey || busy)return;
  const target=event.target;
  if(target instanceof HTMLElement && (target.isContentEditable ||
      (['INPUT','TEXTAREA','SELECT'].includes(target.tagName) &&
       !(target=== $('playerId') && target.value.trim()))))return;
  event.preventDefault();
  if(key==='q'){$('apply').click();return;}
  mode='foot';document.querySelectorAll('[data-mode]').forEach(button=>button.classList.toggle('active',button.dataset.mode==='foot'));
  message('Click the visible floor-contact point for the current player.');
});
$('remove').onclick=()=>{if(selected<0)return;included.splice(selected,1);dirty=true;fill(emptyPlayer());listPlayers();};
async function loadFrame(index) {
  if(busy || !Number.isInteger(index) || index<0 || index>=data.draft.frames.length)return;
  if((dirty || formDirty) && !confirm('Discard unsaved changes on this frame?')){$('frameSelect').value=data.draft.frames.indexOf(frame);return;}
  const token=++requestIndex;block(true);message('Loading original source frame…');
  try {
    const next=data.draft.frames[index], response=await fetch(`${api}/frame/${next.frame_index}`);
    if(!response.ok)throw new Error('Could not decode source frame');
    const url=URL.createObjectURL(await response.blob()), nextImage=new Image();nextImage.src=url;
    try{await nextImage.decode();}finally{URL.revokeObjectURL(url);}
    if(data.assisted_proposals_available){
      const suggestions=await fetch(`${endpointBase}/proposals/${next.frame_index}`);
      if(!suggestions.ok)throw new Error('Could not load frozen box suggestions');
      next.proposals=(await suggestions.json()).proposals;
    }
    if(token!==requestIndex)return;
    frame=next;image=nextImage;canvas.width=data.source.camera.width;canvas.height=data.source.camera.height;
    const saved=data.saved.frames[String(frame.frame_index)];
    const prefill=!saved && side==='near' ? (frame.suggested_players || []) : [];
    included=clone(saved?.players || prefill);
    proposalExposure=!!saved?.proposal_displayed;
    $('complete').checked=saved?.all_players_accounted_for || false;$('frameNotes').value=saved?.notes || '';
    if(saved)$('annotator').value=saved.annotator_id;
    $('frameSelect').value=index;$('frameState').textContent=saved?(frameReviewed(frame.frame_index)?'Saved — reviewed':data.draft.annotation_mode==='honours_sample_unverified_detector_suggestions' && saved.all_players_accounted_for?'Saved — six players accounted for':'Saved — unreviewed'):prefill.length?'Suggested IDs — unsaved':'Not annotated';
    dirty=false;formDirty=false;fill(emptyPlayer());listPlayers();
    $('copyPrevious').hidden=data.draft.annotation_mode!=='independent_manual_no_detector_proposals' || index<1 || !!saved || !data.saved.frames[String(data.draft.frames[index-1]?.frame_index)];
    if(prefill.length){
      const unresolved=frame.unresolved_player_ids?.join(', ');
      const noBox=frame.no_box_player_ids?.join(', ');
      message(`Suggested IDs filled for ${prefill.length} players. Check boxes and identities, then mark foot contacts.${unresolved?` Add unresolved IDs ${unresolved}.`:''}${noBox?` Check no-box slots ${noBox}; draw a box when a player is visible enough.`:''} Suggestions are unsaved until you save this frame.`);
    }
    else message(data.assisted_proposals_available || data.draft.annotation_mode==='honours_sample_unverified_detector_suggestions'?'Grey boxes are unverified suggestions. Click one, set a player ID, correct its box, and include it. Draw missing players yourself; check all six on this side.':'Draw or copy and correct all six players on this side. Use Out of frame or full occlusion where supported by the source.');
  }catch(error){message(error.message);}finally{block(false);}
}
$('prev').onclick=()=>loadFrame(data.draft.frames.indexOf(frame)-1);
$('next').onclick=()=>loadFrame(data.draft.frames.indexOf(frame)+1);
$('frameSelect').onchange=()=>loadFrame(Number($('frameSelect').value));
['annotator','complete','frameNotes'].forEach(id=>$(id).oninput=()=>{dirty=true;});
$('saveFrame').onclick=async()=>{
  if(busy)return;
  if(data.stale){message('Rally boundaries changed. Reconcile the frame schedule before saving labels.');return;}
  if(formDirty){message('Include/update the current player before saving the frame, or use New player to discard that edit.');return;}
  if(['independent_manual_no_detector_proposals','honours_sample_unverified_detector_suggestions'].includes(data.draft.annotation_mode) && $('complete').checked && included.length!==6){message('Account for all six target players, including fully occluded players with no box, before marking this frame complete.');return;}
  const annotator=$('annotator').value.trim();if(!annotator){message('Enter your annotator code.');return;}
  block(true);
  try {
    const response=await fetch(`${endpointBase}/frames/${frame.frame_index}?side=${side}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({annotator_id:annotator,all_players_accounted_for:$('complete').checked,proposal_displayed:proposalExposure,notes:$('frameNotes').value,players:included})});
    const saved=await response.json();if(!response.ok)throw new Error(typeof saved.detail==='string'?saved.detail:JSON.stringify(saved.detail));
    data.review_attestation=null;
    data.saved.frames[String(frame.frame_index)]=saved;dirty=false;$('frameState').textContent=data.draft.annotation_mode==='honours_sample_unverified_detector_suggestions' && saved.all_players_accounted_for?'Saved — six players accounted for':'Saved — unreviewed';updateDenseProgress();
    $('reviewNote').textContent=data.draft.annotation_mode==='honours_sample_unverified_detector_suggestions'?'Annotation complete on this frame. Final metric use depends on phase and court validation.':'Saved labels need review. Completeness records and edit history stay in the project.';
    message(data.draft.annotation_mode==='honours_sample_unverified_detector_suggestions'?'Frame saved. Your six-player annotation is complete on this frame.':'Frame saved in the project. Labels remain unreviewed.');
  }catch(error){message(error.message);}finally{block(false);}
};
$('refreshDrafts').onclick=async()=>{
  if(busy)return;
  if((dirty||formDirty)&&!confirm('Discard unsaved edits and refresh the frame schedule for the corrected boundaries?'))return;
  block(true);message('Refreshing the frame schedule for the corrected rally boundaries…');
  try{
    const response=await fetch(`${endpointBase}/refresh`,{method:'POST'});
    const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:JSON.stringify(result.detail));
    dirty=false;formDirty=false;location.reload();
  }catch(error){message(error.message);block(false);}
};
$('denseStart').onclick=()=>{if(denseIndices.length)loadFrame(denseIndices[0]);};
$('nextUnsaved').onclick=()=>{
  const current=data.draft.frames.indexOf(frame);
  const next=denseIndices.find(i=>i>current && !data.saved.frames[String(data.draft.frames[i].frame_index)])
    ?? denseIndices.find(i=>!data.saved.frames[String(data.draft.frames[i].frame_index)]);
  if(next===undefined){message('All dense frames have been saved; check completeness and review each label.');return;}
  loadFrame(next);
};
window.addEventListener('beforeunload',event=>{if(dirty||formDirty){event.preventDefault();event.returnValue='';}});
(async()=>{
  block(true);
  try {
    const response=await fetch(endpoint);data=await response.json();if(!response.ok)throw new Error(data.detail);
    $('boundaryLink').href=rally.startsWith('hs_')?'/honours-sample':`/?match=${encodeURIComponent(match)}`;$('export').href=`${endpointBase}/export.csv?side=${side}`;
    const heldout=data.draft.annotation_mode==='independent_manual_no_detector_proposals';
    const honoursSample=data.draft.annotation_mode==='honours_sample_unverified_detector_suggestions';
    $('heading').textContent=`${rally} · ${heldout?(side==='far'?'far-side team':'near-side team'):'target team'} · ${data.draft.frames.length} ${heldout?'consecutive':'sparse'} frames · ${data.source.camera.width} × ${data.source.camera.height}`;
    if(heldout){$('instructions').textContent=`${side}-side team review: account for all six players on each frame. Grey boxes are unverified tracker suggestions; correct them and draw any missing players. Keep IDs stable. A player outside the image has no box.`;$('canvasHelp').textContent='Grey = unverified suggestions, green = included labels, yellow = current edit. Draw a box by dragging. Floor contact points are optional unless marked Visible contact.';$('showProposals').checked=!!data.assisted_proposals_available;$('showProposals').closest('label').hidden=!data.assisted_proposals_available;$('copyPrevious').hidden=false;$('refreshDrafts').textContent='Refresh frame schedule for corrected rally boundaries';const switchSide=side==='far'?'near':'far';$('sideSwitch').href=`/players?match=${encodeURIComponent(match)}&rally=${encodeURIComponent(rally)}&side=${switchSide}&frame=${data.dense_review_window?.first_frame ?? data.draft.start_frame}`;$('sideSwitch').textContent=`Review ${switchSide} team instead`;$('sideSwitch').hidden=false;}
    if(honoursSample){$('instructions').textContent='Frozen sample, near-side team only: grey boxes are unverified detector suggestions. Assign stable IDs, correct boxes, click visible floor contacts, and account for all six players before marking a frame complete. These navigation frames may fall outside live play until the rally boundary is checked.';$('showProposals').checked=true;$('heading').textContent=`${data.draft.sample_point_id} · near-side review · ${data.draft.frames.length} navigation frames`;$('boundaryLink').textContent='Back to frozen sample';}
    $('boundaryNotice').textContent=data.stale?'Boundary changes detected: saving is blocked until the frame schedule is reconciled.':data.boundary.boundary_status==='checked_by_annotator'?'Boundaries checked by an annotator; independent review remains pending.':'Rally boundaries are still draft estimates. Labels made now are provisional and will need reconciliation if boundaries change.';
    $('reviewNote').textContent=data.review_attestation?'These saved player labels were checked by a reviewer. Editing any frame requires a new review.':honoursSample?'Saved six-player annotations are complete where checked. Final metric use depends on phase and court validation.':'Saved labels need review. Completeness records and edit history stay in the project.';
    $('refreshDrafts').hidden=!data.stale || Object.keys(data.saved.frames).length>0;
    data.draft.frames.forEach((f,i)=>{const option=document.createElement('option');option.value=i;option.textContent=`${i+1}/${data.draft.frames.length} · frame ${f.frame_index} · ${f.time_s.toFixed(2)} s`;$('frameSelect').appendChild(option);});
    const windowRange=data.dense_review_window;
    if(heldout && windowRange && Number.isInteger(windowRange.first_frame) && Number.isInteger(windowRange.last_frame)) {
      denseIndices=data.draft.frames.map((f,i)=>f.frame_index>=windowRange.first_frame && f.frame_index<=windowRange.last_frame?i:-1).filter(i=>i>=0);
      $('denseStart').hidden=!denseIndices.length;$('nextUnsaved').hidden=!denseIndices.length;
      updateDenseProgress();
    }
    const ids=new Set(Object.values(data.saved.frames).flatMap(f=>f.players.map(p=>p.player_id)));
    ids.forEach(id=>{const option=document.createElement('option');option.value=id;$('knownIds').appendChild(option);});
    const requested=Number(query.get('frame'));
    const requestedIndex=query.has('frame') && Number.isInteger(requested)?data.draft.frames.findIndex(f=>f.frame_index===requested):-1;
    block(false);await loadFrame(requestedIndex>=0?requestedIndex:0);
  }catch(error){message(error.message);block(true);}
})();
