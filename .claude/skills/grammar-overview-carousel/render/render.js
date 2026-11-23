#!/usr/bin/env node
// 지나쌤영어 어법 종합편 캐러셀 렌더러
// 사용: node render.js <spec.json> <outDir> [--sheet-only]
// 출력: outDir/slide_NN.png (1080x1350), outDir/sheet.png, outDir/slides.html
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const W = 1080, H = 1350;

// ---------- color ----------
const hex2rgb = h => { h = h.replace('#', ''); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); };
const rgb2hex = c => '#' + c.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('').toUpperCase();
const mix = (a, b, t) => { const x = hex2rgb(a), y = hex2rgb(b); return rgb2hex(x.map((v, i) => v + (y[i] - v) * t)); };
const lum = h => { const c = hex2rgb(h).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const sat = h => { const c = hex2rgb(h).map(v => v / 255); const mx = Math.max(...c), mn = Math.min(...c); const l = (mx + mn) / 2; return mx === mn ? 0 : (mx - mn) / (1 - Math.abs(2 * l - 1)); };
const rgba = (h, a) => { const c = hex2rgb(h); return `rgba(${c[0]},${c[1]},${c[2]},${a})`; };

function resolvePalette(p) {
  if (!p) p = ['#2B2B2B', '#D9D9D9', '#FFD84D', '#FAFAF7'];
  if (!Array.isArray(p)) {
    const o = { ...p };
    o.SUB = o.SUB || mix(o.DK, o.BG, 0.38);
    o.ACC = o.ACC || o.LP;
    o.W = o.W || '#FFFFFF';
    return o;
  }
  const four = p.slice(0, 4).map(s => s.toUpperCase());
  const byLum = [...four].sort((a, b) => lum(a) - lum(b));
  let DK = byLum[0];
  const BG = byLum[byLum.length - 1];
  if (lum(DK) > 0.08) DK = mix(DK, '#000000', 0.55);
  const rest = four.filter(c => c !== byLum[0] && c !== BG);
  const chroma = h => { const c = hex2rgb(h); return Math.max(...c) - Math.min(...c); };
  rest.sort((a, b) => chroma(b) - chroma(a));
  const PK = rest[0] || mix(DK, BG, 0.5);
  const LP = rest[1] || mix(PK, BG, 0.55);
  return { DK, BG, PK, LP, SUB: mix(DK, BG, 0.38), ACC: p[4] ? p[4].toUpperCase() : LP, W: '#FFFFFF' };
}

// ---------- inline markup ----------
function inline(s, C, dark = false) {
  if (s == null) return '';
  s = String(s).replace(/'/g, '&#39;');
  const on = dark ? C.DK : C.DK;
  return s
    .replace(/==(.+?)==/g, `<span class="hl" style="background:${C.PK};color:${on}">$1</span>`)
    .replace(/\+\+(.+?)\+\+/g, `<span class="hl" style="background:${C.LP};color:${C.DK}">$1</span>`)
    .replace(/@@(.+?)@@/g, `<span class="hl" style="background:${C.ACC};color:${C.DK}">$1</span>`)
    .replace(/\[\[(.+?)\]\]/g, `<span class="chunk" style="border-color:${dark ? C.BG : C.DK}">$1</span>`)
    .replace(/~~(.+?)~~/g, `<span class="strike">$1</span>`)
    .replace(/__(.+?)__/g, `<span class="ul" style="border-color:${dark ? C.PK : C.DK}">$1</span>`)
    .replace(/\{\{(.+?)\}\}/g, `<span class="tag" style="background:${dark ? C.BG : C.DK};color:${dark ? C.DK : C.BG}">$1</span>`);
}

// ---------- blocks ----------
function boxStyle(C, style, { shadow = true, bg = C.W } = {}) {
  if (style === 'flat') return `background:${bg};border:none;border-radius:26px;`;
  if (style === 'soft') return `background:${bg};border:2px solid ${rgba(C.DK, .18)};border-radius:28px;${shadow ? `box-shadow:0 14px 30px ${rgba(C.DK, .12)};` : ''}`;
  return `background:${bg};border:4px solid ${C.DK};border-radius:22px;${shadow ? `box-shadow:10px 10px 0 ${C.PK};` : ''}`;
}

function block(b, C, S, dark) {
  const I = t => inline(t, C, dark);
  const fg = dark ? C.BG : C.DK;
  switch (b.type) {
    case 'rows': {
      const size = b.size || 34, ks = b.ksize || 26;
      const r = b.items.map((it, i) => `<div style="display:flex;justify-content:space-between;align-items:baseline;gap:18px;padding:15px 0;${i < b.items.length - 1 ? `border-bottom:3px dashed ${C.LP};` : ''}">
        <b style="font-size:${size}px;line-height:1.35">${I(it[0])}</b><span style="font-size:${ks}px;font-weight:700;color:${C.SUB};white-space:nowrap">${I(it[1])}</span></div>`).join('');
      return `<div style="${boxStyle(C, S)}padding:8px 30px;color:${C.DK}">${r}</div>`;
    }
    case 'point':
      return `<div style="${boxStyle(C, S, { shadow: false, bg: dark ? 'transparent' : C.W })}${dark ? `border-color:${C.BG};` : ''}padding:24px 32px;font-size:${b.size || 34}px;font-weight:900;line-height:1.45;color:${dark ? C.BG : C.DK}">${I(b.text)}</div>`;
    case 'dark':
      return `<div style="background:${dark ? C.BG : C.DK};color:${dark ? C.DK : C.BG};border-radius:28px;padding:32px 42px;font-size:${b.size || 28}px;line-height:1.6;font-weight:700">
        ${b.title ? `<div style="display:inline-block;background:${C.PK};color:${C.DK};font-weight:900;font-size:24px;padding:6px 16px;border-radius:999px;margin-bottom:12px">${I(b.title)}</div><br>` : ''}${inline(b.text, C, !dark)}</div>`;
    case 'text':
      return `<div style="font-size:${b.size || 30}px;font-weight:${b.weight || 700};line-height:1.5;color:${b.muted ? C.SUB : fg}">${I(b.text)}</div>`;
    case 'strip': {
      const rows = b.items.map((it, i) => {
        const vcol = it.ok ? C.PK : C.LP;
        return `<div style="padding:16px 0;${i < b.items.length - 1 ? `border-bottom:3px dashed ${C.LP};` : ''}">
          <div style="font-size:${b.size || 32}px;font-weight:900;line-height:1.4">${I(it.base)} <span class="chunk" style="border-color:${C.DK}">${I(it.chunk)}</span>${it.after ? ' ' + I(it.after) : ''}</div>
          <div style="display:flex;align-items:center;gap:14px;margin-top:8px;font-size:${(b.size || 32) - 6}px;font-weight:700;color:${C.SUB}">
            <span>✂ ${I(it.base)} <span class="strike">${I(it.chunk)}</span>${it.after ? ' ' + I(it.after) : ''}</span>
            <span style="margin-left:auto;background:${vcol};color:${C.DK};font-weight:900;padding:4px 14px;border-radius:999px;white-space:nowrap;font-size:24px">${I(it.verdict)}</span></div></div>`;
      }).join('');
      return `<div style="${boxStyle(C, S)}padding:8px 30px;color:${C.DK}">${rows}</div>`;
    }
    case 'vs': {
      const col = (x, tone) => `<div style="flex:1;${boxStyle(C, S, { shadow: false })}${S === 'brutal' ? `box-shadow:8px 8px 0 ${tone};` : ''}padding:22px 24px;display:flex;flex-direction:column;gap:10px;color:${C.DK}">
        <div style="align-self:flex-start;background:${tone};font-weight:900;font-size:26px;padding:6px 16px;border-radius:999px">${I(x.title)}</div>
        ${(x.lines || []).map(l => `<div style="font-size:${b.size || 29}px;font-weight:900;line-height:1.4">${I(l)}</div>`).join('')}
        ${x.note ? `<div style="margin-top:auto;font-size:24px;font-weight:700;color:${C.SUB};line-height:1.45">${I(x.note)}</div>` : ''}</div>`;
      return `<div style="display:flex;gap:26px;align-items:stretch">${col(b.a, C.PK)}<div style="align-self:center;font-family:'Black Han Sans';font-size:44px;color:${fg}">VS</div>${col(b.b, C.ACC)}</div>`;
    }
    case 'trap': {
      const it = b.items.map((t, i) => `<div style="padding:16px 0;${i < b.items.length - 1 ? `border-bottom:3px dashed ${C.LP};` : ''}">
        <div style="font-size:30px;font-weight:900;line-height:1.4"><span class="xchip">✖</span> <span style="color:#8A8A8A">${I(t.bad)}</span></div>
        <div style="font-size:30px;font-weight:900;line-height:1.4;margin-top:6px"><span class="ochip" style="background:${C.PK};color:${C.DK}">⭕</span> ${I(t.good)}</div>
        ${t.why ? `<div style="font-size:24px;font-weight:700;color:${C.SUB};margin-top:6px;line-height:1.45">→ ${I(t.why)}</div>` : ''}</div>`).join('');
      return `<div style="${boxStyle(C, S)}padding:8px 30px;color:${C.DK}">${it}</div>`;
    }
    case 'map': {
      const cols = b.cols || 2;
      const hub = `<div style="background:${C.DK};color:${C.BG};border-radius:26px;padding:22px 30px;text-align:center">
        <div style="font-family:'Black Han Sans';font-size:46px;line-height:1.2">${inline(b.hub, C, true)}</div>
        ${b.hubSub ? `<div style="font-size:25px;font-weight:700;margin-top:6px;opacity:.9">${inline(b.hubSub, C, true)}</div>` : ''}</div>`;
      const tones = [C.PK, C.LP, C.ACC, C.LP, C.PK, C.ACC];
      const cells = b.items.map((it, i) => `<div style="${it.wide ? `grid-column:span ${cols};` : ''}${boxStyle(C, S, { shadow: false })}${S === 'brutal' ? `box-shadow:7px 7px 0 ${tones[i % 6]};` : ''}padding:18px 22px;display:flex;flex-direction:column;gap:6px;color:${C.DK}">
        <div style="display:flex;align-items:center;gap:10px"><span style="background:${C.DK};color:${C.BG};font-weight:900;font-size:22px;width:38px;height:38px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center">${i + 1}</span>
        <span style="font-weight:900;font-size:30px">${I(it.label)}</span><span style="margin-left:auto;background:${tones[i % 6]};font-weight:900;font-size:24px;padding:4px 14px;border-radius:999px;white-space:nowrap">${I(it.ko)}</span></div>
        <div style="font-size:${b.size || 30}px;font-weight:700;line-height:1.4">${I(it.en)}</div></div>`).join('');
      const arrow = `<div style="text-align:center;font-size:34px;line-height:1;color:${fg};margin:-6px 0">▼</div>`;
      return `<div style="display:flex;flex-direction:column;gap:16px">${hub}${arrow}<div style="display:grid;grid-template-columns:repeat(${cols},1fr);gap:18px">${cells}</div></div>`;
    }
    case 'flow': {
      const st = b.steps.map((s, i) => `<div style="flex:1;${boxStyle(C, S, { shadow: false, bg: i === b.steps.length - 1 ? C.PK : C.W })}padding:16px 14px;text-align:center;font-weight:900;font-size:${b.size || 26}px;line-height:1.35;color:${C.DK}"><div style="font-size:20px;color:${C.SUB};margin-bottom:4px">STEP ${i + 1}</div>${I(s)}</div>`).join(`<div style="align-self:center;font-size:34px;font-weight:900;color:${fg}">→</div>`);
      return `<div style="display:flex;gap:10px;align-items:stretch">${st}</div>`;
    }
    case 'cloud': {
      const w = b.words.map((x, i) => `<span style="display:inline-block;margin:6px;padding:8px 18px;border-radius:999px;font-weight:900;font-size:${b.size || 28}px;background:${i % 3 === 0 ? C.PK : i % 3 === 1 ? C.LP : C.W};border:3px solid ${C.DK};color:${C.DK}">${I(x)}</span>`).join('');
      return `<div style="${boxStyle(C, S, { shadow: false, bg: dark ? 'transparent' : C.W })}${dark ? `border-color:${C.BG};` : ''}padding:18px 22px">${b.title ? `<div style="font-weight:900;font-size:26px;color:${dark ? C.BG : C.SUB};margin:0 6px 4px">${I(b.title)}</div>` : ''}${w}</div>`;
    }
    case 'morph': {
      const t = b.tails.map((x, i) => `<div style="display:flex;align-items:baseline;gap:14px;padding:12px 0;${i < b.tails.length - 1 ? `border-bottom:3px dashed ${C.LP};` : ''}">
        <span style="font-size:${b.size || 31}px;font-weight:900;color:${C.SUB};opacity:.75">…</span><b style="font-size:${b.size || 31}px">${I(x[0])}</b><span style="margin-left:auto;font-size:25px;font-weight:700;color:${C.SUB};white-space:nowrap">${I(x[1])}</span></div>`).join('');
      return `<div style="${boxStyle(C, S)}padding:20px 30px;color:${C.DK}"><div style="font-size:${(b.size || 31) + 2}px;font-weight:900;padding-bottom:10px;border-bottom:4px solid ${C.DK}">${I(b.stem)} …</div>${t}</div>`;
    }
    case 'next':
      return `<div style="border:4px dashed ${dark ? C.LP : C.DK};border-radius:22px;padding:20px 28px;font-size:${b.size || 27}px;font-weight:700;line-height:1.5;color:${fg}"><span style="font-weight:900;color:${dark ? C.PK : C.DK}">다음 이야기 미리 보기 ▸</span> ${I(b.text)}</div>`;
    default:
      return `<div style="color:red">unknown block ${b.type}</div>`;
  }
}

// ---------- slides ----------
function topRow(n, total, label, C, dark) {
  return `<div style="display:flex;justify-content:space-between;align-items:center;flex:none">
    <div style="background:${dark ? C.BG : C.DK};color:${dark ? C.DK : C.BG};font-weight:900;font-size:28px;padding:10px 22px;border-radius:999px">${String(n).padStart(2, '0')} / ${String(total).padStart(2, '0')}</div>
    ${label ? `<div style="background:${C.PK};color:${C.DK};font-weight:900;font-size:28px;padding:10px 22px;border-radius:999px">${inline(label, C)}</div>` : ''}</div>`;
}
function nav(spec, idx, C, dark) {
  if (!idx || !spec.map) return '';
  const fg = dark ? C.BG : C.DK;
  return `<div style="display:flex;gap:8px;flex:none;flex-wrap:nowrap">${spec.map.map((m, i) => {
    const on = i + 1 === idx;
    return `<span style="flex:1;text-align:center;font-size:21px;font-weight:900;padding:6px 4px;border-radius:999px;white-space:nowrap;${on ? `background:${C.PK};color:${C.DK};border:3px solid ${C.PK}` : `border:3px solid ${rgba(fg, .28)};color:${rgba(fg, .5)}`}">${i + 1} ${m}</span>`;
  }).join('')}</div>`;
}
function h2(lines, C, dark) {
  const fg = dark ? C.BG : C.DK;
  let [a, b] = lines;
  const second = b == null ? '' : (/==|\+\+|@@/.test(b) ? inline(b, C) : `<span class="hl2" style="background:${C.PK};color:${C.DK}">${inline(b, C)}</span>`);
  return `<h2 style="margin:0;font-family:'Black Han Sans';font-weight:400;font-size:80px;line-height:1.18;color:${fg};flex:none">${inline(a, C, dark)}${b != null ? '<br>' + second : ''}</h2>`;
}
function footer(spec, n, total, C, dark) {
  const col = dark ? rgba(C.BG, .7) : C.SUB;
  return `<div style="display:flex;justify-content:space-between;align-items:center;flex:none;font-size:24px;font-weight:700;color:${col}">
    <span>${spec.handle || '@jina.ssam_english'}</span><span>${n < total ? '넘겨보기 →' : '#지나쌤영어'}</span></div>`;
}

function coverSlide(s, spec, C, baseDir) {
  const photo = s.photo ? 'file://' + path.resolve(baseDir, s.photo) : null;
  const bgLayer = photo
    ? `<img src="${photo}" style="position:absolute;inset:0;width:${W}px;height:${H}px;object-fit:cover;object-position:${s.photoPos || '50% 10%'}">
       <div style="position:absolute;left:0;right:0;bottom:0;height:860px;background:linear-gradient(to bottom,${rgba(C.DK, 0)} 0%,${rgba(C.DK, .8)} 38%,${rgba(C.DK, .96)} 70%)"></div>`
    : `<div style="position:absolute;inset:0;background:
         radial-gradient(circle at 85% 12%, ${rgba(C.PK, .55)} 0 180px, transparent 181px),
         radial-gradient(circle at 8% 40%, ${rgba(C.LP, .35)} 0 120px, transparent 121px),
         repeating-linear-gradient(0deg, ${rgba(C.BG, .05)} 0 2px, transparent 2px 54px),
         repeating-linear-gradient(90deg, ${rgba(C.BG, .05)} 0 2px, transparent 2px 54px), ${C.DK}"></div>`;
  return `<div class="card" style="background:${C.DK};color:${C.BG};padding:84px;position:relative;justify-content:space-between">
    ${bgLayer}
    <div style="position:relative;display:flex;flex-direction:column;gap:20px;align-items:flex-start">
      <div style="display:flex;gap:16px;align-items:center">
        <div style="background:${C.PK};color:${C.DK};font-weight:900;font-size:32px;padding:12px 26px;border-radius:999px;border:4px solid ${C.BG}">${inline(s.badge || '어법 종합편', C)}</div>
        ${s.sub ? `<div style="font-weight:700;font-size:30px;color:${C.BG};background:${rgba(C.DK, .78)};border:2px solid ${rgba(C.BG, .4)};padding:10px 20px;border-radius:999px">${inline(s.sub, C, true)}</div>` : ''}
      </div>
      ${s.keywords ? `<div style="background:${C.DK};color:${C.BG};border:4px solid ${C.BG};border-radius:20px;padding:12px 28px;font-weight:900;font-size:${s.kwSize || 46}px;line-height:1.25">${inline(s.keywords, C, true)}</div>` : ''}
    </div>
    <div style="position:relative;display:flex;flex-direction:column;gap:32px">
      ${s.example ? `<div style="align-self:flex-start;transform:rotate(-3deg);background:${C.BG};color:${C.DK};border:5px solid ${C.DK};box-shadow:10px 10px 0 ${C.PK};border-radius:22px;padding:20px 30px;font-weight:900;font-size:${s.exSize || 48}px;line-height:1.15">${inline(s.example, C)}</div>` : ''}
      <h1 style="margin:0;font-family:'Black Han Sans';font-weight:400;font-size:${s.titleSize || 124}px;line-height:1.12;letter-spacing:-1px;color:${C.BG}">${inline(s.title[0], C, true)}<br><span class="hl2" style="background:${C.PK};color:${C.DK}">${inline(s.title[1], C)}</span></h1>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:20px">
        <div style="font-size:32px;font-weight:700;color:${C.BG};line-height:1.4">${inline(s.desc, C, true)}</div>
        <div style="font-size:30px;font-weight:900;color:${C.DK};background:${C.LP};padding:12px 22px;border-radius:999px;white-space:nowrap">넘겨보기 →</div>
      </div>
      <div style="font-size:24px;font-weight:700;color:${rgba(C.BG, .7)}">${spec.handle || '@jina.ssam_english'}</div>
    </div></div>`;
}

function contentSlide(s, spec, n, total, C) {
  const dark = s.kind === 'summary';
  const S = spec.style || 'brutal';
  let body = '';
  if (s.kind === 'quiz') {
    const q = s.questions.map((t, i) => `<div style="font-size:${s.qsize || 29}px;font-weight:900;line-height:1.45;padding:9px 0;${i < s.questions.length - 1 ? `border-bottom:3px dashed ${C.LP};` : ''}">${i + 1}. ${inline(t, C)}</div>`).join('');
    const a = s.answers.map((t, i) => `<div>${i + 1}. ${inline(t, C, true)}</div>`).join('');
    body = `<div style="${boxStyle(C, S)}padding:12px 30px;color:${C.DK}">${q}</div>
      <div style="background:${C.DK};color:${C.BG};border-radius:28px;padding:26px 40px;font-size:${s.asize || 25}px;line-height:1.6;font-weight:700"><div style="display:inline-block;background:${C.PK};color:${C.DK};font-weight:900;font-size:22px;padding:4px 14px;border-radius:999px;margin-bottom:8px">정답</div>${a}</div>`;
  } else {
    body = (s.blocks || []).map(b => block(b, C, S, dark)).join('');
  }
  return `<div class="card" style="background:${dark ? C.DK : C.BG};color:${dark ? C.BG : C.DK};padding:72px 84px 56px;gap:22px">
    ${topRow(n, total, s.label, C, dark)}
    ${nav(spec, s.nav, C, dark)}
    ${h2(s.h2 || ['', null], C, dark)}
    <div class="content" style="display:flex;flex-direction:column;gap:${s.gap || 26}px;justify-content:${s.align || spec.align || 'center'}">${body}</div>
    ${footer(spec, n, total, C, dark)}</div>`;
}

function buildHTML(spec, baseDir) {
  const C = resolvePalette(spec.palette);
  const total = spec.slides.length;
  const cards = spec.slides.map((s, i) => s.kind === 'cover' ? coverSlide(s, spec, C, baseDir) : contentSlide(s, spec, i + 1, total, C));
  return { C, html: `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box} body{margin:0;background:#888;font-family:'Noto Sans KR',sans-serif;word-break:keep-all}
.card{width:${W}px;height:${H}px;overflow:hidden;display:flex;flex-direction:column;margin:0 0 20px}
.content{flex:1;min-height:0;overflow:hidden}
.hl{padding:0 8px;border-radius:8px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.hl2{padding:0 16px;border-radius:14px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.chunk{border:3px dashed;border-radius:10px;padding:0 8px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.strike{text-decoration:line-through;text-decoration-thickness:3px;color:#8A8A8A}
.ul{border-bottom:5px solid;padding-bottom:1px}
.tag{font-size:.62em;font-weight:900;padding:3px 10px;border-radius:999px;vertical-align:.18em;margin:0 4px}
.xchip{display:inline-block;background:#3A3A3A;color:#fff;border-radius:8px;padding:0 10px;font-size:.85em}
.ochip{display:inline-block;border-radius:8px;padding:0 8px;font-size:.85em}
</style></head><body>${cards.join('\n')}</body></html>` };
}

async function main() {
  const [specPath, outDir] = process.argv.slice(2);
  if (!specPath || !outDir) { console.error('usage: node render.js <spec.json> <outDir>'); process.exit(1); }
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const baseDir = path.dirname(path.resolve(specPath));
  fs.mkdirSync(outDir, { recursive: true });
  const { C, html } = buildHTML(spec, baseDir);
  const htmlPath = path.resolve(outDir, 'slides.html');
  fs.writeFileSync(htmlPath, html);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);

  // overflow check
  const issues = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.card').forEach((card, i) => {
      const c = card.querySelector('.content');
      if (c && c.scrollHeight > c.clientHeight + 1) out.push(`slide ${String(i + 1).padStart(2, '0')}: 세로 넘침 +${c.scrollHeight - c.clientHeight}px`);
      if (card.scrollHeight > card.clientHeight + 1) out.push(`slide ${String(i + 1).padStart(2, '0')}: 카드 넘침 +${card.scrollHeight - card.clientHeight}px`);
      card.querySelectorAll('*').forEach(el => {
        if (el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflow !== 'visible') out.push(`slide ${String(i + 1).padStart(2, '0')}: 가로 넘침 "${el.textContent.slice(0, 30)}"`);
      });
      const r = card.getBoundingClientRect();
      card.querySelectorAll('b,span,div').forEach(el => {
        const e = el.getBoundingClientRect();
        if (e.width && (e.right > r.right + 1 || e.left < r.left - 1)) out.push(`slide ${String(i + 1).padStart(2, '0')}: 카드 밖으로 나감 "${el.textContent.slice(0, 30)}"`);
      });
    });
    return [...new Set(out)];
  });

  const cards = await page.$$('.card');
  const files = [];
  for (let i = 0; i < cards.length; i++) {
    const f = path.resolve(outDir, `slide_${String(i + 1).padStart(2, '0')}.png`);
    await cards[i].screenshot({ path: f });
    files.push(f);
  }

  // contact sheet
  const cols = Math.min(5, files.length), scale = 0.3;
  const tw = Math.round(W * scale), th = Math.round(H * scale);
  const sheet = `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#1d1d1d;font-family:sans-serif}
  .g{display:grid;grid-template-columns:repeat(${cols},${tw}px);gap:16px;padding:20px}.g div{color:#bbb;font-size:13px}img{width:${tw}px;height:${th}px;display:block;border-radius:6px}
  h1{color:#eee;font-size:18px;margin:20px 20px 0}</style></head><body><h1>${spec.title || ''} ${spec.angle ? '· ' + spec.angle : ''}</h1>
  <div class="g">${files.map((f, i) => `<div><img src="file://${f}">${String(i + 1).padStart(2, '0')}</div>`).join('')}</div></body></html>`;
  const sp = path.resolve(outDir, 'sheet.html');
  fs.writeFileSync(sp, sheet);
  const p2 = await browser.newPage({ viewport: { width: cols * (tw + 16) + 24, height: 400 } });
  await p2.goto('file://' + sp, { waitUntil: 'load' });
  await p2.screenshot({ path: path.resolve(outDir, 'sheet.png'), fullPage: true });
  await browser.close();

  console.log(`palette: ${JSON.stringify(C)}`);
  console.log(`rendered ${files.length} slides → ${outDir}`);
  if (issues.length) { console.log('⚠ 검사 결과:'); issues.forEach(x => console.log('  ⚠ ' + x)); }
  else console.log('✓ 넘침 없음');
}
main().catch(e => { console.error(e); process.exit(1); });
