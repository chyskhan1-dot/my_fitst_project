// Музыка квиза: всё играется синтезатором браузера (Web Audio), без чужих файлов.
// Для каждого этапа игры есть несколько стилей; при каждом включении выбирается
// случайный (не тот, что звучал только что) и чуть сдвигается тональность.
//   lobby    — лоу-фай, босса-нова, спокойное пианино
//   question — синтвейв, фанк, напряжённый пульс, латино (на последних 5 с — напряжение)
//   leaders  — хаус, диско, хип-хоп
//   final    — гимн, праздник
// Плюс короткие сигналы и проигрывание мелодий разными инструментами.
(function () {
  const KEY = "quiz-sound";
  let ctx = null, master, musicBus, sfxBus, reverb, noise;
  let muted = (() => { try { return localStorage.getItem(KEY) === "off"; } catch { return false; } })();
  let mood = null, style = null, timer = null, step = 0, nextTime = 0, tension = false, shift = 0;
  const lastStyle = {};
  let melodyNodes = [];

  // ---------- ноты ----------
  const NOTES = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  function midi(name) {
    const m = /^([A-G])([#b]?)(\d)$/.exec(name);
    return NOTES[m[1]] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0) + (Number(m[3]) + 1) * 12;
  }
  const hz = (n) => 440 * Math.pow(2, (n - 69) / 12);
  const f = (name, oct = 0) => hz(midi(name) + shift + oct * 12); // с учётом сдвига тональности

  function unlock() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = muted ? 0 : 1; master.connect(ctx.destination);
      const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 4;
      comp.connect(master);
      musicBus = ctx.createGain(); musicBus.gain.value = 0.36; musicBus.connect(comp);
      sfxBus = ctx.createGain(); sfxBus.gain.value = 0.55; sfxBus.connect(comp);
      // эхо зала: свёртка со сгенерированным затухающим шумом
      reverb = ctx.createConvolver();
      const len = ctx.sampleRate * 1.8, ir = ctx.createBuffer(2, len, ctx.sampleRate);
      for (let c = 0; c < 2; c++) {
        const d = ir.getChannelData(c);
        for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.5);
      }
      reverb.buffer = ir;
      const wet = ctx.createGain(); wet.gain.value = 0.22;
      reverb.connect(wet); wet.connect(comp);
      noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const d = noise.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ctx.state === "suspended") ctx.resume().then(() => { if (mood && !timer) begin(); }).catch(() => {});
    return ctx.state === "running";
  }
  const ready = () => ctx && ctx.state === "running";

  // ---------- строительные блоки ----------
  function out(bus, node, wet = 0.4) {
    node.connect(bus);
    if (wet && reverb) { const s = ctx.createGain(); s.gain.value = wet; node.connect(s); s.connect(reverb); }
  }
  function adsr(g, t, a, peak, hold, rel) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + a);
    g.gain.setValueAtTime(peak, t + a + hold);
    g.gain.exponentialRampToValueAtTime(0.0001, t + a + hold + rel);
    return t + a + hold + rel;
  }
  function osc(type, freq, t, end) {
    const o = ctx.createOscillator(); o.type = type; o.frequency.value = freq;
    o.start(t); o.stop(end + 0.05); return o;
  }
  function lowpass(freq, q = 0.7) { const b = ctx.createBiquadFilter(); b.type = "lowpass"; b.frequency.value = freq; b.Q.value = q; return b; }

  // ---------- инструменты (bus — куда, v — громкость 0..1) ----------
  const I = {
    piano(bus, freq, t, d, v = 0.6) {
      const g = ctx.createGain(); out(bus, g, 0.35);
      const end = t + Math.min(d + 0.8, 3);
      [[1, 1], [2, 0.45], [3, 0.2], [4, 0.1], [6, 0.04]].forEach(([k, a], i) => {
        const pg = ctx.createGain();
        pg.gain.setValueAtTime(0.0001, t);
        pg.gain.exponentialRampToValueAtTime(a * v * 0.16, t + 0.004);
        pg.gain.exponentialRampToValueAtTime(0.0001, t + Math.min(d + 0.8, 3) / (1 + i * 0.6));
        osc("sine", freq * k * (1 + i * 0.0007), t, end).connect(pg); pg.connect(g);
      });
      return g;
    },
    epiano(bus, freq, t, d, v = 0.6) {
      const g = ctx.createGain(); out(bus, g, 0.3);
      const end = adsr(g, t, 0.005, v * 0.14, Math.max(0.05, d * 0.5), 1.0);
      const car = osc("sine", freq, t, end), mod = osc("sine", freq, t, end), mg = ctx.createGain();
      mg.gain.setValueAtTime(freq * 1.8, t); mg.gain.exponentialRampToValueAtTime(freq * 0.15, t + 0.6);
      mod.connect(mg); mg.connect(car.frequency); car.connect(g);
      const bell = ctx.createGain(); bell.gain.setValueAtTime(v * 0.03, t); bell.gain.exponentialRampToValueAtTime(0.0001, t + 0.4);
      osc("sine", freq * 4, t, t + 0.5).connect(bell); bell.connect(g);
      return g;
    },
    strings(bus, freq, t, d, v = 0.5) {
      const g = ctx.createGain(), lp = lowpass(1700); lp.connect(g); out(bus, g, 0.5);
      const end = adsr(g, t, 0.35, v * 0.05, Math.max(0, d - 0.35), 0.6);
      [-8, 0, 7].forEach((cents) => { const o = osc("sawtooth", freq, t, end); o.detune.value = cents; o.connect(lp); });
      return g;
    },
    pluck(bus, freq, t, d, v = 0.6) { // гитара / щипок
      const g = ctx.createGain(), lp = lowpass(3500, 2); lp.connect(g); out(bus, g, 0.3);
      lp.frequency.setValueAtTime(3500, t); lp.frequency.exponentialRampToValueAtTime(500, t + 0.35);
      const end = adsr(g, t, 0.003, v * 0.15, 0.02, Math.min(0.6, d + 0.3));
      osc("sawtooth", freq, t, end).connect(lp); osc("triangle", freq * 2, t, end).connect(lp);
      return g;
    },
    marimba(bus, freq, t, d, v = 0.6) {
      const g = ctx.createGain(); out(bus, g, 0.3);
      const end = adsr(g, t, 0.002, v * 0.22, 0.01, 0.5);
      osc("sine", freq, t, end).connect(g);
      const h = ctx.createGain(); h.gain.setValueAtTime(v * 0.06, t); h.gain.exponentialRampToValueAtTime(0.0001, t + 0.12);
      osc("sine", freq * 4, t, t + 0.15).connect(h); h.connect(g);
      return g;
    },
    flute(bus, freq, t, d, v = 0.6) {
      const g = ctx.createGain(); out(bus, g, 0.45);
      const end = adsr(g, t, 0.06, v * 0.16, Math.max(0, d - 0.1), 0.15);
      const o = osc("sine", freq, t, end), lfo = osc("sine", 5.2, t, end), lg = ctx.createGain();
      lg.gain.setValueAtTime(0, t); lg.gain.linearRampToValueAtTime(freq * 0.006, t + 0.3);
      lfo.connect(lg); lg.connect(o.frequency); o.connect(g);
      const h = ctx.createGain(); h.gain.value = 0.15; osc("sine", freq * 2, t, end).connect(h); h.connect(g);
      return g;
    },
    clav(bus, freq, t, d, v = 0.6) {
      const g = ctx.createGain(), bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 1400; bp.Q.value = 1.5;
      bp.connect(g); out(bus, g, 0.15);
      const end = adsr(g, t, 0.002, v * 0.2, 0.01, 0.16);
      osc("square", freq, t, end).connect(bp);
      return g;
    },
    synth(bus, freq, t, d, v = 0.6) { // синтвейв-арпеджио
      const g = ctx.createGain(), lp = lowpass(2600, 3); lp.connect(g); out(bus, g, 0.35);
      const end = adsr(g, t, 0.004, v * 0.09, Math.max(0, d * 0.6), 0.12);
      const a = osc("sawtooth", freq, t, end), b = osc("sawtooth", freq, t, end); b.detune.value = 12;
      a.connect(lp); b.connect(lp);
      return g;
    },
    bass(bus, freq, t, d, v = 0.7) { // синтезаторный бас
      const g = ctx.createGain(), lp = lowpass(900, 4); lp.connect(g); out(bus, g, 0);
      lp.frequency.setValueAtTime(900, t); lp.frequency.exponentialRampToValueAtTime(220, t + 0.25);
      const end = adsr(g, t, 0.005, v * 0.32, Math.max(0.02, d * 0.7), 0.08);
      osc("sawtooth", freq, t, end).connect(lp); osc("sine", freq, t, end).connect(g);
      return g;
    },
    sub(bus, freq, t, d, v = 0.7) {
      const g = ctx.createGain(); out(bus, g, 0);
      const end = adsr(g, t, 0.01, v * 0.4, Math.max(0.02, d * 0.8), 0.1);
      osc("sine", freq, t, end).connect(g);
      return g;
    },
  };

  // ---------- ударные ----------
  function hiss(t, dur, peak, type, freq, q = 1, wet = 0.1) {
    const s = ctx.createBufferSource(), flt = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = noise; s.playbackRate.value = 0.8 + Math.random() * 0.4;
    flt.type = type; flt.frequency.value = freq; flt.Q.value = q;
    s.connect(flt); flt.connect(g); out(musicBus, g, wet);
    adsr(g, t, 0.001, peak, 0, dur);
    s.start(t); s.stop(t + dur + 0.05);
  }
  const D = {
    kick(t, v = 1) {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(40, t + 0.12);
      o.connect(g); out(musicBus, g, 0); adsr(g, t, 0.002, 0.9 * v, 0.02, 0.22);
      o.start(t); o.stop(t + 0.3);
    },
    snare(t, v = 1) {
      hiss(t, 0.18, 0.32 * v, "bandpass", 1900, 0.8, 0.25);
      const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.setValueAtTime(220, t); o.frequency.exponentialRampToValueAtTime(150, t + 0.08);
      o.connect(g); out(musicBus, g, 0.2); adsr(g, t, 0.001, 0.25 * v, 0, 0.1); o.start(t); o.stop(t + 0.15);
    },
    rim(t, v = 1) { hiss(t, 0.03, 0.25 * v, "highpass", 2500, 1, 0.2); },
    clap(t, v = 1) { [0, 0.012, 0.024].forEach((dt, i) => hiss(t + dt, i === 2 ? 0.16 : 0.02, 0.28 * v, "bandpass", 1300, 1.2, 0.3)); },
    hat(t, v = 1) { hiss(t, 0.035, 0.1 * v, "highpass", 8000, 1, 0.05); },
    open(t, v = 1) { hiss(t, 0.22, 0.08 * v, "highpass", 7000, 1, 0.1); },
    shaker(t, v = 1) { hiss(t, 0.05, 0.05 * v, "highpass", 5500, 1, 0.05); },
    conga(t, high, v = 1) {
      const o = ctx.createOscillator(), g = ctx.createGain(), fr = high ? 330 : 220;
      o.frequency.setValueAtTime(fr * 1.3, t); o.frequency.exponentialRampToValueAtTime(fr, t + 0.03);
      o.connect(g); out(musicBus, g, 0.2); adsr(g, t, 0.002, 0.3 * v, 0, 0.18); o.start(t); o.stop(t + 0.25);
    },
    tick(t, v = 1) {
      const o = ctx.createOscillator(), g = ctx.createGain(); o.type = "square"; o.frequency.value = 1700;
      o.connect(g); out(musicBus, g, 0); adsr(g, t, 0.001, 0.05 * v, 0, 0.025); o.start(t); o.stop(t + 0.05);
    },
  };

  // ---------- стили: play(t, шаг 0..15, номер такта, аккорд, длина шага) ----------
  const chord = (bus, inst, notes, t, d, v, oct = 0) => notes.forEach((n) => I[inst](bus, f(n, oct), t, d, v));
  const at = (s, list) => list.includes(s);
  const STYLES = {
    lobby: [
      { name: "лоу-фай", bpm: 82, swing: 0.18,
        chords: [["D3", "F3", "A3", "C4"], ["G3", "B3", "D4", "F4"], ["C3", "E3", "G3", "B3"], ["A2", "C3", "E3", "G3"]],
        play(t, s, bar, ch, L) {
          if (s === 0 || s === 10) chord(musicBus, "epiano", ch, t, L * 8, 0.45, 1);
          if (at(s, [0, 7, 10])) I.sub(musicBus, f(ch[0], -1), t, L * 3);
          if (at(s, [0, 7, 10])) D.kick(t, 0.6);
          if (at(s, [4, 12])) D.rim(t, 0.8);
          if (s % 2 === 0) D.hat(t, s % 4 ? 0.5 : 0.8);
          if (bar % 2 === 1 && at(s, [12, 14])) I.epiano(musicBus, f(ch[3], 1), t, L * 2, 0.3);
        } },
      { name: "босса-нова", bpm: 118, swing: 0,
        chords: [["A2", "C3", "E3", "G3"], ["D3", "F#3", "A3", "C4"], ["G2", "B2", "D3", "F#3"], ["C3", "E3", "G3", "B3"]],
        play(t, s, bar, ch, L) {
          if (at(s, [0, 3, 6, 10, 13])) chord(musicBus, "pluck", ch.slice(1), t, L * 2, 0.35, 1);
          if (s === 0) I.sub(musicBus, f(ch[0], -1), t, L * 5);
          if (s === 6) I.sub(musicBus, f(ch[2], -1), t, L * 2);
          if (s === 8) I.sub(musicBus, f(ch[0], -1), t, L * 5);
          if (s === 14) I.sub(musicBus, f(ch[2], -1), t, L * 2);
          D.shaker(t, s % 2 ? 0.5 : 0.9);
          if (at(s, [3, 6, 10, 13])) D.rim(t, 0.6);
          if (at(s, [0, 8])) D.kick(t, 0.4);
        } },
      { name: "пианино", bpm: 92, swing: 0,
        chords: [["F3", "A3", "C4"], ["C3", "E3", "G3"], ["D3", "F3", "A3"], ["A#2", "D3", "F3"]],
        play(t, s, bar, ch, L) {
          if (s === 0) { I.piano(musicBus, f(ch[0], -1), t, L * 16, 0.5); chord(musicBus, "strings", ch, t, L * 16, 0.4); }
          if (s % 2 === 0) I.piano(musicBus, f([...ch, ch[1], ch[2]][(s / 2) % 5], 1), t, L * 2, 0.35);
          if (s === 14 && bar === 3) I.piano(musicBus, f(ch[2], 2), t, L * 2, 0.3);
        } },
    ],
    question: [
      { name: "синтвейв", bpm: 116, swing: 0,
        chords: [["A2", "C3", "E3"], ["F2", "A2", "C3"], ["C3", "E3", "G3"], ["G2", "B2", "D3"]],
        play(t, s, bar, ch, L) {
          if (s === 0) chord(musicBus, "strings", ch, t, L * 16, 0.5, 1);
          if (s % 2 === 0) I.bass(musicBus, f(ch[0], s % 4 ? 0 : -1), t, L * 1.5, 0.7);
          I.synth(musicBus, f([ch[0], ch[1], ch[2], ch[1]][s % 4], 2), t, L * 0.9, tension ? 0.7 : 0.45);
          if (s % 4 === 0) D.kick(t);
          if (at(s, [4, 12])) D.snare(t, 0.8);
          if (s % 4 === 2) D.hat(t);
          if (tension) D.hat(t, 0.6);
        } },
      { name: "фанк", bpm: 106, swing: 0.08,
        chords: [["E3", "G#3", "D4", "F#4"], ["E3", "G#3", "D4", "F#4"], ["A2", "C#3", "G3", "B3"], ["B2", "D#3", "A3", "C#4"]],
        play(t, s, bar, ch, L) {
          if (at(s, [0, 3, 6, 7, 10, 14])) I.bass(musicBus, f(ch[0], s === 7 ? 0 : -1), t, L * 0.9, 0.8);
          if (at(s, [2, 6, 10, 13])) chord(musicBus, "clav", ch.slice(1), t, L, 0.5, 1);
          if (at(s, [0, 6, 10])) D.kick(t);
          if (at(s, [4, 12])) D.snare(t);
          D.hat(t, s % 2 ? 0.5 : 0.9);
          if (tension && s % 2 === 1) D.open(t, 0.5);
        } },
      { name: "напряжение", bpm: 124, swing: 0,
        chords: [["A2", "C3", "E3"], ["A2", "C3", "E3"], ["F2", "A2", "C3"], ["E2", "G#2", "B2"]],
        play(t, s, bar, ch, L) {
          if (s === 0) chord(musicBus, "strings", ch, t, L * 16, 0.6, 1);
          if (s % 2 === 0) I.bass(musicBus, f(ch[0], -1), t, L * 1.2, 0.7);
          if (at(s, [3, 11])) I.pluck(musicBus, f(ch[2], 1), t, L, 0.4);
          if (s % 8 === 0) D.kick(t);
          if (s % 4 === 0) D.tick(t, tension ? 1.3 : 0.8);
          if (tension) D.hat(t, 0.7); else if (s % 2 === 0) D.shaker(t);
        } },
      { name: "латино", bpm: 110, swing: 0,
        chords: [["A2", "C3", "E3"], ["D3", "F3", "A3"], ["G2", "B2", "D3"], ["E2", "G#2", "B2"]],
        play(t, s, bar, ch, L) {
          // монтуно: пианино играет синкопированный рисунок
          if (at(s, [0, 3, 6, 8, 10, 12, 14])) chord(musicBus, "piano", s % 4 === 2 ? ch.slice(1) : [ch[0], ch[2]], t, L * 1.2, 0.35, 1);
          if (at(s, [0, 6, 8, 14])) I.sub(musicBus, f(ch[s === 6 || s === 14 ? 2 : 0], -1), t, L * 2);
          if (at(s, [3, 6, 10, 12])) D.rim(t, 0.6);
          if (at(s, [7, 14])) D.conga(t, false); if (at(s, [2, 10, 15])) D.conga(t, true);
          D.shaker(t, s % 2 ? 0.4 : 0.8);
          if (tension && s % 4 === 0) D.kick(t, 0.8);
        } },
    ],
    leaders: [
      { name: "хаус", bpm: 122, swing: 0,
        chords: [["C3", "E3", "G3", "B3"], ["A2", "C3", "E3", "G3"], ["F2", "A2", "C3", "E3"], ["G2", "B2", "D3", "F3"]],
        play(t, s, bar, ch, L) {
          if (s % 4 === 0) D.kick(t);
          if (s % 4 === 2) { D.open(t); I.bass(musicBus, f(ch[0], -1), t, L * 1.5, 0.7); }
          if (at(s, [4, 12])) D.clap(t);
          if (at(s, [2, 5, 10, 13])) chord(musicBus, "piano", ch.slice(1), t, L * 1.5, 0.4, 1);
          D.hat(t, 0.3);
        } },
      { name: "диско", bpm: 116, swing: 0,
        chords: [["D3", "F3", "A3"], ["G2", "B2", "D3"], ["C3", "E3", "G3"], ["A2", "C#3", "E3"]],
        play(t, s, bar, ch, L) {
          if (s % 2 === 0) I.bass(musicBus, f(ch[0], s % 4 ? 0 : -1), t, L * 1.6, 0.75);
          if (s % 4 === 0) D.kick(t);
          if (at(s, [4, 12])) D.snare(t, 0.8);
          if (s % 4 === 2) D.open(t, 0.8); else D.hat(t, 0.5);
          if (s === 0) chord(musicBus, "strings", ch, t, L * 6, 0.6, 1);
          if (at(s, [6, 7])) chord(musicBus, "strings", ch, t, L * 0.8, 0.6, 1);
          if (at(s, [10, 14])) chord(musicBus, "clav", ch, t, L, 0.4, 1);
        } },
      { name: "хип-хоп", bpm: 90, swing: 0.2,
        chords: [["C3", "E3", "G3", "B3"], ["A2", "C3", "E3", "G3"], ["D3", "F3", "A3", "C4"], ["G2", "B2", "D3", "F3"]],
        play(t, s, bar, ch, L) {
          if (at(s, [0, 7, 10])) D.kick(t);
          if (at(s, [4, 12])) D.snare(t);
          if (s % 2 === 0) D.hat(t, s % 4 ? 0.5 : 0.9);
          if (s === 0) chord(musicBus, "epiano", ch, t, L * 10, 0.45, 1);
          if (s === 11) chord(musicBus, "epiano", ch.slice(1), t, L * 4, 0.35, 1);
          if (at(s, [0, 7, 10])) I.sub(musicBus, f(ch[0], -1), t, L * 3);
        } },
    ],
    final: [
      { name: "гимн", bpm: 100, swing: 0,
        chords: [["C3", "E3", "G3"], ["G2", "B2", "D3"], ["A2", "C3", "E3"], ["F2", "A2", "C3"]],
        play(t, s, bar, ch, L) {
          if (s === 0) { chord(musicBus, "strings", ch, t, L * 16, 0.7, 1); I.sub(musicBus, f(ch[0], -1), t, L * 15); }
          if (s % 4 === 0) D.kick(t);
          if (at(s, [4, 12])) D.snare(t);
          if (s % 2 === 0) I.piano(musicBus, f([ch[0], ch[1], ch[2], ch[1]][(s / 2) % 4], 1), t, L * 2, 0.4);
          const tune = [["E4", "G4"], ["D4", "B3"], ["C4", "E4"], ["C4", "A3"]][bar];
          if (s === 0 || s === 8) I.piano(musicBus, f(tune[s ? 1 : 0], 1), t, L * 7, 0.6);
        } },
      { name: "праздник", bpm: 128, swing: 0,
        chords: [["F3", "A3", "C4"], ["C3", "E3", "G3"], ["D3", "F3", "A3"], ["A#2", "D3", "F3"]],
        play(t, s, bar, ch, L) {
          if (s % 4 === 0) D.kick(t);
          if (at(s, [4, 12])) D.clap(t);
          D.hat(t, s % 2 ? 0.4 : 0.8);
          if (s % 2 === 0) I.bass(musicBus, f(ch[0], s % 4 ? 0 : -1), t, L * 1.5, 0.7);
          if (at(s, [0, 3, 6, 8, 11, 14])) I.marimba(musicBus, f(ch[[0, 1, 2, 1, 2, 0][[0, 3, 6, 8, 11, 14].indexOf(s)]], 2), t, L, 0.5);
          if (s === 0) chord(musicBus, "strings", ch, t, L * 16, 0.5, 1);
        } },
    ],
  };

  function tick() {
    if (!style || !ready()) return;
    const L = 60 / style.bpm / 4;
    while (nextTime < ctx.currentTime + 0.15) {
      const s = step % 16, bar = Math.floor(step / 16) % style.chords.length;
      const t = nextTime + (s % 4 === 2 ? style.swing * L : 0); // свинг: «и» чуть позже
      style.play(t, s, bar, style.chords[bar], L);
      nextTime += L; step++;
    }
  }

  function begin() {
    if (!mood || !ready()) return;
    const list = STYLES[mood];
    const options = list.length > 1 ? list.filter((x) => x !== lastStyle[mood]) : list;
    style = options[Math.floor(Math.random() * options.length)];
    lastStyle[mood] = style;
    shift = Math.floor(Math.random() * 5) - 2; // другая тональность для разнообразия
    musicBus.gain.cancelScheduledValues(ctx.currentTime);
    musicBus.gain.setValueAtTime(0.36, ctx.currentTime);
    step = 0; nextTime = ctx.currentTime + 0.05;
    clearInterval(timer); timer = setInterval(tick, 25); tick();
  }

  function play(name) {
    if (name === mood) return;
    stop(0.4);
    mood = name; tension = false;
    unlock();
    // новая тема чуть позже, чтобы старая успела затихнуть; если звук ещё не разрешён,
    // тема начнётся после первого нажатия (см. unlock)
    setTimeout(() => { if (mood === name && !timer) begin(); }, 420);
  }

  function stop(fade = 0.5) {
    mood = null; style = null;
    clearInterval(timer); timer = null;
    if (ready()) {
      const g = musicBus.gain, t = ctx.currentTime;
      g.cancelScheduledValues(t); g.setValueAtTime(g.value, t); g.linearRampToValueAtTime(0, t + fade);
    }
  }

  function setTension(on) { tension = !!on; }

  function sting(name) {
    if (!unlock() && !ready()) return;
    const t = ctx.currentTime + 0.02, keep = shift;
    shift = 0;
    const seq = {
      reveal: [["C5", 0], ["E5", 0.08], ["G5", 0.16], ["C6", 0.24]],
      start: [["G4", 0], ["C5", 0.1], ["E5", 0.2]],
      fanfare: [["C5", 0], ["C5", 0.15], ["C5", 0.3], ["G5", 0.48], ["E5", 0.78], ["G5", 0.93], ["C6", 1.08]],
    }[name] || [];
    for (const [n, dt] of seq) { I.marimba(sfxBus, f(n), t + dt, 0.3, 0.8); I.piano(sfxBus, f(n), t + dt, 0.4, 0.5); }
    if (name === "fanfare") { ["C4", "E4", "G4", "C5"].forEach((n) => I.strings(sfxBus, f(n), t + 1.08, 2, 0.9)); D.kick(t + 1.08); }
    if (name === "start") D.open(t + 0.2, 1);
    shift = keep;
  }

  // Мелодия из нот «E4 E4 F4 G4:2 R:1»; длительность — в долях, темп — удары в минуту.
  // instrument: piano, epiano, marimba, flute, strings, pluck, synth (по умолчанию пианино)
  const MELODY_INSTRUMENTS = ["piano", "epiano", "marimba", "flute", "strings", "pluck"];
  function melody(notes, tempo = 110, instrument = "piano") {
    stopMelody();
    if (!unlock() && !ready()) return 0;
    const inst = I[instrument] ? instrument : "piano";
    const beat = 60 / tempo;
    let t = ctx.currentTime + 0.15;
    for (const tok of String(notes).split(/\s+/).filter(Boolean)) {
      const [n, d] = tok.split(":");
      const dur = (d ? Number(d) : 1) * beat;
      if (n !== "R") melodyNodes.push(I[inst](sfxBus, hz(midi(n)), t, dur * 0.95, 0.8));
      t += dur;
    }
    return t - ctx.currentTime;
  }
  function stopMelody() {
    for (const g of melodyNodes) {
      try { g.gain.cancelScheduledValues(ctx.currentTime); g.gain.setTargetAtTime(0, ctx.currentTime, 0.03); } catch {}
    }
    melodyNodes = [];
  }

  function setMuted(v) {
    muted = v;
    try { localStorage.setItem(KEY, v ? "off" : "on"); } catch {}
    if (ctx) master.gain.setTargetAtTime(v ? 0 : 1, ctx.currentTime, 0.05);
  }

  window.QuizMusic = {
    unlock, play, stop, sting, setTension, melody, stopMelody, MELODY_INSTRUMENTS,
    get muted() { return muted; },
    get blocked() { return !ready(); },
    get styleName() { return style ? style.name : null; },
    toggle() { setMuted(!muted); unlock(); return muted; },
  };
})();
