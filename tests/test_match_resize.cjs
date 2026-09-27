const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
test('paused and finished 3D resize observes the common visible container',()=>{
 const source=fs.readFileSync('app/static/match/bootstrap.js','utf8');
 const block=source.slice(source.indexOf('  const observer = new ResizeObserver'),source.indexOf('  window.addEventListener("beforeunload"'));
 const hidden2d={hidden:true},broadcast={hidden:false};let observed,callback,resized=0;
 const context={stage:hidden2d,root:{querySelector:()=>broadcast},renderer:{resize:()=>resized++},ResizeObserver:class{constructor(fn){callback=fn}observe(node){observed=node}}};
 vm.runInNewContext(block,context);assert.equal(observed,broadcast);callback();assert.equal(resized,1);
});
