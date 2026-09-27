const {test} = require('node:test');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const plan = require('./fixtures/match-visual-plan.json');
const load = name => import(pathToFileURL(path.resolve('app/static/match', name)).href);
async function fixture() {
  const [{createMatchEngine}, {createTacticalEngine}] = await Promise.all([load('match-engine.js'), load('tactical-engine.js')]);
  let clock = 1000, next = 0;
  const frames = new Map(), rendered = [];
  global.performance = {now: () => clock};
  global.requestAnimationFrame = fn => {frames.set(++next,fn);return next;};
  global.cancelAnimationFrame = id => frames.delete(id);
  global.document = new EventTarget(); document.hidden = false;
  global.window = new EventTarget();
  const tactical = createTacticalEngine(structuredClone(plan));
  const engine = createMatchEngine({tactical,renderer:{render:s=>rendered.push(structuredClone(s))}});
  function frame(ms=1000/60) { clock+=ms;const work=[...frames];frames.clear();work.forEach(([,fn])=>fn(clock)); }
  return {engine,tactical,frames,rendered,frame};
}
test('full time cannot restart RAF, step actors, or accept late revealed transitions', async()=>{
  const f=await fixture();f.engine.start();f.frame();
  assert.equal(typeof f.engine.finish,'function');f.engine.finish();
  const end=JSON.stringify(f.tactical.getState());
  f.engine.start();f.engine.resume();f.engine.setSpeed(4);f.engine.handleHalftime();
  f.engine.handleCard({visual:{kind:'red_card',side:'home'}});
  document.hidden=true;document.dispatchEvent(new Event('visibilitychange'));
  document.hidden=false;document.dispatchEvent(new Event('visibilitychange'));f.frame(10000);
  assert.equal(f.frames.size,0);assert.equal(JSON.stringify(f.tactical.getState()),end);
  assert.equal(f.engine.isFinished(),true);f.engine.destroy();
});
test('manual pause remains paused after tab visibility returns and consumes no RAF',async()=>{
  const f=await fixture();f.engine.start();f.engine.pause();
  assert.equal(f.frames.size,0);
  document.hidden=true;document.dispatchEvent(new Event('visibilitychange'));
  document.hidden=false;document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(f.engine.isPaused(),true);assert.equal(f.frames.size,0);
  f.engine.resume();assert.equal(f.frames.size,1);f.engine.destroy();
});
test('opening a completed match draws all 22 actors without starting a simulation',async()=>{
  const f=await fixture();assert.equal(typeof f.engine.finish,'function');f.engine.finish();
  assert.equal(f.rendered.length,1);assert.equal(f.rendered[0].actors.length,22);assert.equal(f.frames.size,0);
  f.engine.destroy();
});
test('final repaint uses a captured frame and never steps the tactical engine',async()=>{
  const f=await fixture();f.engine.start();f.frame();assert.equal(typeof f.engine.finish,'function');f.engine.finish();
  const frame=structuredClone(f.rendered.at(-1));f.tactical.getState().actors[0].x=99;
  f.engine.repaint();assert.deepEqual(f.rendered.at(-1),frame);assert.equal(f.frames.size,0);f.engine.destroy();
});
test('4x speed advances four times the fixed-step simulation rather than being clamped by tactics',async()=>{
  async function elapsed(speed) {const f=await fixture();f.engine.setSpeed(speed);f.engine.start();for(let i=0;i<60;i++)f.frame();const s=f.rendered.at(-1);f.engine.destroy();return s.elapsed;}
  const one=await elapsed(1),four=await elapsed(4);
  assert.ok(Number.isFinite(one));assert.ok(Math.abs(one-1)<.02);assert.ok(Math.abs(four-4)<.02);
});
test('destroy is terminal and resolves pending presentation waits without leaking frames',async()=>{
  const f=await fixture();f.engine.start();assert.equal(typeof f.engine.waitForSimulation,'function');
  const wait=f.engine.waitForSimulation(10);f.engine.destroy();assert.equal(await wait,false);
  f.engine.start();f.engine.resume();f.frame();assert.equal(f.frames.size,0);
});
test('finishing while paused captures instant cards in the final frame',async()=>{
 const f=await fixture();f.engine.start();f.engine.pause();
 f.engine.handleCard({visual:{kind:'red_card',side:'away'}});
 f.engine.finish();assert.equal(f.rendered.at(-1).actors.length,21);f.engine.destroy();
});
