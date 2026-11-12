'use strict';
const API='/api/u5/s3p34-remaining-rally-review';
const mode=new URLSearchParams(window.location.search).get('mode')==='full'?'full':'focused';
const keys=['28','12','15','7','19','21'];
const $=id=>document.getElementById(id);
let state, index=0, image, markKey=null, boxes=null, previewShown=false;
const choices={identity_status:[['digit_confirmed','Digit confirmed'],['sequence_consistent','Same by sequence'],['uncertain','Uncertain'],['not_visible','Not visible']],
 ground_status:[['grounded','Grounded'],['airborne','Airborne'],['feet_occluded','Feet occluded'],['uncertain','Uncertain'],['not_visible','Not visible']],
 candidate_alignment:[['same_player','Same player'],['wrong_player','Wrong player'],['no_box','No box'],['uncertain','Uncertain']],
 floor_alignment:[['plausible','Plausible proxy'],['implausible','Implausible proxy'],['not_applicable','Not applicable'],['uncertain','Uncertain']]};
function status(message,bad=false){$('status').textContent=message;$('status').style.color=bad?'#ff9e9e':'#aeeab6'}
const fieldNames={identity_status:'Identity',ground_status:'State',candidate_alignment:'Box',floor_alignment:'Floor'};
function select(name,options,value){const label=document.createElement('label');label.textContent=fieldNames[name]||name;
 const input=document.createElement('select');input.dataset.field=name;
 for(const [key,title] of options){const option=document.createElement('option');option.value=key;option.textContent=title;input.append(option)}
 input.value=value;label.append(input);return label}
function card(key,fields){const div=document.createElement('div');div.className='card';div.dataset.key=key;
 const title=document.createElement('strong');title.textContent=`Player ${keys.indexOf(key)+1} · UCLA #${key} (provisional)`;div.append(title,...fields);return div}
function field(node,name){return node.querySelector(`[data-field="${name}"]`)}
function sourceCard(key,saved){const node=card(key,[select('identity_status',choices.identity_status,saved?.identity_status||'sequence_consistent'),
 select('ground_status',choices.ground_status,saved?.ground_status||'grounded')]);
 const extra=document.createElement('details');extra.className='optional';
 const summary=document.createElement('summary');summary.textContent=saved?.shoe_x_px!=null?'Shoe point saved / note':'Optional shoe point / note';extra.append(summary);
 const point=document.createElement('div');point.className='point';point.dataset.point='';
 point.textContent=saved?.shoe_x_px!=null?`Shoe: ${saved.shoe_x_px}, ${saved.shoe_y_px}`:'No shoe point';extra.append(point);
 const buttons=document.createElement('div');const mark=document.createElement('button');mark.textContent='Click shoe point';
 mark.onclick=()=>{markKey=key;boxes=null;paint();status(`Click the shoe or floor contact for player ${keys.indexOf(key)+1}; boxes hidden for the click`)};
 const clear=document.createElement('button');clear.textContent='Clear';clear.onclick=()=>{node.dataset.x='';node.dataset.y='';point.textContent='No shoe point';paint()};
 buttons.append(mark,clear);extra.append(buttons);
 node.dataset.x=saved?.shoe_x_px??'';node.dataset.y=saved?.shoe_y_px??'';
 const note=document.createElement('label');note.textContent='Note';const input=document.createElement('input');input.dataset.field='note';input.value=saved?.note||'';note.append(input);extra.append(note);node.append(extra);
 if(saved?.note)extra.open=true;
 field(node,'ground_status').onchange=()=>{if(field(node,'ground_status').value!=='grounded'){node.dataset.x='';node.dataset.y='';point.textContent='No shoe point';paint()}};
 field(node,'identity_status').onchange=()=>{if(field(node,'identity_status').value==='not_visible')field(node,'ground_status').value='not_visible'};
 field(node,'ground_status').addEventListener('change',()=>{if(field(node,'ground_status').value==='not_visible')field(node,'identity_status').value='not_visible'});
 return node}
function pairedCard(key,saved,box,source){const has=!!box;
 const node=card(key,[select('candidate_alignment',choices.candidate_alignment,saved?.candidate_alignment||(has?'same_player':'no_box')),
 select('floor_alignment',choices.floor_alignment,saved?.floor_alignment||(has&&source.ground_status==='grounded'?'plausible':'not_applicable'))]);
 const extra=document.createElement('details');extra.className='optional';const summary=document.createElement('summary');summary.textContent='Optional note';extra.append(summary);
 const note=document.createElement('label');note.textContent='Note';const input=document.createElement('input');input.dataset.field='note';input.value=saved?.note||'';note.append(input);extra.append(note);node.append(extra);if(saved?.note)extra.open=true;
 const id=document.createElement('div');id.className='point';id.textContent=has?`Raw ID ${box.raw_track_id}; box ${box.bbox_px.map(Math.round).join(', ')}`:'No jersey-keyed candidate box';node.append(id);
 field(node,'candidate_alignment').onchange=()=>{if(field(node,'candidate_alignment').value!=='same_player')field(node,'floor_alignment').value='not_applicable'};
 return node}
function paint(){const canvas=$('frameCanvas'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,1280,720);if(image)ctx.drawImage(image,0,0,1280,720);
 if(boxes){for(const [i,key] of keys.entries()){const b=boxes[key];if(!b)continue;const [x1,y1,x2,y2]=b.bbox_px;
 ctx.lineWidth=3;ctx.strokeStyle='#ffffff';ctx.strokeRect(x1,y1,x2-x1,y2-y1);ctx.fillStyle='#111';ctx.fillRect(x1,Math.max(0,y1-30),90,28);ctx.fillStyle='#ffe466';ctx.font='bold 21px system-ui';ctx.fillText(`${i+1} / #${key}`,x1+5,Math.max(23,y1-8))}}
 for(const [i,key] of keys.entries()){const node=$(`sourceCards`).querySelector(`[data-key="${key}"]`);if(!node||!node.dataset.x)continue;
 const x=Number(node.dataset.x),y=Number(node.dataset.y);ctx.fillStyle='#ff416e';ctx.beginPath();ctx.arc(x,y,7,0,2*Math.PI);ctx.fill();ctx.fillStyle='#fff';ctx.font='bold 18px system-ui';ctx.fillText(String(i+1),x+9,y-7)}}
function getFrame(){return state.frames[index]}
function record(){return state.draft.frames[String(getFrame().frame)]||{}}
function advanceUnfinished(){const next=state.frames.findIndex((frame,i)=>i>index&&!state.draft.frames[String(frame.frame)]?.paired);
 if(next>=0){index=next;show();return}
 const first=state.frames.findIndex(frame=>!state.draft.frames[String(frame.frame)]?.paired);
 if(first>=0){index=first;show();return}
 show();status('Every frame is saved; export the full packet')}
async function show(){const frame=getFrame(),saved=record();boxes=frame.numbered_boxes;previewShown=true;markKey=null;
 $('frameLabel').textContent=`Frame ${frame.frame} (${index+1}/${state.frames.length})`;
 $('progress').textContent=`${state.frames.filter(f=>state.draft.frames[String(f.frame)]?.paired).length}/${state.frames.length} complete`;
 $('reviewer').value=state.draft.reviewer_code||$('reviewer').value;
 $('sourceCards').replaceChildren(...keys.map((k,i)=>sourceCard(k,saved.source?.[i])));
 $('sourceSection').hidden=!!saved.source;
 $('pairedSection').hidden=!saved.source;
 $('toggleBoxes').textContent='Hide numbered boxes';
 if(saved.source)$('pairedCards').replaceChildren(...keys.map((k,i)=>pairedCard(k,saved.paired?.[i],boxes?.[k],saved.source[i])));
 image=new Image();image.onload=paint;image.src=frame.image_url;paint();
 if(state.completed_csv_exists){$('saveSource').disabled=true;$('savePaired').disabled=true;$('saveDefaults').disabled=true;status('Completed review is frozen')}else status(saved.paired?'Both stages saved':saved.source?'Source saved; compare boxes':'Review source and numbered boxes; correct any exceptions')}
async function call(url,method,data){const response=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const body=await response.json();if(!response.ok){const detail=Array.isArray(body.detail)?body.detail.map(item=>`${item.loc?.join('.')}: ${item.msg}`).join('; '):body.detail;
 throw Error(detail||`HTTP ${response.status}`)}return body}
function sourceRows(){return [...$('sourceCards').children].map(node=>({jersey:node.dataset.key,
 identity_status:field(node,'identity_status').value,ground_status:field(node,'ground_status').value,
 shoe_x_px:node.dataset.x===''?null:Number(node.dataset.x),shoe_y_px:node.dataset.y===''?null:Number(node.dataset.y),
 note:field(node,'note').value}))}
function pairedRows(){return [...$('pairedCards').children].map(node=>({jersey:node.dataset.key,
 candidate_alignment:field(node,'candidate_alignment').value,floor_alignment:field(node,'floor_alignment').value,
 note:field(node,'note').value}))}
$('frameCanvas').onclick=event=>{if(!markKey||boxes)return;const rect=$('frameCanvas').getBoundingClientRect();
 const x=Math.round((event.clientX-rect.left)*1280/rect.width*10)/10,y=Math.round((event.clientY-rect.top)*720/rect.height*10)/10;
 const node=$('sourceCards').querySelector(`[data-key="${markKey}"]`);node.dataset.x=x;node.dataset.y=y;
 node.querySelector('[data-point]').textContent=`Shoe: ${x}, ${y}`;paint()};
$('saveSource').onclick=async()=>{try{const frame=getFrame().frame;const out=await call(`${API}/${frame}/source`,'PUT',{
 expected_revision:state.draft.revision,reviewer_code:$('reviewer').value.trim(),checked_source_frame:true,
 candidate_boxes_shown_before_source:previewShown,rows:sourceRows()});
 state.draft=out.draft;state.frames[index].numbered_boxes=out.numbered_boxes;show()}catch(error){status(`Save failed: ${error.message}`,true)}};
$('savePaired').onclick=async()=>{try{const frame=getFrame().frame;const out=await call(`${API}/${frame}/paired`,'PUT',{
 expected_revision:state.draft.revision,checked_source_and_boxes:true,rows:pairedRows()});
 state.draft=out.draft;advanceUnfinished()}catch(error){status(`Save failed: ${error.message}`,true)}};
$('saveDefaults').onclick=async()=>{const button=$('saveDefaults');try{
 const frame=getFrame(),source=sourceRows();
 if(source.some(row=>!['digit_confirmed','sequence_consistent'].includes(row.identity_status)||
     !['grounded','airborne'].includes(row.ground_status))){
   status('Use the two-stage review for uncertain, occluded or invisible players',true);return}
 if(source.some(row=>row.shoe_x_px!=null&&row.ground_status!=='grounded')){
   status('Clear shoe marks on airborne players before saving',true);return}
 button.disabled=true;status('Saving reviewed source and candidate defaults…');
 const first=await call(`${API}/${frame.frame}/source`,'PUT',{
   expected_revision:state.draft.revision,reviewer_code:$('reviewer').value.trim(),checked_source_frame:true,
   candidate_boxes_shown_before_source:previewShown,rows:source});
 state.draft=first.draft;
 const paired=source.map(row=>{const has=!!frame.numbered_boxes?.[row.jersey];
   return {jersey:row.jersey,candidate_alignment:has?'same_player':'no_box',
     floor_alignment:has&&row.ground_status==='grounded'?'plausible':'not_applicable',note:''}});
 const second=await call(`${API}/${frame.frame}/paired`,'PUT',{
   expected_revision:state.draft.revision,checked_source_and_boxes:true,rows:paired});
 state.draft=second.draft;advanceUnfinished();
 }catch(error){show();status(`Save failed: ${error.message}`,true)}finally{button.disabled=false}};
$('editSource').onclick=()=>{$('sourceSection').hidden=false;$('pairedSection').hidden=true;paint();status('Editing source decisions; save to update this frame')};
$('toggleBoxes').onclick=()=>{boxes=boxes?null:getFrame().numbered_boxes;markKey=null;$('toggleBoxes').textContent=boxes?'Hide numbered boxes':'Show numbered boxes';paint()};
$('prev').onclick=()=>{if(index>0){index--;show()}};$('next').onclick=()=>{if(index<state.frames.length-1){index++;show()}};
$('nextUnfinished').onclick=advanceUnfinished;
document.addEventListener('keydown',event=>{if(event.altKey||event.ctrlKey||event.metaKey||event.repeat)return;
 const tag=event.target?.tagName;if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(tag))return;
 if(event.code==='Space'){event.preventDefault();($('sourceSection').hidden?$('savePaired'):$('saveSource')).click()}
 if(event.key==='ArrowLeft')$('prev').click();if(event.key==='ArrowRight')$('next').click()});
$('export').onclick=async()=>{try{
 if(mode==='full'&&state.draft.frames['36112']?.source?.find(row=>row.jersey==='15')?.ground_status==='grounded'){
   status('Review frame 36112 before export: #15 appears airborne in the prior source audit',true);return}
 const out=await call(`${API}/${mode==='focused'?'export-focused':'export'}`,'POST',{});
 status(`${out.rows} rows exported to ${out.completed_csv}`);state.completed_csv_exists=true;show()
 }catch(error){status(`Export failed: ${error.message}`,true)}};
fetch(`${API}?mode=${mode}`).then(r=>r.json()).then(data=>{state=data;
 const requested=Number(new URLSearchParams(window.location.search).get('frame'));
 index=Number.isInteger(requested)&&requested>0?state.frames.findIndex(frame=>frame.frame===requested):-1;
 if(index<0)index=state.frames.findIndex(frame=>!state.draft.frames[String(frame.frame)]?.paired);
 if(index<0)index=state.frames.length-1;show()}).catch(error=>status(`Load failed: ${error.message}`,true));
