// kinetic.html を1コマずつ描いて PNG を標準出力に流す(render_kinetic.py から呼ぶ)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const s = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const n = parseInt(process.argv[3], 10);
  const br = await chromium.launch();
  const pg = await br.newPage({ viewport: { width: 1080, height: 1920 } });
  await pg.goto('file://' + path.join(__dirname, 'kinetic.html'));
  await pg.evaluate(x => { window.SCRIPT = x; }, s);
  await pg.evaluate(() => Promise.all([document.fonts.load('100px Dela'), document.fonts.load('50px Mplus')]));
  for (let f = 0; f < n; f++) {
    await pg.evaluate(t => seek(t), f / s.fps);
    const buf = await pg.screenshot({ type: 'png' });
    if (!process.stdout.write(buf)) await new Promise(r => process.stdout.once('drain', r));
  }
  await br.close();
})().catch(e => { console.error(e); process.exit(1); });
