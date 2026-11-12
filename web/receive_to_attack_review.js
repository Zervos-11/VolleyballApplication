'use strict';
const $=id=>document.getElementById(id), API='/api/receive-to-attack-review';
let state,position=0,frame=0,mark={reception:[null,null],attack:[null,null]},timer;
function status(message,bad=false){$('status').textContent=message;$('status').style.color=bad?'#ffabab':'#b5e7ba'}
function chosen(){return state.protocol.cases[position]}
function key(){const c=chosen();return `${c.match_id}/${c.rally_id}`}
function showMark(){const fmt=v=>v[0]===null?'unmarked':`${v[0]} to ${v[1]===null?'?':v[1]}`;
 $('receptionValue').textContent=fmt(mark.reception);$('attackValue').textContent=fmt(mark.attack)}
function setFrame(value){const [lo,hi]=chosen().provisional_interval_inclusive;
 frame=Math.max(lo,Math.min(hi,Number(value)));$('slider').value=frame;$('frame').value=frame;
 $('imageStatus').textContent=`Source frame ${frame} | ${(frame/chosen().fps).toFixed(3)} s`;
 $('fullFrame').href=`${API}/image/${key()}/${frame}`;
 clearTimeout(timer);timer=setTimeout(()=>{$('sourceFrame').src=`${API}/image/${key()}/${frame}`},90)}
function showCase(){const c=chosen(),[lo,hi]=c.provisional_interval_inclusive,saved=state.draft.cases[key()];
 $('rangeLabel').textContent=`Source frames ${lo} to ${hi}; boundaries provisional`;
 $('slider').min=lo;$('slider').max=hi;$('frame').min=lo;$('frame').max=hi;
 $('reviewer').value=saved?.reviewer_code||$('reviewer').value;
 $('receives').value=saved?.near_side_receives===true?'yes':saved?.near_side_receives===false?'no':'';
 $('absent').value=saved?.attack_absent===true?'yes':saved?.attack_absent===false?'no':'';
 $('note').value=saved?.note||'';$('sourceOnly').checked=!!saved?.source_only_before_metric;
 mark={reception:saved?.reception_contact_frame_interval?.slice()||[null,null],
 attack:saved?.first_near_side_attack_contact_frame_interval?.slice()||[null,null]};showMark();setFrame(lo);
 status(saved?'Saved event verdict loaded':'Mark the contacts from unboxed source frames')}
function booleanValue(id){return $(id).value==='yes'?true:$(id).value==='no'?false:null}
function interval(value){return value.every(Number.isInteger)?value:null}
function eventButton(id,kind,which){$(id).onclick=()=>{mark[kind][which]=frame;showMark()}}
eventButton('rStart','reception',0);eventButton('rEnd','reception',1);
eventButton('aStart','attack',0);eventButton('aEnd','attack',1);
$('rExact').onclick=()=>{mark.reception=[frame,frame];showMark()};
$('aExact').onclick=()=>{mark.attack=[frame,frame];showMark()};
for(const [id,offset] of [['back10',-10],['back1',-1],['forward1',1],['forward10',10]])
 $(id).onclick=()=>setFrame(frame+offset);
document.addEventListener('keydown',event=>{
 if(event.altKey||event.ctrlKey||event.metaKey||event.repeat)return;
 if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(event.target?.tagName))return;
 if(event.key==='ArrowLeft'){event.preventDefault();setFrame(frame-(event.shiftKey?10:1))}
 if(event.key==='ArrowRight'){event.preventDefault();setFrame(frame+(event.shiftKey?10:1))}
});
$('slider').oninput=()=>setFrame($('slider').value);$('frame').onchange=()=>setFrame($('frame').value);
$('case').onchange=()=>{position=Number($('case').value);showCase()};
async function send(url,body){const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await response.json();if(!response.ok)throw Error(data.detail||`HTTP ${response.status}`);return data}
$('save').onclick=async()=>{try{const c=chosen(),body={expected_revision:state.draft.revision,
 reviewer_code:$('reviewer').value.trim(),near_side_receives:booleanValue('receives'),
 reception_contact_frame_interval:interval(mark.reception),
 first_near_side_attack_contact_frame_interval:interval(mark.attack),
 attack_absent:booleanValue('absent'),source_only_before_metric:$('sourceOnly').checked,note:$('note').value};
 const response=await fetch(`${API}/${key()}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await response.json();if(!response.ok)throw Error(Array.isArray(data.detail)?data.detail.map(x=>x.msg).join('; '):data.detail||`HTTP ${response.status}`);
 state.draft=data.draft;status('Event verdict saved')}catch(error){status(`Save failed: ${error.message}`,true)}};
$('export').onclick=async()=>{try{const data=await send(`${API}/export`,{});status(`Exported ${data.cases} cases. Run scripts/analyze_receive_to_attack_transition.py`)}
 catch(error){status(`Export failed: ${error.message}`,true)}};
fetch(API).then(r=>r.json()).then(data=>{state=data;for(const [i,c] of data.protocol.cases.entries()){
 const option=document.createElement('option');option.value=i;option.textContent=`${c.match_id} / ${c.rally_id}`;$('case').append(option)}
 if(data.completed_exists){$('save').disabled=true;$('export').disabled=true}showCase()})
 .catch(error=>status(`Load failed: ${error.message}`,true));
