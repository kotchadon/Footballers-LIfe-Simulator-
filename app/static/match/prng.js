export function createPrng(seed) {
  let state = Number(seed) >>> 0;
  return function next() {
    state = (state + 0x6D2B79F5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function sampleSeed(seed, ...parts) {
  let value = Number(seed) >>> 0;
  for (const part of parts) {
    for (const char of String(part)) {
      value = Math.imul(value ^ char.charCodeAt(0), 16777619) >>> 0;
    }
  }
  return value >>> 0;
}
