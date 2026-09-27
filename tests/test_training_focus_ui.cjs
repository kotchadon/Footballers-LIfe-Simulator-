/* Run: node tests/test_training_focus_ui.cjs
 * Uses the real Flask-rendered dashboard and API responses. The small DOM and
 * fetch adapters isolate training UI behaviour; this is not a browser/layout test.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const repo = path.resolve(__dirname, '..');
const python = path.join(repo, '.venv', 'bin', 'python');
const fixture = JSON.parse(execFileSync(python, ['-c', `
import json,tempfile
from pathlib import Path
from app import create_app
from app.services import create_career
from app.db import get_db
with tempfile.TemporaryDirectory() as td:
 app=create_app({'TESTING':True,'DATABASE':str(Path(td)/'ui.sqlite3'),'SECRET_KEY':'test'})
 with app.app_context():
  cid=create_career('QA','India','CAM')
  get_db().execute("UPDATE careers SET training_focus='passing',season_phase='competitive' WHERE id=?",(cid,))
  get_db().commit()
 client=app.test_client()
 html=client.get('/').get_data(as_text=True)
 plans={f:client.post('/api/training-plan',json={'focus':f}).get_json() for f in ['pace','shooting','passing','dribbling','defending','physical','balanced','recovery']}
 print(json.dumps({'html':html,'plans':plans}))
`], {cwd:repo,encoding:'utf8'}));
const source=fs.readFileSync(path.join(repo,'app/static/app.js'),'utf8');
const functions = source.slice(source.indexOf('  async function setTrainingFocus('),source.indexOf('  document.querySelectorAll("[data-training-focus]").forEach((button)')) + source.slice(source.indexOf('  function setupDashboardShortcuts('),source.indexOf('  function setupMatchReplay('));
function element(attributes={}, text='') {
  const classes=new Set((attributes.class||'').split(' ').filter(Boolean));
  return {attributes, dataset:Object.fromEntries(Object.entries(attributes).filter(([k])=>k.startsWith('data-')).map(([k,v])=>[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),v])),
    disabled:Object.hasOwn(attributes,'disabled'), textContent:text, style:{},
    setAttribute(k,v){this.attributes[k]=v;},
    classList:{add:v=>classes.add(v),remove:v=>classes.delete(v),toggle(v,on){on?classes.add(v):classes.delete(v);},contains:v=>classes.has(v)}};
}
function setup() {
  const nodes=[];
  for(const m of fixture.html.matchAll(/<(\w+)\b([^>]*)>/g)) {
    const attrs={}; for(const a of m[2].matchAll(/([\w-]+)="([^"]*)"/g)) attrs[a[1]]=a[2];
    if(attrs.id || attrs['data-training-focus'] || attrs['data-training-preview']) nodes.push(element(attrs));
  }
  const ids=Object.fromEntries(nodes.filter(n=>n.attributes.id).map(n=>[n.attributes.id,n]));
  const buttons=nodes.filter(n=>n.dataset.trainingFocus), previews=nodes.filter(n=>n.dataset.trainingPreview);
  const panel=ids.development;
  panel.querySelectorAll=()=>previews;
  const toasts=[],requests=[];
  const document={getElementById:id=>ids[id]||null,querySelectorAll:selector=>selector==='[data-training-focus]'?buttons:[],querySelector:selector=>buttons.find(b=>selector===`[data-training-focus="${b.dataset.trainingFocus}"]`)||null};
  const context=vm.createContext({document,showToast:(message,error)=>toasts.push({message,error}),fetch:async(endpoint,options)=>{
    const focus=JSON.parse(options.body).focus;
    requests.push({endpoint,options});
    return {ok:true,json:async()=>fixture.plans[focus]};
  }});
  vm.runInContext(functions,context);
  return {context,ids,panel,buttons,previews,toasts,requests};
}
async function run() {
  const ui=setup();
  for(const focus of Object.keys(fixture.plans)) {
    const button=ui.buttons.find(b=>b.dataset.trainingFocus===focus);
    await ui.context.setTrainingFocus(button);
    assert.equal(ui.toasts.at(-1)?.error,undefined,`focus ${focus} should update without a missing-element error`);
    assert.equal(ui.ids['training-plan-title'].textContent,fixture.plans[focus].plan.label);
    for(const node of ui.previews) assert.equal(node.textContent,`+${fixture.plans[focus].plan.weekly_preview[node.dataset.trainingPreview]} XP`);
    for(const b of ui.buttons) assert.equal(b.attributes['aria-pressed'],String(b===button));
    assert(ui.buttons.every(b=>!b.disabled));
  }
  console.log('PASS all eight focus updates, selected accessibility state and recovery preview');
  const before=ui.previews.map(n=>n.textContent);
  ui.context.fetch=async()=>{throw new Error('Connection failed');};
  await ui.context.setTrainingFocus(ui.buttons[0]);
  assert.deepEqual(ui.previews.map(n=>n.textContent),before);
  assert.equal(ui.toasts.at(-1).error,true);
  assert(ui.buttons.every(b=>!b.disabled));
  console.log('PASS network failure preserves preview and permits retry');
  ui.context.fetch=async()=>({ok:false,json:async()=>({ok:false,message:'Finish active match',plan:{locked:true}})});
  await ui.context.setTrainingFocus(ui.buttons[0]);
  assert.equal(ui.panel.dataset.trainingLocked,'true');
  assert(ui.buttons.every(b=>b.disabled));
  assert.deepEqual(ui.previews.map(n=>n.textContent),before);
  let called=false;ui.context.fetch=async()=>{called=true;};
  await ui.context.setTrainingFocus(ui.buttons[1]);
  assert.equal(called,false);
  console.log('PASS active-match conflict locks controls and blocks repeat requests');
  const keys=setup();
  for(const [key,focus] of Object.entries({'1':'pace','2':'shooting','3':'passing','4':'dribbling','5':'defending','6':'physical','r':'recovery'})) {
    let prevented=false;
    assert.equal(keys.context.setupDashboardShortcuts({key,preventDefault(){prevented=true;}}),true);
    await new Promise(resolve=>setImmediate(resolve));
    assert(prevented);
    assert.equal(JSON.parse(keys.requests.at(-1).options.body).focus,focus);
  }
  console.log('PASS existing focus keyboard shortcuts');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
