// Музыка квиза: всё играется синтезатором браузера (Web Audio), без чужих файлов.
// Настроения: lobby — спокойный грув, question — напряжённый пульс (с ускорением в конце),
// leaders — бодрый ритм, final — торжественная тема. Плюс короткие звуки-сигналы и
// проигрывание мелодий для раунда «Угадай мелодию».
(function () {
  const KEY = "quiz-sound";
  let ctx = null, master, musicBus, sfxBus, noise;
  let muted = (() => { try { return localStorage.getItem(KEY) === "off"; } catch { return false; } })();
  let mood = null, timer = null, step = 0, nextTime = 0, tension = false;
  let melodyNodes = [];

  const NOTES = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  function freq(name) {
    const m = /^([A-G])([#b]?)(\d)$/.exec(name);
    const semis = NOTES[m[1]] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0) + (Number(m[3]) + 1) * 12;
    return 440 * Math.pow(2, (semis - 69) / 12);
  }

  function unlock() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = muted ? 0 : 1; master.connect(ctx.destination);
      musicBus = ctx.createGain(); musicBus.gain.value = 0.32; musicBus.connect(master);
      sfxBus = ctx.createGain(); sfxBus.gain.value = 0.5; sfxBus.connect(master);
      noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const d = noise.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ctx.state === "suspended") ctx.resume().then(() => { if (mood && !timer) begin(); }).catch(() => {});
    return ctx.state === "running";
  }
  const ready = () => ctx && ctx.state === "running";

  // ---------- инструменты ----------
  function env(g, t, a, peak, dur, rel) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + a);
    g.gain.setValueAtTime(peak, t + Math.max(a, dur - rel));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  }
  function tone(bus, type, f, t, dur, peak, a = 0.01, rel = 0.1, cutoff = 0) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.value = f;
    let out = o;
    if (cutoff) { const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = cutoff; o.connect(lp); out = lp; }
    out.connect(g); g.connect(bus);
    env(g, t, a, peak, dur, Math.min(rel, dur * 0.8));
    o.start(t); o.stop(t + dur + 0.05);
    return o;
  }
  const pad = (n, t, dur) => { tone(musicBus, "sawtooth", freq(n), t, dur, 0.035, 0.25, 0.4, 1100); tone(musicBus, "sawtooth", freq(n) * 1.004, t, dur, 0.03, 0.25, 0.4, 1100); };
  const pluck = (n, t, peak = 0.12) => tone(musicBus, "triangle", freq(n), t, 0.28, peak, 0.005, 0.25);
  const bass = (n, t, dur) => tone(musicBus, "triangle", freq(n) / 2, t, dur, 0.28, 0.01, 0.08);
  function kick(t, peak = 0.7) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(42, t + 0.14);
    o.connect(g); g.connect(musicBus); env(g, t, 0.003, peak, 0.22, 0.18);
    o.start(t); o.stop(t + 0.25);
  }
  function hiss(bus, t, dur, peak, type, f) {
    const s = ctx.createBufferSource(), flt = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = noise; flt.type = type; flt.frequency.value = f;
    s.connect(flt); flt.connect(g); g.connect(bus); env(g, t, 0.002, peak, dur, dur * 0.9);
    s.start(t); s.stop(t + dur + 0.02);
  }
  const hat = (t, peak = 0.08) => hiss(musicBus, t, 0.05, peak, "highpass", 7500);
  const clap = (t) => hiss(musicBus, t, 0.14, 0.22, "bandpass", 1600);

  // ---------- настроения: 16 шагов (шестнадцатых) на такт, 4 такта ----------
  const MOODS = {
    lobby: { bpm: 96, chords: [["A3", "C4", "E4"], ["F3", "A3", "C4"], ["C4", "E4", "G4"], ["G3", "B3", "D4"]],
      play(t, s, bar, ch, len) {
        if (s === 0) { ch.forEach((n) => pad(n, t, len * 16 * 0.98)); bass(ch[0], t, len * 6); }
        if (s === 8) bass(ch[0], t, len * 6);
        if (s % 4 === 2) pluck(ch[(s / 2 | 0) % 3].replace(/\d/, (o) => +o + 1), t, 0.07);
        if (s % 4 === 2) hat(t, 0.05);
        if (s === 0 || s === 10) kick(t, 0.35);
      } },
    question: { bpm: 124, chords: [["A3", "C4", "E4"], ["A3", "C4", "E4"], ["F3", "A3", "C4"], ["E3", "G#3", "B3"]],
      play(t, s, bar, ch, len) {
        if (s === 0) ch.forEach((n) => pad(n, t, len * 16 * 0.98));
        if (s % 2 === 0) bass(ch[0], t, len * 1.6);
        if (s % 4 === 0) tone(musicBus, "square", tension ? 1760 : 1320, t, 0.03, tension ? 0.05 : 0.03, 0.002, 0.02); // «тик»
        if (tension) { hat(t, 0.06); if (s % 2 === 1) pluck(ch[2].replace(/\d/, (o) => +o + 1), t, 0.05); }
        else if (s % 2 === 0) hat(t, 0.035);
        if (s % 8 === 0) kick(t, tension ? 0.55 : 0.4);
      } },
    leaders: { bpm: 116, chords: [["C4", "E4", "G4"], ["G3", "B3", "D4"], ["A3", "C4", "E4"], ["F3", "A3", "C4"]],
      play(t, s, bar, ch, len) {
        if (s === 0) ch.forEach((n) => pad(n, t, len * 16 * 0.98));
        if (s % 4 === 0) kick(t, 0.6);
        if (s === 4 || s === 12) clap(t);
        if (s % 2 === 1) hat(t, 0.06);
        if ([0, 3, 6, 8, 11, 14].includes(s)) bass(ch[0], t, len * 1.8);
        if (s % 2 === 0) pluck([...ch, ch[1]][(s / 2) % 4].replace(/\d/, (o) => +o + 1), t, 0.06);
      } },
    final: { bpm: 104, chords: [["C4", "E4", "G4"], ["F3", "A3", "C4"], ["G3", "B3", "D4"], ["C4", "E4", "G4"]],
      play(t, s, bar, ch, len) {
        if (s === 0) { ch.forEach((n) => pad(n, t, len * 16 * 0.98)); pad(ch[0].replace(/\d/, (o) => +o + 1), t, len * 16); }
        if (s % 4 === 0) kick(t, 0.55);
        if (s === 4 || s === 12) clap(t);
        if (s % 4 === 2) bass(ch[0], t, len * 1.5);
        if (s % 2 === 0) pluck(ch[(s / 2) % 3].replace(/\d/, (o) => +o + 1), t, 0.07);
      } },
  };

  function tick() {
    const m = MOODS[mood];
    if (!m || !ready()) return;
    const len = 60 / m.bpm / 4;
    while (nextTime < ctx.currentTime + 0.15) {
      const bar = Math.floor(step / 16) % m.chords.length;
      m.play(nextTime, step % 16, bar, m.chords[bar], len);
      nextTime += len; step++;
    }
  }

  function begin() {
    if (!mood || !ready()) return;
    musicBus.gain.cancelScheduledValues(ctx.currentTime);
    musicBus.gain.setValueAtTime(0.32, ctx.currentTime);
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
    mood = null;
    clearInterval(timer); timer = null;
    if (ready()) {
      const g = musicBus.gain, t = ctx.currentTime;
      g.cancelScheduledValues(t); g.setValueAtTime(g.value, t); g.linearRampToValueAtTime(0, t + fade);
    }
  }

  function setTension(on) { tension = !!on; }

  function sting(name) {
    if (!unlock() && !ready()) return;
    const t = ctx.currentTime + 0.02;
    const seq = {
      reveal: [["C5", 0], ["E5", 0.09], ["G5", 0.18], ["C6", 0.27]],
      start: [["G4", 0], ["C5", 0.12], ["E5", 0.24]],
      fanfare: [["C5", 0], ["C5", 0.16], ["C5", 0.32], ["G5", 0.5], ["E5", 0.8], ["G5", 0.95], ["C6", 1.1]],
      join: [["E5", 0], ["A5", 0.07]],
    }[name] || [];
    for (const [n, dt] of seq) {
      tone(sfxBus, "triangle", freq(n), t + dt, name === "fanfare" ? 0.5 : 0.35, 0.22, 0.005, 0.25);
      tone(sfxBus, "sine", freq(n) * 2, t + dt, 0.25, 0.06, 0.005, 0.2);
    }
    if (name === "fanfare") ["C4", "E4", "G4", "C5"].forEach((n) => tone(sfxBus, "sawtooth", freq(n), t + 1.1, 1.6, 0.05, 0.05, 0.8, 2200));
  }

  // Мелодия из нот «E4 E4 F4 G4:2 R:1»; длительность — в долях, темп — удары в минуту
  function melody(notes, tempo = 110) {
    stopMelody();
    if (!unlock() && !ready()) return 0;
    const beat = 60 / tempo;
    let t = ctx.currentTime + 0.15;
    for (const tok of String(notes).split(/\s+/).filter(Boolean)) {
      const [n, d] = tok.split(":");
      const dur = (d ? Number(d) : 1) * beat;
      if (n !== "R") {
        melodyNodes.push(tone(sfxBus, "triangle", freq(n), t, dur * 0.95, 0.3, 0.01, Math.min(0.15, dur / 2)));
        melodyNodes.push(tone(sfxBus, "sine", freq(n) * 2, t, dur * 0.9, 0.07, 0.01, Math.min(0.12, dur / 2)));
      }
      t += dur;
    }
    return t - ctx.currentTime;
  }
  function stopMelody() {
    for (const o of melodyNodes) { try { o.stop(); } catch {} }
    melodyNodes = [];
  }

  function setMuted(v) {
    muted = v;
    try { localStorage.setItem(KEY, v ? "off" : "on"); } catch {}
    if (ctx) master.gain.setTargetAtTime(v ? 0 : 1, ctx.currentTime, 0.05);
  }

  window.QuizMusic = {
    unlock, play, stop, sting, setTension, melody, stopMelody,
    get muted() { return muted; },
    get blocked() { return !ready(); },
    toggle() { setMuted(!muted); unlock(); return muted; },
  };
})();
