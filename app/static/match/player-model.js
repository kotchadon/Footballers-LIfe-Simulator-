import * as THREE from "../vendor/three/three.module.js";

export function createPlayerFactory() {
  const box = new THREE.BoxGeometry(1, 1, 1);
  const sphere = new THREE.SphereGeometry(1, 10, 8);
  const cylinder = new THREE.CylinderGeometry(1, 1, 1, 8);
  const material = color => new THREE.MeshStandardMaterial({color, roughness: .88});
  const shirts = {home: material(0x2776ef), away: material(0xe13a43), homeGK: material(0xf7b928), awayGK: material(0x87d747)};
  const shorts = {home: material(0xf1f2e9), away: material(0x182439), keeper: material(0x182439)};
  const skins = [0xdba57d, 0x8c5638, 0xc98b5b, 0x583923, 0xe9bb99].map(material);
  const hair = material(0x252021), boots = material(0x171d27), socks = material(0xe9edf2);
  function part(parent, geometry, mat, position, scale, name) {
    const m = new THREE.Mesh(geometry, mat); m.name = name;
    m.position.set(...position); m.scale.set(...scale); parent.add(m); return m;
  }
  function joint(parent, name, x, y, z) {
    const g = new THREE.Group(); g.name = name; g.position.set(x,y,z); parent.add(g); return g;
  }
  return function createPlayer(index, team) {
    const body = new THREE.Group(); body.name = "Body";
    const skin = skins[index % skins.length];
    const torso = part(body, box, shirts[team], [0,1.255,0], [.33,.49,.43], "Shirt"); torso.castShadow = true;
    const hip = part(body, box, shorts[team], [0,.91,0], [.30,.24,.34], "Shorts");
    part(body,cylinder,skin,[0,1.55,0],[.065,.12,.065],"Neck");
    const head = part(body,sphere,skin,[0,1.72,0],[.135,.17,.13],"Head"); head.castShadow = true;
    part(body,sphere,hair,[-.025,1.815,0],[.119,.085,.129],"Hair");
    part(body,sphere,skin,[.135,1.71,0],[.037,.037,.035],"Nose");
    const limbs = {};
    for (const [side,z,sign] of [["Left",-.135,-1],["Right",.135,1]]) {
      const leg=joint(body,`${side}Hip`,0,.86,z);
      part(leg,cylinder,skin,[0,-.195,0],[.077,.39,.077],`${side}Thigh`);
      const knee=joint(leg,`${side}Knee`,0,-.39,0);
      part(knee,cylinder,socks,[0,-.18,0],[.06,.36,.06],`${side}Sock`);
      part(knee,box,boots,[.055,-.405,0],[.26,.13,.125],`${side}Boot`);
      const arm=joint(body,`${side}Arm`,0,1.45,sign*.27);
      part(arm,cylinder,shirts[team],[0,-.08,0],[.08,.16,.08],`${side}Sleeve`);
      part(arm,cylinder,skin,[0,-.195,0],[.055,.23,.055],`${side}UpperArm`);
      const elbow=joint(arm,`${side}Elbow`,0,-.28,0);
      part(elbow,cylinder,skin,[0,-.11,0],[.048,.22,.048],`${side}Forearm`);
      part(elbow,sphere,skin,[0,-.24,0],[.06,.075,.05],`${side}Hand`);
      limbs[side]={leg,knee,arm,elbow};
    }
    let label=null;
    function bind(actor) {
      const keeper=actor.role==="GK";
      torso.material=shirts[keeper?`${team}GK`:team];hip.material=shorts[keeper?"keeper":team];
      body.traverse(o=>{if(o.name.endsWith('Sleeve'))o.material=torso.material;});
      if(label){body.remove(label);label.material.map.dispose();label.material.dispose();label.geometry.dispose();label=null;}
      if(typeof document!=="undefined" && typeof document.createElement==="function") {
        const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;
        const ctx=canvas.getContext('2d');
        if(ctx){ctx.fillStyle='#ffffff';ctx.font='bold 100px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(actor.shirtNumber||index+1),64,70);
          const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
          label=new THREE.Mesh(new THREE.PlaneGeometry(.25,.27),new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false}));
          label.name='ShirtNumber';label.position.set(-.168,1.275,0);label.rotation.y=-Math.PI/2;body.add(label);
        }
      }
    }
    function pose(actor,time) {
      const speed=Math.hypot((actor.vx||0)*1.05,(actor.vy||0)*.68);
      const motion=Math.min(1,speed/7.5), phase=time*(6+motion*6)+index*1.71;
      const stride=Math.sin(phase)*.55*motion;
      body.rotation.set(0,0,-.045*motion);body.position.y=0;
      for(const [side,sign] of [["Left",1],["Right",-1]]){
        const l=limbs[side];l.leg.rotation.z=sign*stride;
        l.knee.rotation.z=-Math.max(0,-sign*Math.sin(phase))*.8*motion;
        l.arm.rotation.set(0,0,-sign*stride*.75);l.elbow.rotation.z=-.2-motion*.35;
      }
      const state=String(actor.animationState||'');
      const t=Math.max(0,Math.min(1,actor.animationProgress??.5));
      if(['PASS','LONG_PASS','CROSS','SHOOT'].includes(state)){
        const kick=state==='SHOOT'?1.12:.72;
        limbs.Right.leg.rotation.z=kick*Math.sin(t*Math.PI)-.25;
        limbs.Right.knee.rotation.z=-.35*(1-t);limbs.Left.arm.rotation.z=-.55;limbs.Right.arm.rotation.z=.48;
        body.rotation.z=-.1;
      } else if(state==='RECEIVE'){limbs.Right.leg.rotation.z=.35;limbs.Right.knee.rotation.z=-.2;}
      else if(state==='GK_DIVE'){
        const dive=Math.sin(Math.PI*t);body.rotation.x=1.15*dive;body.position.y=.25*dive;
        limbs.Left.arm.rotation.x=1.9;limbs.Right.arm.rotation.x=-1.9;
      } else if(state==='GK_CATCH'){
        limbs.Left.arm.rotation.z=1.1;limbs.Right.arm.rotation.z=1.1;
      } else if(state==='CELEBRATE'){
        limbs.Left.arm.rotation.x=2.7;limbs.Right.arm.rotation.x=-2.7;
      } else if(actor.role==='GK'){
        limbs.Left.arm.rotation.x=.3;limbs.Right.arm.rotation.x=-.3;
      } else if(state==='TACKLE'||state==='STUMBLE'){
        body.rotation.z=-.65;limbs.Right.leg.rotation.z=.8;
      }
    }
    return {body,bind,pose};
  };
}
