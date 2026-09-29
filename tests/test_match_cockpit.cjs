const {test}=require('node:test');
const assert=require('node:assert/strict');
const load=()=>import('../app/static/match/cockpit.js').then(()=>globalThis.FootyCockpit);
const event=(sequence,minute,kind,actor_id='career_player')=>({sequence,minute,kind,visual:{kind,actor_id}});
test('starter minutes stop at substitution and duplicate events have no effect',async()=>{
 const c=await load();const s=c.createPlayerState('starter');
 c.advancePlayer(s,event(1,30,'moment'));assert.equal(s.status,'ON PITCH');assert.equal(s.minutes,30);
 c.advancePlayer(s,event(2,64,'substitution_off'));c.advancePlayer(s,event(3,90,'full_time'));
 assert.equal(s.status,'SUBBED OFF');assert.equal(s.minutes,64);assert.equal(s.exit,64);assert.equal(s.finished,true);
 c.advancePlayer(s,event(2,80,'substitution_off'));assert.equal(s.exit,64);
});
test('bench stays unrevealed until introduction; a later removal stops minutes',async()=>{
 const c=await load(),s=c.createPlayerState('substitute');
 c.advancePlayer(s,event(1,45,'moment'));assert.equal(s.status,'BENCH');assert.equal(s.minutes,0);
 c.advancePlayer(s,event(2,61,'substitution_on'));c.advancePlayer(s,event(3,70,'moment'));
 assert.equal(s.status,'ON PITCH');assert.equal(s.enter,61);assert.equal(s.minutes,9);
 c.advancePlayer(s,event(4,78,'substitution_off'));c.advancePlayer(s,event(5,90,'full_time'));assert.equal(s.minutes,17);
});
test('opponent substitutions do not change career state; career red card does',async()=>{
 const c=await load(),s=c.createPlayerState('starter');
 c.advancePlayer(s,event(1,50,'substitution_off','away_cm'));assert.equal(s.status,'ON PITCH');
 c.advancePlayer(s,event(2,60,'red_card'));c.advancePlayer(s,event(3,85,'moment'));assert.equal(s.status,'SENT OFF');assert.equal(s.minutes,60);
});
test('unavailable player remains unavailable and goal/card labels are explicit',async()=>{
 const c=await load(),s=c.createPlayerState('injured');c.advancePlayer(s,event(1,90,'full_time'));assert.equal(s.status,'UNAVAILABLE');assert.equal(s.minutes,0);
 assert.equal(c.eventType({kind:'goal_for'}),'GOAL');assert.equal(c.eventType(event(2,20,'yellow_card')),'YELLOW CARD');
});
test('feed follows near bottom, preserves reading position, and resumes explicitly',async()=>{
 const c=await load(),f=c.createFollowState();
 f.scroll(800,200,1000);assert.equal(f.following,true);
 f.scroll(350,200,1000);assert.equal(f.following,false);assert.equal(f.append(),false);assert.equal(f.unread,1);
 f.resume();assert.equal(f.following,true);assert.equal(f.unread,0);assert.equal(f.append(),true);
});
test('injury treatment alone does not invent a substitution',async()=>{
 const c=await load(),s=c.createPlayerState('starter');
 c.advancePlayer(s,event(1,30,'injury'));c.advancePlayer(s,event(2,45,'moment'));
 assert.equal(s.status,'ON PITCH');assert.equal(s.minutes,45);assert.equal(s.exit,null);
});
test('mounted cockpit preserves history, updates revealed facts and opens report only on request',async()=>{
 const c=await load();
 // Small DOM adapter for behavior, not a browser/layout substitute.
 class Node {
  constructor(){this.children=[];this.listeners={};this.attrs={};this.dataset={};this.textContent='';this.hidden=false;this.disabled=false;this.scrollTop=0;this.clientHeight=200;this.scrollHeight=1000;this.classes=new Set();this.classList={add:x=>this.classes.add(x)};}
  append(...nodes){this.children.push(...nodes);} prepend(node){this.children.unshift(node);}
  setAttribute(k,v){this.attrs[k]=v;} getAttribute(k){return this.attrs[k];}
  addEventListener(k,fn){this.listeners[k]=fn;} fire(k,e={}){this.listeners[k]?.(e);}
  querySelector(k){return this.children.find(x=>x.tag===k);}
  querySelectorAll(){return this.children;}
  focus(){this.focused=true;} showModal(){this.open=true;} close(){this.open=false;this.fire('close');}
 }
 const ids={};for(const id of ['cockpit-data','match-timeline','jump-to-live','match-report-dialog','open-match-report','close-match-report','squad-tabs','squad-own','squad-bench','squad-opponent','live-player-state','live-player-minutes','live-player-timing','live-player-goals','live-player-assists','live-player-cards','live-player-fitness','live-player-rating','cockpit-latest-type','cockpit-latest-text','player-briefing'])ids[id]=new Node();
 const player={actor_id:'career_player',display_name:'<script>unsafe</script>',shirt_number:17,role:'CAM',team:'away'};
 ids['cockpit-data'].textContent=JSON.stringify({player,selection:'substitute',squads:{home:[],away:[]}});
 for(const side of ['own','bench','opponent']){const list=new Node();list.tag='ul';ids['squad-'+side].append(list);const tab=new Node();tab.setAttribute('aria-controls','squad-'+side);ids['squad-tabs'].append(tab);}
 const speed=new Node();ids['open-match-report'].disabled=true;
 global.document={getElementById:id=>ids[id],createElement:tag=>{const node=new Node();node.tag=tag;return node;},querySelectorAll:selector=>selector==='[data-match-speed]'?[speed]:[]};
 try{
  const cockpit=c.mount();assert.equal(ids['live-player-state'].textContent,'BENCH');
  assert.equal(ids['squad-bench'].children[0].children[0].children[1].textContent,player.display_name,'Name is assigned as text, never HTML');
  ids['match-timeline'].scrollTop=200;ids['match-timeline'].fire('scroll');
  const row=new Node(),copy=new Node();copy.tag='p';row.append(copy);
  cockpit.event({...event(1,61,'substitution_on'),text:'Your player enters.'},row);
  assert.equal(ids['live-player-state'].textContent,'ON PITCH');assert.equal(ids['match-timeline'].scrollTop,200);
  assert.equal(ids['jump-to-live'].hidden,false);assert.ok(row.classes.has('is-career-event'));
  assert.equal(ids['live-player-rating'].textContent,'');assert.equal(ids['open-match-report'].disabled,true);
  ids['squad-tabs'].children[0].fire('keydown',{key:'ArrowRight',preventDefault(){}});
  assert.equal(ids['squad-tabs'].children[1].getAttribute('aria-selected'),'true');assert.equal(ids['squad-own'].hidden,true);
  cockpit.finish({report:{minutes:29,goals:1,assists:2,yellow_cards:1,red_cards:0,rating:8.1,fitness_after:76}});
  assert.equal(ids['live-player-minutes'].textContent,'29′');assert.equal(ids['live-player-rating'].textContent,8.1);
  assert.equal(ids['live-player-cards'].textContent,'1Y / 0R');assert.equal(ids['live-player-state'].textContent,'FULL TIME');
  assert.equal(ids['match-report-dialog'].open,undefined);assert.equal(speed.disabled,true);
  ids['open-match-report'].fire('click');assert.equal(ids['match-report-dialog'].open,true);
  ids['close-match-report'].fire('click');assert.equal(ids['open-match-report'].focused,true);
  ids['jump-to-live'].fire('click');assert.equal(ids['match-timeline'].scrollTop,1000);assert.equal(ids['jump-to-live'].hidden,true);
 }finally{delete global.document;}
});
