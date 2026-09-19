export const FORMATION_ANCHORS = Object.freeze({
  "4-3-3": Object.freeze({GK:[6,50],LB:[22,16],LCB:[18,37],RCB:[18,63],RB:[22,84],DM:[38,50],LCM:[50,35],RCM:[50,65],LW:[67,18],ST:[74,50],RW:[67,82]}),
  "4-2-3-1": Object.freeze({GK:[6,50],LB:[22,16],LCB:[18,37],RCB:[18,63],RB:[22,84],LDM:[38,39],RDM:[38,61],CAM:[56,50],LW:[64,19],ST:[75,50],RW:[64,81]}),
  "4-4-2": Object.freeze({GK:[6,50],LB:[22,16],LCB:[18,37],RCB:[18,63],RB:[22,84],LM:[48,17],LCM:[46,39],RCM:[46,61],RM:[48,83],LST:[72,40],RST:[72,60]}),
  "3-5-2": Object.freeze({GK:[6,50],LCB:[19,28],CB:[17,50],RCB:[19,72],LWB:[42,10],LCM:[44,34],CM:[42,50],RCM:[44,66],RWB:[42,90],LST:[72,41],RST:[72,59]}),
});

export const TEN_MAN_SHAPES = Object.freeze({
  "4-4-1": Object.freeze({GK:[6,50],LB:[22,16],LCB:[18,37],RCB:[18,63],RB:[22,84],LM:[48,17],LCM:[46,39],RCM:[46,61],RM:[48,83],ST:[72,50]}),
});

export function formationAnchors(name, attackingDirection = 1) {
  const source = FORMATION_ANCHORS[name] || FORMATION_ANCHORS["4-3-3"];
  return Object.fromEntries(Object.entries(source).map(([role,[x,y]]) => [role,[attackingDirection < 0 ? 100 - x : x,y]]));
}
