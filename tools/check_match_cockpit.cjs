/* Optional real-browser acceptance. Requires an existing Playwright installation.
 * Uses a disposable database; never opens the real career. node tools/check_match_cockpit.cjs
 */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const fs = require('node:fs'), path = require('node:path');
const {chromium} = require('playwright');
const repo = path.resolve(__dirname, '..');
const out = path.resolve(process.env.FOOTY_QA_OUTPUT || path.join(repo, '.upgrade-backups/cockpit-browser-qa'));
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  fs.mkdirSync(out, {recursive:true});
  const server = spawn(path.join(repo, '.venv/bin/python'), [path.join(__dirname,'live_3d_test_server.py'), '8781'], {cwd:repo, stdio:['ignore','pipe','pipe']});
  let browser;
  try {
    const url = await new Promise((resolve,reject) => {
      let output=''; const timer=setTimeout(() => reject(Error('Fixture timeout')), 15000);
      server.once('exit', code => {clearTimeout(timer); reject(Error(`Fixture exited ${code}`));});
      server.stdout.on('data', chunk => {output += chunk; for (const line of output.split('\n')) {
        try {const value=JSON.parse(line); if(value.url) {clearTimeout(timer); resolve(value.url);}} catch {}
      }});
    });
    let ready=false;
    for (let i=0;i<30;i++) {try {if((await fetch(url)).ok) {ready=true;break;}} catch {} await delay(100);}
    assert.ok(ready,'Fixture responds');
    browser=await chromium.launch({headless:true});
    const page=await browser.newPage(); const errors=[]; page.on('pageerror', error => errors.push(error.message));
    await page.goto(url); await page.locator('#match-3d-shell').waitFor({state:'visible',timeout:20000});
    await page.locator('#pause-replay').click();
    const sizes=[[1512,982],[1440,900],[1366,768],[1280,800],[390,844]];
    for (const [width,height] of sizes) {
      await page.setViewportSize({width,height}); await delay(150);
      const layout=await page.evaluate(() => {
        const ids=['match-broadcast','player-briefing','match-timeline','squad-tabs','pause-replay','open-match-report','match-minute'];
        return {width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
          boxes:ids.map(id => {const r=document.getElementById(id).getBoundingClientRect();return {id,x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};})};
      });
      assert.ok(layout.width<=width+1 && layout.height<=height+1,`Document must fit ${width}x${height}: ${JSON.stringify(layout)}`);
      for(const box of layout.boxes) assert.ok(box.x>=0 && box.y>=0 && box.right<=width+1 && box.bottom<=height+1 && box.height>0,JSON.stringify(box));
      await page.screenshot({path:path.join(out,`cockpit-${width}x${height}.png`)});
    }
    await page.setViewportSize({width:1366,height:768});
    await page.locator('#tab-own').focus(); await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#tab-bench').getAttribute('aria-selected'),'true');
    assert.ok(await page.locator('#squad-bench').isVisible());
    await page.getByRole('button',{name:'Tactical 2D',exact:true}).click();
    assert.ok(await page.locator('#match-2d-shell').isVisible());
    await page.getByRole('button',{name:'Live 3D',exact:true}).click();
    await page.locator('#finish-replay').click();
    await page.waitForFunction(() => !document.getElementById('open-match-report').disabled);
    assert.equal(await page.locator('#match-report-dialog').isVisible(),false,'Report must not steal focus or open automatically');
    assert.equal(await page.evaluate(() => window.scrollY),0);
    await page.locator('#open-match-report').click(); assert.ok(await page.locator('#post-match-mount').isVisible());
    await page.keyboard.press('Escape'); assert.equal(await page.locator('#match-report-dialog').isVisible(),false);
    assert.equal(await page.evaluate(() => document.activeElement.id),'open-match-report');
    await page.reload(); await page.waitForFunction(() => !document.getElementById('open-match-report').disabled);
    assert.equal(await page.locator('#match-minute').textContent(),'FT');
    assert.equal(await page.locator('#match-report-dialog').isVisible(),false);
    const feed=page.locator('#match-timeline'); await feed.evaluate(node => {node.scrollTop=0; node.dispatchEvent(new Event('scroll'));});
    await page.locator('#jump-to-live').click();
    assert.ok(await feed.evaluate(node => node.scrollHeight-node.clientHeight-node.scrollTop<2));
    const fallback=await browser.newPage(); await fallback.route('**/*.glb*',route=>route.abort()); await fallback.goto(url);
    await fallback.locator('#match-3d-status').filter({hasText:'unavailable'}).waitFor();
    assert.ok(await fallback.locator('#match-2d-shell').isVisible()); await fallback.close();
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({passed:true,sizes,browser:await browser.version()},null,2));
    console.log('Cockpit browser acceptance passed: '+out);
  } finally {await browser?.close(); server.kill('SIGTERM');}
})().catch(error=>{console.error(error);process.exitCode=1;});
