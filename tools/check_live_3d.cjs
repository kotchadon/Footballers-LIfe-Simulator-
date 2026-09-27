/* Local acceptance: requires Node 18+ and Playwright Chromium. Isolated test DB. */
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const path=require('node:path');
const {chromium}=require('playwright');
const repo=path.resolve(__dirname,'..');
const out=path.resolve(process.env.FOOTY_QA_OUTPUT||path.join(repo,'.upgrade-backups','live3d-browser-qa'));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const server=spawn(path.join(repo,'.venv/bin/python'),[path.join(__dirname,'live_3d_test_server.py'),'8778'],{cwd:repo,stdio:['ignore','pipe','pipe']});
 let browser;
 try{
 const url=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(new Error('Fixture server timeout')),15000);
 server.once('exit',code=>{clearTimeout(timer);reject(new Error('Fixture server exited '+code));});
 server.stdout.on('data',data=>{text+=data;for(const line of text.split('\n')){try{const item=JSON.parse(line);if(item.url){clearTimeout(timer);resolve(item.url);return;}}catch{}}});});
 // Readiness is the actual HTTP page, not merely a spawned process.
 let ready=false;for(let i=0;i<50;i++){try{if((await fetch(url)).ok){ready=true;break;}}catch{}await delay(100);}assert.ok(ready);
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.__matchFrames=0;const raf=window.requestAnimationFrame;window.requestAnimationFrame=fn=>raf.call(window,t=>{if(fn.name==='tick')window.__matchFrames++;fn(t);});});
 await page.goto(url);
 await page.locator('#match-3d-shell').waitFor({state:'visible',timeout:20000});
 await page.locator('#pause-replay').click();await delay(1800);
 const frameCount=await page.evaluate(()=>window.__matchFrames);await delay(300);assert.equal(await page.evaluate(()=>window.__matchFrames),frameCount,'Pause must stop match frames');
 const shot=await page.locator('#match-3d-canvas').screenshot({path:path.join(out,'live-3d.png')});
 await page.getByRole('button',{name:'Tactical 2D',exact:true}).click();
 await page.getByRole('button',{name:'Live 3D',exact:true}).click();
 assert.deepEqual(await page.locator('#match-3d-canvas').screenshot(),shot,'Switch must preserve frozen scene');
 await page.locator('#pause-replay').click();await page.locator('[data-match-speed="4"]').click();await delay(500);
 assert.ok(await page.evaluate(()=>window.__matchFrames)>frameCount,'Resume advances shared simulation');
 await page.locator('#pause-replay').click();
 await page.setViewportSize({width:390,height:844});
 await page.locator('#match-3d-canvas').screenshot({path:path.join(out,'live-3d-mobile.png')});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'No horizontal mobile overflow');
 await page.locator('#finish-replay').click();await page.getByText('Full time',{exact:true}).waitFor({timeout:20000});await delay(250);
 const finalCount=await page.evaluate(()=>window.__matchFrames);await delay(500);assert.equal(await page.evaluate(()=>window.__matchFrames),finalCount,'Full time stops frames');
 await page.reload();await page.getByText('Full time',{exact:true}).waitFor({timeout:20000});await delay(250);
 assert.equal(await page.evaluate(()=>window.__matchFrames),0,'Completed reload must not start loop');
 // Missing optional module and missing GLB must independently preserve tactical mode.
 for(const pattern of ['**/three-renderer.js','**/*.glb*']){
  const fallback=await browser.newPage();await fallback.route(pattern,r=>r.abort());await fallback.goto(url);
  await fallback.locator('#match-3d-status').filter({hasText:'unavailable'}).waitFor({timeout:20000});
  assert.equal(await fallback.locator('#match-2d-shell').isVisible(),true);assert.equal(await fallback.getByRole('button',{name:'Live 3D',exact:true}).isEnabled(),false);await fallback.close();
 }
 await page.evaluate(()=>document.getElementById('match-3d-canvas').dispatchEvent(new Event('webglcontextlost',{cancelable:true})));
 await page.locator('#match-2d-shell').waitFor({state:'visible'});
 assert.deepEqual(errors,[],'No uncaught browser errors');
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({passed:true,checks:['live-3d','pause','view-switch','resume','4x','mobile','full-time','completed-reload','module-fallback','glb-fallback','context-loss'],browser:await browser.version()},null,2));
 console.log('Browser acceptance passed. Evidence: '+out);
 } finally {await browser?.close();server.kill('SIGTERM');}
})().catch(error=>{console.error(error);process.exitCode=1;});
