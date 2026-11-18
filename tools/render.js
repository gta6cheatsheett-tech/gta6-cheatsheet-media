var gta6Post = async function (prefix, slides) {
  const W = 1080, H = 1350, PINK = '#ff3da6', CYAN = '#28e6ff', ORANGE = '#ffa640', SOFT = '#e1d7f0';
  const HF = '900 {s}px "Arial Black","Segoe UI Black",Impact,sans-serif';
  const BF = '700 {s}px "Segoe UI","Helvetica Neue",Arial,sans-serif';
  const f = (t, s) => t.replace('{s}', s);
  const token = localStorage.getItem('gta6_media_token');
  const repo = 'gta6cheatsheett-tech/gta6-cheatsheet-media';
  function wrap(ctx, text, maxw) {
    const out = []; let cur = '';
    for (const w of text.split(' ')) { const t = (cur + ' ' + w).trim(); if (ctx.measureText(t).width <= maxw) cur = t; else { out.push(cur); cur = w; } }
    if (cur) out.push(cur); return out;
  }
  function bg(ctx) {
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#0c0828'); g.addColorStop(0.6, '#460e5a'); g.addColorStop(1, '#961e5a');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    const cx = W / 2, cy = H - 170, r = 330;
    ctx.save(); ctx.globalAlpha = 0.35;
    for (let y = cy - r; y <= cy; y++) {
      const k = (y - (cy - r)) / r, band = (y - (cy - r)) % 46, gap = 4 + 18 * k;
      if (k > 0.35 && band < gap) continue;
      const half = Math.sqrt(Math.max(r * r - (y - cy) ** 2, 0));
      ctx.fillStyle = `rgb(255,${Math.round(166 - 105 * k)},${Math.round(64 + 102 * k)})`;
      ctx.fillRect(cx - half, y, half * 2, 1);
    }
    ctx.restore();
    ctx.strokeStyle = 'rgba(255,80,180,0.8)'; ctx.lineWidth = 2;
    for (let i = 0; i < 9; i++) { const y = H - 170 + Math.round((i / 8) ** 2 * 170); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    for (let i = -10; i <= 10; i++) { ctx.beginPath(); ctx.moveTo(W / 2 + i * 30, H - 170); ctx.lineTo(W / 2 + i * 260, H); ctx.stroke(); }
    ctx.fillStyle = 'rgba(8,4,24,0.47)'; ctx.fillRect(0, 0, W, H);
  }
  function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
  function draw(s, page, total) {
    const c = document.createElement('canvas'); c.width = W; c.height = H; const ctx = c.getContext('2d');
    bg(ctx); ctx.textBaseline = 'top';
    let y = 200;
    if (s.kicker) { ctx.font = f(BF, 40); ctx.fillStyle = ORANGE; ctx.fillText(s.kicker.toUpperCase(), 80, y); y += 70; }
    const big = s.big || 112; ctx.font = f(HF, big);
    for (const line of wrap(ctx, s.headline.toUpperCase(), W - 160)) {
      ctx.save(); ctx.shadowColor = PINK; ctx.shadowBlur = 30; ctx.fillStyle = '#fff'; ctx.fillText(line, 80, y); ctx.restore();
      ctx.fillStyle = '#fff'; ctx.fillText(line, 80, y); y += Math.round(big * 1.05);
    }
    y += 40;
    for (const it of (s.lines || [])) {
      if (Array.isArray(it)) {
        rr(ctx, 80, y, W - 160, 92, 20); ctx.fillStyle = '#140a2d'; ctx.fill(); ctx.strokeStyle = PINK; ctx.lineWidth = 2; ctx.stroke();
        ctx.textBaseline = 'middle'; ctx.font = f(BF, 44); ctx.fillStyle = SOFT; ctx.textAlign = 'left'; ctx.fillText(it[0], 110, y + 46);
        ctx.font = f(HF, 44); ctx.fillStyle = CYAN; ctx.textAlign = 'right'; ctx.fillText(it[1], W - 110, y + 46);
        ctx.textAlign = 'left'; ctx.textBaseline = 'top'; y += 112;
      } else {
        ctx.font = f(BF, 44); ctx.fillStyle = '#fff';
        for (const line of wrap(ctx, it, W - 160)) { ctx.fillText(line, 80, y); y += 62; }
        y += 18;
      }
    }
    rr(ctx, 60, 60, 360, 52, 26); ctx.strokeStyle = CYAN; ctx.lineWidth = 3; ctx.stroke();
    ctx.textBaseline = 'middle'; ctx.textAlign = 'center'; ctx.font = f(BF, 28); ctx.fillStyle = CYAN; ctx.fillText('GTA 6 CHEAT SHEET', 240, 87);
    if (total > 1) { ctx.textAlign = 'right'; ctx.fillStyle = SOFT; ctx.fillText(`${page}/${total}`, W - 60, 87); }
    ctx.textAlign = 'center'; ctx.font = f(BF, 24); ctx.fillStyle = SOFT;
    ctx.fillText('@gta6.cheatsheet  ·  fan page, not affiliated with Rockstar Games', W / 2, H - 60);
    return c.toDataURL('image/jpeg', 0.88).split(',')[1];
  }
  const urls = [];
  for (let i = 0; i < slides.length; i++) {
    const path = `${prefix}_${i + 1}.jpg`;
    const r = await fetch(`https://api.github.com/repos/${repo}/contents/${path}`, {
      method: 'PUT', headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' },
      body: JSON.stringify({ message: 'Add ' + path, content: draw(slides[i], i + 1, slides.length) })
    });
    if (r.status !== 201 && r.status !== 200) throw new Error(path + ' upload failed: ' + r.status + ' ' + (await r.text()).slice(0, 200));
    urls.push(`https://raw.githubusercontent.com/${repo}/main/${path}`);
  }
  return urls;
};