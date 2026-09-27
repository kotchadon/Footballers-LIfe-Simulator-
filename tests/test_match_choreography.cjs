const {test}=require('node:test');const assert=require('node:assert/strict');
const plan=require('./fixtures/match-visual-plan.json');
async function fixture(){
 const [{createEventChoreography},{createTacticalEngine},{createMatchEngine}]=await Promise.all(['event-choreography','tactical-engine','match-engine'].map(s=>import('../app/static/match/'+s+'.js')));
 global.document=new EventTarget();document.hidden=false;global.window=new EventTarget();
 let now=0,id=0;const frames=new Map();global.performance={now:()=>now};global.requestAnimationFrame=fn=>{frames.set(++id,fn);return id};global.cancelAnimationFrame=id=>frames.delete(id);
 const tactical=createTacticalEngine(structuredClone(plan)),renders=[],overlays=[];
 const engine=createMatchEngine({tactical,renderer:{render:state=>renders.push(state)}});
 const c=createEventChoreography({tactical,matchEngine:engine,onOverlay:s=>overlays.push(s)});
 engine.start();async function step(n){for(let i=0;i<n;i++){now+=1000/60;let work=[...frames.values()];frames.clear();work.forEach(fn=>fn(now));await Promise.resolve();}}
 return{tactical,engine,c,step,overlays,renders};
}
test('paused shot choreography cannot announce a goal or run a late keeper catch',async()=>{
 const f=await fixture();const job=f.c.playEvent({sequence:1,minute:30,visual:{kind:'goal',side:'home',ball_start:[85,50],ball_target:[98,50]}});
 f.engine.pause();await f.step(90);assert.deepEqual(f.overlays,['BUILDUP']);
 f.engine.resume();await f.step(360);await job;assert.deepEqual(f.overlays,['BUILDUP','SHOT','GOAL']);assert.ok(f.renders.some(frame=>frame.ball.x>100));f.engine.destroy();
});
test('cancelling a shot prevents late outcome overlays after finish',async()=>{
 const f=await fixture();const job=f.c.playEvent({sequence:2,minute:30,visual:{kind:'save',side:'home'}});
 f.c.cancel();f.engine.finish();await job;assert.deepEqual(f.overlays,['BUILDUP']);assert.notEqual(f.tactical.getState().ball.state,'KEEPER_HELD');f.engine.destroy();
});
test('45th minute does not switch ends; first later reveal switches once',async()=>{
 const f=await fixture();const direction=f.tactical.getState().teams.home.direction;
 f.c.applyInstantEvent({sequence:1,minute:45,visual:{kind:'moment'}});assert.equal(f.tactical.getState().teams.home.direction,direction);
 f.c.applyInstantEvent({sequence:2,minute:46,visual:{kind:'moment'}});f.c.applyInstantEvent({sequence:3,minute:60,visual:{kind:'moment'}});assert.equal(f.tactical.getState().teams.home.direction,-direction);f.engine.destroy();
});
test('repeated revealed red card affects one player only',async()=>{
 const f=await fixture();const event={sequence:4,minute:15,visual:{kind:'red_card',side:'home'}};
 f.c.applyInstantEvent(event);f.c.applyInstantEvent(structuredClone(event));assert.equal(f.tactical.getState().actors.length,21);f.engine.destroy();
});
test('paused instant substitution refreshes captured marker without stepping the clock',async()=>{
 const f=await fixture();f.engine.pause();const time=f.renders.at(-1).elapsed;
 f.c.applyInstantEvent({sequence:1,minute:30,visual:{kind:'substitution_off',actor_id:'career_player'}});
 assert.equal(f.renders.at(-1).actors.some(a=>a.isUser),false);
 assert.equal(f.renders.at(-1).elapsed,time);f.engine.destroy();
});
test('outer app watchdog does not commit a paused shot on wall time',async()=>{
 const fs=require('node:fs'),vm=require('node:vm');const f=await fixture();f.engine.pause();
 const source=fs.readFileSync('app/static/app.js','utf8');const fn=source.slice(source.indexOf('    async function addEvent(item'),source.indexOf('    async function postJson('));
 const wall=[],commits=[];
 const context={window:{FootyRevealedEvents:[],FootyMatchVisuals:{playEvent:()=>f.engine.waitForSimulation(.8),waitForSimulation:s=>f.engine.waitForSimulation(s),cancelEvent:()=>{}},setTimeout:cb=>{wall.push(cb);return wall.length;},clearTimeout:()=>{}},timeline:{querySelector:()=>null},paused:false,alreadyCompleted:false,finalising:false,reportShown:false,addEventImmediate:item=>commits.push(item),console};
 vm.createContext(context);vm.runInContext(fn+'; this.runEvent=addEvent;',context);
 const pending=context.runEvent({sequence:10,visual:{kind:'goal'}});wall.forEach(cb=>cb());await new Promise(r=>setImmediate(r));
 assert.equal(commits.length,0,'A paused visual cannot commit its score through the wall timer');
 f.engine.resume();await f.step(70);await pending;assert.equal(commits.length,1);f.engine.destroy();
});
test('a late shot cannot overwrite the final report after skip',async()=>{
 const fs=require('node:fs'),vm=require('node:vm');const f=await fixture();
 const source=fs.readFileSync('app/static/app.js','utf8');const fn=source.slice(source.indexOf('    async function addEvent(item'),source.indexOf('    async function postJson('));
 const commits=[];const context={window:{FootyRevealedEvents:[],FootyMatchVisuals:{playEvent:()=>f.engine.waitForSimulation(.8),waitForSimulation:s=>f.engine.waitForSimulation(s),cancelEvent:()=>{}},setTimeout,clearTimeout},timeline:{querySelector:()=>null},paused:false,alreadyCompleted:false,finalising:false,reportShown:false,addEventImmediate:item=>commits.push(item),console};
 vm.createContext(context);vm.runInContext(fn+'; this.runEvent=addEvent;',context);
 const pending=context.runEvent({sequence:11,visual:{kind:'goal'}});context.reportShown=true;f.engine.finish();await pending;
 assert.equal(commits.length,0);f.engine.destroy();
});
test('network failure pauses visuals together with replay controls',async()=>{
 const fs=require('node:fs'),vm=require('node:vm');const source=fs.readFileSync('app/static/app.js','utf8');
 const fn=source.slice(source.indexOf('    async function tick()'),source.indexOf('    const MAJOR_EVENT_KINDS'));
 let synced=0;const context={paused:false,finalising:false,reportShown:false,advancing:false,skipInProgress:false,cursor:0,advanceEndpoint:'/test',postJson:async()=>{throw new Error('test connection failure')},syncVisualControls:()=>synced++,status:{},pauseButton:{},showToast:()=>{}};
 vm.createContext(context);vm.runInContext(fn+'; this.runTick=tick;',context);await context.runTick();assert.equal(context.paused,true);assert.ok(synced>0);assert.equal(context.advancing,false);
});
test('long buildup consumes the existing replay gap instead of adding another full delay',async()=>{
 const fs=require('node:fs'),vm=require('node:vm');const source=fs.readFileSync('app/static/app.js','utf8');
 const fn=source.slice(source.indexOf('    async function tick()'),source.indexOf('    const MAJOR_EVENT_KINDS'));
 const delays=[];let now=0;
 const context={Date:{now:()=>now},paused:false,finalising:false,reportShown:false,advancing:false,skipInProgress:false,cursor:0,speed:1,timer:null,advanceEndpoint:'/test',postJson:async()=>({event:{kind:'goal'},cursor:1,has_more:true}),addEvent:async()=>{now+=2600;},interval:()=>3000,window:{setTimeout:(_fn,ms)=>delays.push(ms)},syncVisualControls:()=>{},status:{},pauseButton:{},showToast:()=>{}};
 vm.createContext(context);vm.runInContext(fn+'; this.runTick=tick;',context);await context.runTick();assert.deepEqual(delays,[2000]);
});
