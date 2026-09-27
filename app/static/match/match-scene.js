import * as THREE from "../vendor/three/three.module.js";
import {createPlayerFactory} from "./player-model.js";

export const GRASS_Y = .04;
export const BALL_RADIUS = .11;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,Number(v)||0));
export function pitchToWorld(x,y,height=0) {
  return new THREE.Vector3((Number(x)-50)*1.05,GRASS_Y+Number(height),-(Number(y)-50)*.68);
}

function addNets(scene) {
  const vertices=[];
  const line=(a,b)=>vertices.push(...a,...b);
  for(const side of [-1,1]) {
    const x=side*52.5,back=side*54.3,top=2.48;
    for(let z=-3.66;z<=3.67;z+=.244){line([x,top,z],[back,top,z]);line([back,.04,z],[back,top,z]);}
    for(let y=.04;y<=top+.01;y+=.244){line([back,y,-3.66],[back,y,3.66]);line([x,y,-3.66],[back,y,-3.66]);line([x,y,3.66],[back,y,3.66]);}
    for(let d=0;d<=1.81;d+=.225){const xx=x+side*d;line([xx,.04,-3.66],[xx,top,-3.66]);line([xx,.04,3.66],[xx,top,3.66]);}
  }
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
  const net=new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({color:0xe9efed,transparent:true,opacity:.48}));net.name='GoalNets';scene.add(net);
}
function addCrowd(scene,asset) {
  asset.updateMatrixWorld(true);
  const positions=[];
  asset.traverse(o=>{
    if(!/^Stand(Long|End)_/.test(o.name))return;
    const b=new THREE.Box3().setFromObject(o),long=o.name.startsWith('StandLong');
    const begin=long?b.min.x+.6:b.min.z+.6,end=long?b.max.x-.6:b.max.z-.6;
    const width=long?b.max.z-b.min.z:b.max.x-b.min.x;
    const rows=Math.max(1,Math.min(3,Math.floor(width/.9)));
    for(let row=0;row<rows;row++)for(let p=begin;p<end;p+=.74){
      if(positions.length>=4200)break;
      const cross=(long?b.min.z:b.min.x)+(row+.5)*width/rows;
      positions.push([long?p:cross,b.max.y+.28,long?cross:p]);
    }
  });
  const bodies=new THREE.InstancedMesh(new THREE.BoxGeometry(.27,.42,.25),new THREE.MeshLambertMaterial({color:0xffffff}),positions.length);
  const heads=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.10,0),new THREE.MeshLambertMaterial({color:0xc2926b}),positions.length);
  const palette=[0x263954,0x31598c,0x657785,0xdbc7b1,0x933b40,0xc0c9bf];const m=new THREE.Matrix4(),c=new THREE.Color();
  positions.forEach(([x,y,z],i)=>{m.makeTranslation(x,y,z);bodies.setMatrixAt(i,m);bodies.setColorAt(i,c.setHex(palette[(i*7+Math.floor(i/13))%palette.length]));m.makeTranslation(x,y+.3,z);heads.setMatrixAt(i,m);});
  bodies.name='StadiumCrowd';heads.name='CrowdHeads';scene.add(bodies,heads);
}
function contactShadow(radius,opacity) {
  const m=new THREE.Mesh(new THREE.CircleGeometry(radius,16),new THREE.MeshBasicMaterial({color:0x14251e,transparent:true,opacity,depthWrite:false}));
  m.rotation.x=-Math.PI/2;m.position.y=.008;return m;
}

export function createMatchScene(asset,plan,{reducedMotion=false}={}) {
  const scene=new THREE.Scene();scene.background=new THREE.Color(0x9db5bf);scene.fog=new THREE.Fog(0x9db5bf,150,260);
  const camera=new THREE.PerspectiveCamera(43,16/9,.1,350);
  const importedLights=[];
  asset.traverse(o=>{
    if(o.isLight)importedLights.push(o);
    if(o.isMesh){o.receiveShadow=true;if(o.material){o.material.roughness=.95;o.material.metalness=0;}}
    if(/^Pitch_Stripe_/.test(o.name))o.material.color.setHex(Number(o.name.slice(-2))%2?0x347d3d:0x398544);
    if(/^Goal(East|West)_/.test(o.name)){o.position.x=o.position.x>0?52.5:-52.5;o.position.y+=GRASS_Y;}
    if(/^Ad_X_/.test(o.name))o.position.x=o.position.x>0?56:-56;
    if(o.name.endsWith('_UserRing'))o.visible=false;
  });
  importedLights.forEach(o=>o.removeFromParent());scene.add(asset);
  const hemi=new THREE.HemisphereLight(0xdaebff,0x486334,2.2);scene.add(hemi);
  const sun=new THREE.DirectionalLight(0xffedd1,2.5);sun.position.set(-25,65,30);sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-65,right:65,top:50,bottom:-50,near:1,far:160});sun.shadow.bias=-.0003;sun.shadow.normalBias=.03;scene.add(sun);
  addNets(scene);addCrowd(scene,asset);
  const slots={home:[],away:[]}, actorSlots=new Map(),models=new Map();const makePlayer=createPlayerFactory();
  for(const team of ['home','away'])for(let i=1;i<=11;i++) {
    const name=`${team}_${String(i).padStart(2,'0')}`,root=asset.getObjectByName(name);
    if(!root)throw new Error(`Missing stadium player ${name}`);
    root.children.forEach(child=>child.visible=false);
    const model=makePlayer(i+(team==='away'?11:0),team);root.add(model.body,contactShadow(.34,.23));
    root.position.y=GRASS_Y;root.visible=false;root.userData.actorId=null;models.set(root,model);slots[team].push(root);
  }
  const ball=asset.getObjectByName('MatchBall');if(!ball)throw new Error('Missing MatchBall');
  ball.geometry.dispose();ball.geometry=new THREE.IcosahedronGeometry(BALL_RADIUS,2);
  const pos=ball.geometry.getAttribute('position'),colors=[];
  for(let i=0;i<pos.count;i++) {const face=Math.floor(i/3);const dark=((face*17+Math.floor(face/9))%13)<3;colors.push(...(dark?[.028,.035,.047]:[.96,.97,.95]));}
  ball.geometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));
  ball.material=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.64});ball.scale.setScalar(1);ball.castShadow=true;
  const ballShadow=contactShadow(.17,.32);ballShadow.name='BallShadow';scene.add(ballShadow);
  const userRing=new THREE.Mesh(new THREE.RingGeometry(.49,.62,40),new THREE.MeshBasicMaterial({color:0xffd24a,side:THREE.DoubleSide,depthWrite:false}));
  userRing.name='CareerPlayerMarker';userRing.rotation.x=-Math.PI/2;userRing.visible=false;scene.add(userRing);
  const pointer=new THREE.Mesh(new THREE.ConeGeometry(.12,.22,3),new THREE.MeshBasicMaterial({color:0xffd24a}));pointer.rotation.z=Math.PI;pointer.visible=false;scene.add(pointer);
  let previousTime=null,previousBall=null,disposed=false,cameraMode='broadcast',cameraReset=true;
  const target=new THREE.Vector3();
  function reconcile(actors) {
    const present=new Map(actors.map(a=>[a.actorId,a]));
    for(const [id,root] of actorSlots)if(!present.has(id)||present.get(id).team!==root.userData.team){root.visible=false;root.userData.actorId=null;actorSlots.delete(id);}
    const additions=actors.filter(a=>!actorSlots.has(a.actorId)).sort((a,b)=>(a.role==='GK'?-1:0)-(b.role==='GK'?-1:0)||a.actorId.localeCompare(b.actorId));
    for(const actor of additions){const root=slots[actor.team]?.find(r=>r.userData.actorId===null);if(!root)continue;root.userData.actorId=actor.actorId;root.userData.team=actor.team;actorSlots.set(actor.actorId,root);models.get(root).bind(actor);root.visible=true;}
  }
  function sync(state,aspect=16/9) {
    if(disposed)return;
    const actors=state.actors||[],time=Number(state.elapsed)||0;
    const dt=previousTime===null?0:clamp(time-previousTime,0,.4);
    reconcile(actors);userRing.visible=false;pointer.visible=false;
    for(const actor of actors){const root=actorSlots.get(actor.actorId);if(!root)continue;
      root.position.copy(pitchToWorld(actor.x,actor.y));
      root.rotation.y=Math.atan2(Math.sin(actor.heading||0)*.68,Math.cos(actor.heading||0)*1.05);
      models.get(root).pose(actor,reducedMotion?0:time);
      if(actor.isUser){userRing.visible=true;pointer.visible=true;userRing.position.copy(root.position);userRing.position.y=GRASS_Y+.018;pointer.position.copy(root.position);pointer.position.y+=2.1;}
    }
    const bs=state.ball||{x:50,y:50,height:0},world=pitchToWorld(bs.x,bs.y,BALL_RADIUS+Math.max(0,Number(bs.height)||0));
    if(previousBall && dt>0 && bs.state!=='KEEPER_HELD'){
      const dx=world.x-previousBall.x,dz=world.z-previousBall.z;
      // A revealed restart can reposition the ball. Do not spin it hundreds of turns.
      if(Math.hypot(dx,dz)<8){ball.rotateZ(-dx/BALL_RADIUS);ball.rotateX(dz/BALL_RADIUS);}
    }
    ball.position.copy(world);previousBall=world.clone();
    ballShadow.position.set(world.x,GRASS_Y+.009,world.z);ballShadow.material.opacity=.32/(1+(Number(bs.height)||0)*.35);
    camera.aspect=Math.max(.35,aspect);camera.fov=cameraMode==='wide'?46:43;camera.updateProjectionMatrix();
    const wanted=new THREE.Vector3(cameraMode==='wide'?0:clamp(world.x*.72,-35,35),0,cameraMode==='wide'?0:clamp(world.z*.18,-5,5));
    if(cameraReset||previousTime===null){target.copy(wanted);cameraReset=false;}else if(dt>0)target.lerp(wanted,1-Math.exp(-dt*2.4));
    const narrow=Math.max(1,Math.min(1.65,1.4/camera.aspect));
    camera.position.set(target.x+(cameraMode==='wide'?0:9),(cameraMode==='wide'?76:43)*narrow,(cameraMode==='wide'?79:57)*narrow+target.z);
    camera.lookAt(target.x,0,target.z);camera.updateMatrixWorld(true);
    previousTime=time;
  }
  function setCameraMode(mode){cameraMode=mode==='wide'?'wide':'broadcast';cameraReset=true;}
  function dispose(){
    if(disposed)return;disposed=true;
    const geometries=new Set(),materials=new Set(),textures=new Set();
    scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m)materials.add(m);});
    for(const m of materials)for(const v of Object.values(m))if(v?.isTexture)textures.add(v);
    textures.forEach(t=>t.dispose());materials.forEach(m=>m.dispose());geometries.forEach(g=>g.dispose());actorSlots.clear();
  }
  return {scene,camera,actorSlots,ball,userRing,sync,setCameraMode,dispose};
}
