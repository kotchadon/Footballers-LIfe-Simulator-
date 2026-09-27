const {test}=require('node:test');const assert=require('node:assert/strict');
const plan=require('./fixtures/match-visual-plan.json');
const tactical=()=>import('../app/static/match/tactical-engine.js').then(m=>m.createTacticalEngine(structuredClone(plan)));
test('ball controller exposes visually distinct ground driven lofted switch and cross flights',async()=>{
 const {createBallController}=await import('../app/static/match/ball.js');const b=createBallController();
 const cases=[['groundPass','GROUND_PASS',.2],['drivenPass','DRIVEN_PASS',.5],['loftedPass','LOFTED_PASS',2.5],['longSwitch','LONG_SWITCH',4],['cross','CROSS',4]];
 for(const [method,state,max] of cases){b[method]({x:20,y:30},{x:70,y:60},{duration:1,maxHeight:max,targetActorId:'p'});assert.equal(b.state.state,state);b.update(.5,new Map());assert.ok(b.state.height>0&&b.state.height<=max);}
});
test('revealed goal builds from current ball through a connected route before shooting',async()=>{
 const t=await tactical(),before=structuredClone(t.getState());const shooter=before.actors.find(a=>a.team==='home'&&a.role==='ST');
 const duration=t.beginAuthoritativeBuildup({side:'home',actorId:shooter.actorId,ballStart:[3,97]});
 assert.ok(duration>.5);assert.ok(Math.hypot(t.getState().ball.x-before.ball.x,t.getState().ball.y-before.ball.y)<.01,'ball cannot jump to event metadata');
 let previous=new Map(before.actors.map(a=>[a.actorId,{x:a.x,y:a.y}]));
 for(let i=0;i<Math.ceil((duration+.5)*60);i++){
  const state=t.update(1/60);for(const actor of state.actors){const old=previous.get(actor.actorId),m=Math.hypot((actor.x-old.x)*1.05,(actor.y-old.y)*.68);assert.ok(m<.22,`actor teleported ${m}`);previous.set(actor.actorId,{x:actor.x,y:actor.y});}
 }
 assert.equal(t.isAuthoritativeBuildupReady(),true);assert.equal(t.getState().ball.ownerActorId,shooter.actorId);
 const shotStart={x:t.getState().ball.x,y:t.getState().ball.y};t.beginAuthoritativeEvent({side:'home',actorId:shooter.actorId,outcome:'GOAL',ballStart:[3,97],ballTarget:[98,50]});
 assert.ok(Math.hypot(t.getState().ball.x-shotStart.x,t.getState().ball.y-shotStart.y)<.01,'shot must start from live buildup');
});
test('normal possession cannot skip directly from buildup to final third',async()=>{
 const t=await tactical();let previous=t.getState().phase;
 for(let i=0;i<4000;i++){const next=t.update(1/60).phase;if(next!==previous){assert.notEqual(`${previous}>${next}`,'BUILDUP>FINAL_THIRD');previous=next;}}
});
test('presentation focus leads an active pass toward its target',async()=>{
 const t=await tactical(),shooter=t.getState().actors.find(a=>a.team==='home'&&a.role==='ST');t.beginAuthoritativeBuildup({side:'home',actorId:shooter.actorId});
 const state=t.getState();assert.ok(state.presentationFocus);const ball=state.ball,focus=state.presentationFocus;assert.ok(Math.hypot(focus.x-ball.x,focus.y-ball.y)>1);
});
test('ordinary passes and phase changes keep the ball continuous and mostly grounded',async()=>{
 const t=await tactical();let last=structuredClone(t.getState().ball),starts=[];
 for(let i=0;i<6000;i++){
  const b=t.update(1/60).ball;
  assert.ok(Math.hypot((b.x-last.x)*1.05,(b.y-last.y)*.68)<2.5,'ball jumped');
  if(b.action&&!last.action)starts.push(b.action.kind);
  last=structuredClone(b);
 }
 assert.ok(starts.length>15);assert.ok(starts.filter(k=>['GROUND_PASS','DRIVEN_PASS'].includes(k)).length>starts.length*.55);
});
test('shot from live possession does not relocate any actor or obey staging coordinates',async()=>{
 const t=await tactical(),before=structuredClone(t.getState());
 t.beginAuthoritativeEvent({side:'home',outcome:'GOAL',ballStart:[88,50]});
 assert.deepEqual(t.getState().actors.map(a=>[a.x,a.y]),before.actors.map(a=>[a.x,a.y]));
 assert.equal(t.getState().ball.x,before.ball.x);assert.equal(t.getState().ball.y,before.ball.y);
});
test('camera focus is bounded and cannot be dragged by a future event coordinate',async()=>{
 const {createCameraController}=await import('../app/static/match/camera.js');const c=createCameraController();
 c.emphasize('GOAL',{ball_target:[100,50]});
 for(let i=0;i<10;i++)c.update(1/60,{ball:{x:10,y:50},presentationFocus:{x:13,y:50}});
 assert.ok(c.getState().panX<0,'camera must follow current left-side possession');
});
test('in-flight buildup preserves its existing flight until reception and stays below the watchdog',async()=>{
 for(const side of ['home','away'])for(const warmup of [80,170,550]){
  const t=await tactical();for(let i=0;i<warmup;i++)t.update(1/60);
  const shooter=t.getState().actors.find(a=>a.team===side&&['ST','LST','RST'].includes(a.role));
  const old=structuredClone(t.getState().ball),duration=t.beginAuthoritativeBuildup({side,actorId:shooter.actorId});
  if(old.action)assert.deepEqual(t.getState().ball.action,old.action);
  let last=structuredClone(t.getState().ball),elapsed=0;
  for(;elapsed<6&&!t.isAuthoritativeBuildupReady();elapsed+=1/60){
   const b=t.update(1/60).ball;assert.ok(Math.hypot((b.x-last.x)*1.05,(b.y-last.y)*.68)<2.5);last=structuredClone(b);
  }
  assert.ok(t.isAuthoritativeBuildupReady(),`${side}/${warmup} failed to receive`);
  assert.ok(elapsed<=duration+.5);assert.equal(t.getState().ball.ownerActorId,shooter.actorId);
 }
});
test('mirrored revealed outcomes preserve scorer and only goals finish inside the goal mouth',async()=>{
 for(const half of [1,2])for(const side of ['home','away'])for(const outcome of ['GOAL','SAVE','MISS']){
  const t=await tactical();if(half===2)t.switchEnds();
  const shooter=t.getState().actors.find(a=>a.team===side&&['ST','LST','RST'].includes(a.role));
  t.beginAuthoritativeBuildup({side,actorId:shooter.actorId});
  for(let i=0;i<350&&!t.isAuthoritativeBuildupReady();i++)t.update(1/60);
  assert.ok(t.isAuthoritativeBuildupReady());const before=structuredClone(t.getState().ball);
  const duration=t.beginAuthoritativeEvent({side,actorId:shooter.actorId,outcome,ballStart:[1,99],ballTarget:[99,50]});
  assert.equal(t.getState().ball.x,before.x);assert.equal(t.getState().ball.y,before.y);
  for(let i=0;i<Math.ceil(duration*60)+1;i++){
   t.update(1/60);if(i===0)assert.equal(t.getState().actors.find(a=>a.animationState==='SHOOT')?.actorId,shooter.actorId);
  }
  const {ball,teams,actors}=t.getState(),progress=teams[side].direction>0?ball.x:100-ball.x;
  if(outcome==='GOAL'){assert.ok(progress>100);assert.ok(Math.abs(ball.y-50)<5);}
  if(outcome==='SAVE')assert.ok(progress<100);
  if(outcome==='MISS')assert.ok(Math.abs(ball.y-50)>5);
 }
});
