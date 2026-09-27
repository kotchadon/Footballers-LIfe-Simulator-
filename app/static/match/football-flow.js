const clamp=(value,min,max)=>Math.max(min,Math.min(max,Number(value)||0));
const metres=(a,b)=>Math.hypot((Number(b.x)-Number(a.x))*1.05,(Number(b.y)-Number(a.y))*.68);
export function nextFlowPhase(current, turnover=false) {
  if (turnover) return 'TRANSITION_ATTACK';
  return ({TRANSITION_ATTACK:'PROGRESSION',BUILDUP:'PROGRESSION',PROGRESSION:'FINAL_THIRD',FINAL_THIRD:'BUILDUP'})[current] || 'BUILDUP';
}
// Normalized pitch coordinates; distances/speeds are evaluated in metres.
// A receiver, not a fabricated destination, distinguishes a cross from a switch.
export function selectPassProfile(carrier,receiver,{direction=1,phase='BUILDUP'}={}) {
  const dx=(receiver.x-carrier.x)*direction, lateral=Math.abs(receiver.y-carrier.y);
  const distance=metres(carrier,receiver);
  const wide=carrier.y<=22||carrier.y>=78;
  const finalThird=direction>0?carrier.x>=72:carrier.x<=28;
  const inBox=(direction>0?receiver.x>=84:receiver.x<=16)&&receiver.y>=30&&receiver.y<=70;
  if (phase==='FINAL_THIRD'&&wide&&finalThird&&inBox&&dx>=-12) {
    const target={x:receiver.x,y:receiver.y};
    return {kind:'CROSS',target,duration:clamp(distance/30,.55,1.5),maxHeight:dx<0?1.1:2.7};
  }
  const target={x:receiver.x,y:receiver.y};
  if (lateral>=38&&distance>=28) return {kind:'LONG_SWITCH',target,duration:clamp(distance/32,.82,2.8),maxHeight:3.4};
  if (distance>=31) return {kind:'LOFTED_PASS',target,duration:clamp(distance/36,.75,2.8),maxHeight:1.9};
  if (distance>=16&&dx>=8) return {kind:'DRIVEN_PASS',target,duration:clamp(distance/40,.42,1.1),maxHeight:.28};
  return {kind:'GROUND_PASS',target,duration:clamp(distance/30,.3,1.1),maxHeight:.06};
}
export function planAuthoritativeAttack(ball,actors,{side='home',direction=1,shooterId=null}={}) {
  const available=actors.filter(actor=>actor.team===side&&actor.role!=='GK');
  const shooter=available.find(actor=>actor.actorId===shooterId)||available.sort((a,b)=>(b.x-a.x)*direction)[0];
  if (!shooter) return [];
  const start={x:Number(ball.x),y:Number(ball.y)};
  const nodes=[{actorId:null,...start},...available];
  const targetIndex=nodes.indexOf(shooter);
  const owner=actors.find(a=>a.actorId===ball.ownerActorId);
  const recovery=owner&&owner.team!==side
    ? available.reduce((best,a)=>metres(a,start)<metres(best,start)?a:best,available[0]) : null;
  const entry=recovery?nodes.indexOf(recovery):0;
  const queue=[entry],previous=new Map([[0,null]]);
  if(entry)previous.set(entry,0);
  while(queue.length&&!previous.has(targetIndex)){
    const index=queue.shift(),from=nodes[index];
    const candidates=nodes.map((node,i)=>({node,i,d:metres(from,node)}))
      .filter(item=>item.i>0&&!previous.has(item.i)&&item.d<=42)
      .sort((a,b)=>{
        if(a.i===targetIndex)return -1;if(b.i===targetIndex)return 1;
        return ((b.node.x-a.node.x)*direction)||a.d-b.d;
      });
    for(const item of candidates){previous.set(item.i,index);queue.push(item.i);}
  }
  let indices=[];
  if(previous.has(targetIndex))for(let at=targetIndex;at;at=previous.get(at))indices.unshift(at);
  else indices=[targetIndex];
  // Keep the broadcast sequence readable: at most recovery, midfield, final pass.
  // Never shorten a connected route by discarding an intermediate receiver.
  const route=[];let from=start;
  for(const index of indices){const receiver=nodes[index];const profile=selectPassProfile(from,receiver,{direction,phase:route.length?'PROGRESSION':'BUILDUP'});
    route.push({from:{x:from.x,y:from.y},to:profile.target,receiverId:receiver.actorId,...profile});from={x:profile.target.x,y:profile.target.y};}
  return route;
}

export function currentPresentationFocus(ball,actors) {
  const owner=actors.find(a=>a.actorId===ball.ownerActorId);
  const target=ball.action?.to || (owner?{x:owner.targetX,y:owner.targetY}:ball);
  const dx=(Number(target.x??ball.x)-ball.x)*1.05,dy=(Number(target.y??ball.y)-ball.y)*.68;
  const distance=Math.hypot(dx,dy),lead=Math.min(7,distance*.2);
  return {x:clamp(ball.x+(distance?dx/distance*lead/1.05:0),0,100),
    y:clamp(ball.y+(distance?dy/distance*lead/.68:0),0,100)};
}
