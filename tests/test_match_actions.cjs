const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const plan=JSON.parse(fs.readFileSync(__dirname+'/fixtures/match-visual-plan.json'));
const tactical=()=>import('../app/static/match/tactical-engine.js').then(m=>m.createTacticalEngine(structuredClone(plan)));
test('a revealed goal crosses the actual goal line inside the posts',async()=>{
 const t=await tactical();const duration=t.beginAuthoritativeEvent({side:'home',outcome:'GOAL',ballStart:[82,47],ballTarget:[98,50]});
 for(let i=0;i<Math.ceil(duration*60)+1;i++)t.update(1/60);
 const b=t.getState().ball;assert.ok(b.x>100);assert.ok(Math.abs(b.y-50)<5);
});
test('duplicate red card cannot remove a second actor',async()=>{
 const t=await tactical();const id=t.getState().actors.find(a=>a.team==='home'&&a.role!=='GK').actorId;
 t.reshapeForRedCard('home',id);t.reshapeForRedCard('home',id);assert.equal(t.getState().actors.length,21);
});
test('substitute is marked and fills an empty slot without removing another player',async()=>{
 const t=await tactical();const user=t.getState().actors.find(a=>a.isUser);t.removeActor(user.actorId);
 const p=structuredClone(plan.actors.find(a=>a.actor_id===user.actorId));t.activateActor(p);
 assert.equal(t.getState().actors.length,22);assert.equal(t.getState().actors.filter(a=>a.isUser).length,1);
});
test('movement respects human speed in metres on both pitch axes',async()=>{
 const {integrateMovement}=await import('../app/static/match/movement.js');
 const a={x:10,y:10,vx:0,vy:0,heading:0,maxSpeed:9,acceleration:6};
 for(let i=0;i<100;i++)integrateMovement(a,{x:90,y:90},1/60);
 assert.ok(Math.hypot(a.vx*1.05,a.vy*.68)<=9.001);
});
test('phase changes transfer the ball through an action, never a new distant owner',async()=>{
 const t=await tactical();let old=structuredClone(t.getState().ball);
 for(let i=0;i<1800;i++){const b=t.update(1/60).ball;
 if(old.ownerActorId&&b.ownerActorId&&old.ownerActorId!==b.ownerActorId) assert.fail('silent ownership change');
 old=structuredClone(b);}
});
test('long sprints on either axis obey metre speed and bounded turning',async()=>{
 const {integrateMovement}=await import('../app/static/match/movement.js');
 for(const target of [{x:95,y:50},{x:50,y:95}]){
 const a={x:50,y:50,vx:0,vy:0,heading:Math.PI,maxSpeed:9,acceleration:6};
 for(let i=0;i<110;i++){let h=a.heading;integrateMovement(a,target,1/60);assert.ok(Math.hypot(a.vx*1.05,a.vy*.68)<=9.001);assert.ok(Math.abs(Math.atan2(Math.sin(a.heading-h),Math.cos(a.heading-h)))<=.151);}
 }
});
test('overlapping outfield bodies separate instead of occupying the same space',async()=>{
 const t=await tactical();const [a,b]=t.getState().actors.filter(a=>a.role!=='GK').slice(0,2);
 a.x=b.x=50;a.y=b.y=50;a.anchorX=b.anchorX=50;a.anchorY=b.anchorY=50;
 t.update(1/60);assert.ok(Math.hypot((a.x-b.x)*1.05,(a.y-b.y)*.68)>.05);
});
