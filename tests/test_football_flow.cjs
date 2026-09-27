const {test}=require('node:test');const assert=require('node:assert/strict');
const plan=require('./fixtures/match-visual-plan.json');
const load=()=>import('../app/static/match/football-flow.js');
const player=(x,y,role='CM',id=`p${x}-${y}`)=>({actorId:id,x,y,role,team:'home'});
test('possession advances through buildup, progression and final third in order',async()=>{
 const {nextFlowPhase}=await load();
 assert.equal(nextFlowPhase('BUILDUP',false),'PROGRESSION');
 assert.equal(nextFlowPhase('PROGRESSION',false),'FINAL_THIRD');
 assert.equal(nextFlowPhase('FINAL_THIRD',false),'BUILDUP');
 assert.equal(nextFlowPhase('BUILDUP',true),'TRANSITION_ATTACK');
 assert.equal(nextFlowPhase('TRANSITION_ATTACK',false),'PROGRESSION');
});
test('short local option is a grounded pass',async()=>{
 const {selectPassProfile}=await load();const p=selectPassProfile(player(40,50),player(51,54),{direction:1,phase:'BUILDUP'});
 assert.equal(p.kind,'GROUND_PASS');assert.ok(p.maxHeight<=.2);
});
test('fast vertical midfield pass is driven and stays low',async()=>{
 const {selectPassProfile}=await load();const p=selectPassProfile(player(35,50),player(58,52),{direction:1,phase:'PROGRESSION'});
 assert.equal(p.kind,'DRIVEN_PASS');assert.ok(p.maxHeight>.2&&p.maxHeight<.7);
});
test('long central pass can be lofted without masquerading as a cross',async()=>{
 const {selectPassProfile}=await load();const p=selectPassProfile(player(28,48),player(65,55,'ST'),{direction:1,phase:'PROGRESSION'});
 assert.equal(p.kind,'LOFTED_PASS');assert.ok(p.maxHeight>=1.3&&p.maxHeight<3);
});
test('large lateral midfield diagonal is a switch, never a cross',async()=>{
 const {selectPassProfile}=await load();const p=selectPassProfile(player(48,12,'LM'),player(61,88,'RM'),{direction:1,phase:'PROGRESSION'});
 assert.equal(p.kind,'LONG_SWITCH');assert.ok(p.maxHeight>=3);
});
test('a cross only starts wide in the final third and lands in the box',async()=>{
 const {selectPassProfile}=await load();const p=selectPassProfile(player(82,86,'RW'),player(91,49,'ST'),{direction:1,phase:'FINAL_THIRD'});
 assert.equal(p.kind,'CROSS');assert.ok(p.target.x>=87&&p.target.x<=94);assert.ok(p.target.y>=36&&p.target.y<=64);
});
test('same diagonal from midfield remains a switch',async()=>{
 const {selectPassProfile}=await load();const p=selectPassProfile(player(57,86,'RW'),player(78,35,'ST'),{direction:1,phase:'PROGRESSION'});
 assert.equal(p.kind,'LONG_SWITCH');
});
test('advanced opposite-wing passes remain switches and a cross follows a real box receiver',async()=>{
 const {selectPassProfile}=await load();
 for(const direction of [1,-1]){
  const x=v=>direction===1?v:100-v;
  assert.equal(selectPassProfile(player(x(82),12),player(x(90),86),{direction,phase:'FINAL_THIRD'}).kind,'LONG_SWITCH');
  const receiver=player(x(88),43),cross=selectPassProfile(player(x(92),12),receiver,{direction,phase:'FINAL_THIRD'});
  assert.equal(cross.kind,'CROSS');assert.deepEqual(cross.target,{x:x(88),y:43});
 }
});
test('authoritative attack route begins at current ball and ends at revealed shooter with connected links',async()=>{
 const {planAuthoritativeAttack}=await load();const actors=plan.actors.map((a,i)=>({actorId:a.actor_id,team:a.team,role:a.role,x:20+(i%6)*12,y:12+(i%5)*18}));
 const shooter=actors.find(a=>a.team==='home'&&a.role==='ST');const route=planAuthoritativeAttack({x:31,y:22,ownerActorId:null},actors,{side:'home',direction:1,shooterId:shooter.actorId});
 assert.deepEqual(route[0].from,{x:31,y:22});assert.equal(route.at(-1).receiverId,shooter.actorId);
 for(const leg of route){const metres=Math.hypot((leg.to.x-leg.from.x)*1.05,(leg.to.y-leg.from.y)*.68);assert.ok(metres<=42,`disconnected ${metres}`);}
});
test('an opposing possession is recovered locally before linking to the named scorer',async()=>{
 const {planAuthoritativeAttack}=await load();
 const actors=[{...player(45,50,'CM','opponent'),team:'away'},player(47,52,'CM','recovery'),player(76,50,'ST','scorer')];
 const route=planAuthoritativeAttack({x:45,y:50,ownerActorId:'opponent'},actors,{side:'home',shooterId:'scorer'});
 assert.equal(route[0].receiverId,'recovery');assert.equal(route.at(-1).receiverId,'scorer');
});
