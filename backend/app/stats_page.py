"""A tiny self-contained dashboard for the outbound-call metrics.

Served at GET /stats; it polls GET /api/scrape-stats and renders the counts so you
can watch how many calls each scrape makes. No build step, no template engine.
"""

STATS_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Grocery Helper — scrape stats</title>
<style>
  :root {
    --bg:#0f1115; --card:#1a1d24; --card2:#22262f; --text:#f5f6f8;
    --muted:#9aa1ad; --accent:#3ddc84; --border:#2a2f3a;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .wrap { max-width:640px; margin:0 auto; padding:28px 18px 56px; }
  h1 { font-size:22px; margin:0 0 4px; }
  h2 { font-size:13px; text-transform:uppercase; letter-spacing:.5px;
    color:var(--muted); margin:26px 0 10px; }
  .sub { color:var(--muted); font-size:13px; margin:0 0 22px; }
  .total { background:var(--card); border:1px solid var(--border); border-radius:16px;
    padding:20px 22px; display:flex; align-items:baseline; gap:14px; }
  .total .n { font-size:44px; font-weight:800; color:var(--accent); line-height:1; }
  .total small { color:var(--muted); font-size:13px; }
  .row { background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between;
    align-items:center; }
  .row .label { font-weight:600; }
  .row .count { font-variant-numeric:tabular-nums; font-weight:700; color:var(--accent); }
  .lastrun { background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:14px 16px; }
  .lastrun .when { color:var(--muted); font-size:12px; margin-bottom:8px; }
  .lastrun .line { display:flex; justify-content:space-between; padding:3px 0; }
  .lastrun .line span:last-child { color:var(--accent); font-weight:700;
    font-variant-numeric:tabular-nums; }
  table { width:100%; border-collapse:collapse; }
  td { padding:7px 4px; border-bottom:1px solid var(--border); font-size:13px; }
  td.host { color:var(--muted); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  td.c { text-align:right; font-variant-numeric:tabular-nums; color:var(--accent); font-weight:700; }
  .hint { color:var(--muted); font-size:12px; margin-top:24px; line-height:1.6; }
  .dot { display:inline-block; width:7px; height:7px; border-radius:50%;
    background:var(--accent); margin-right:7px; vertical-align:middle; opacity:.85; }
  .pulse { animation:p .4s ease; }
  @keyframes p { from { opacity:.3; } to { opacity:1; } }
</style>
</head>
<body>
  <div class="wrap">
    <h1>Outbound calls to the scraped sites</h1>
    <p class="sub">Browsing the app makes <b>none</b> of these — they happen only when
      we scrape (cold start / set&nbsp;PLZ) or open “Stores” (Overpass, cached 24h).
      Live, refreshes every 3s.</p>

    <div class="total"><span class="n" id="total">–</span>
      <small>total calls since the server started<br /><span id="since"></span></small></div>

    <h2>By source</h2>
    <div id="by_source"></div>

    <h2>Most recent scrape run</h2>
    <div class="lastrun" id="last_run"></div>

    <h2>By host</h2>
    <table id="by_host"></table>

    <p class="hint">Reference: browsing&nbsp;=&nbsp;0 calls · one scrape run&nbsp;≈&nbsp;7
      (2&nbsp;Lidl&nbsp;Plus + 5&nbsp;meinprospekt) · opening Stores&nbsp;=&nbsp;1&nbsp;Overpass
      call, then cached. Counts reset when the server restarts.</p>
  </div>

<script>
function fmtDate(iso) {
  if (!iso) return "no scrape yet this session";
  try { return new Date(iso).toLocaleString(); } catch (e) { return iso; }
}
function rows(obj) {
  const keys = Object.keys(obj || {}).sort((a,b) => obj[b]-obj[a]);
  if (!keys.length) return '<div class="row"><span class="label" style="color:var(--muted)">none yet</span><span class="count">0</span></div>';
  return keys.map(k =>
    '<div class="row"><span class="label"><span class="dot"></span>'+k+'</span><span class="count">'+obj[k]+'</span></div>'
  ).join('');
}
let lastTotal = null;
async function load() {
  let d;
  try { d = await (await fetch('/api/scrape-stats')).json(); }
  catch (e) { document.getElementById('total').textContent = '?'; return; }
  const tot = document.getElementById('total');
  tot.textContent = d.total_calls;
  if (lastTotal !== null && d.total_calls !== lastTotal) {
    tot.classList.remove('pulse'); void tot.offsetWidth; tot.classList.add('pulse');
  }
  lastTotal = d.total_calls;
  document.getElementById('since').textContent = fmtDate(d.since);
  document.getElementById('by_source').innerHTML = rows(d.by_source);
  const lr = d.last_run || {};
  const lrLines = Object.keys(lr.by_source || {}).sort((a,b)=>lr.by_source[b]-lr.by_source[a])
    .map(k => '<div class="line"><span>'+k+'</span><span>'+lr.by_source[k]+'</span></div>').join('');
  document.getElementById('last_run').innerHTML =
    '<div class="when">'+fmtDate(lr.at)+' · '+(lr.total_calls||0)+' calls</div>'+
    (lrLines || '<div class="line"><span style="color:var(--muted)">no scrape run yet</span><span></span></div>');
  const hosts = d.by_host || {};
  document.getElementById('by_host').innerHTML =
    Object.keys(hosts).sort((a,b)=>hosts[b]-hosts[a]).map(h =>
      '<tr><td class="host">'+h+'</td><td class="c">'+hosts[h]+'</td></tr>').join('')
    || '<tr><td class="host" style="border:none">no calls yet</td></tr>';
}
load(); setInterval(load, 3000);
</script>
</body>
</html>
"""
