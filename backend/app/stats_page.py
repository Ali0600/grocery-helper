"""A tiny self-contained dashboard for the outbound-call metrics.

Served at GET /stats; it fetches GET /api/scrape-stats on demand (a Refresh button)
and renders the counts so you can see how many calls each scrape makes. No build
step, no template engine.
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
  .sub { color:var(--muted); font-size:13px; margin:0 0 14px; }
  .total { background:var(--card); border:1px solid var(--border); border-radius:16px;
    padding:20px 22px; display:flex; align-items:baseline; gap:14px; }
  .total .n { font-size:44px; font-weight:800; color:var(--accent); line-height:1; }
  .total small { color:var(--muted); font-size:13px; }
  .row { background:var(--card); border:1px solid var(--border); border-radius:12px;
    padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between;
    align-items:center; }
  .row .label { font-weight:600; }
  .row .count { font-variant-numeric:tabular-nums; font-weight:700; color:var(--accent); }
  table { width:100%; border-collapse:collapse; }
  td { padding:7px 4px; border-bottom:1px solid var(--border); font-size:13px; }
  td.host { color:var(--muted); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  td.c { text-align:right; font-variant-numeric:tabular-nums; color:var(--accent); font-weight:700; }
  td.when { white-space:nowrap; font-variant-numeric:tabular-nums; width:1%; padding-right:14px; }
  td.src { font-weight:600; }
  .hint { color:var(--muted); font-size:12px; margin-top:24px; line-height:1.6; }
  .dot { display:inline-block; width:7px; height:7px; border-radius:50%;
    background:var(--accent); margin-right:7px; vertical-align:middle; opacity:.85; }
  .pulse { animation:p .4s ease; }
  @keyframes p { from { opacity:.3; } to { opacity:1; } }
  .bar { display:flex; align-items:center; gap:12px; margin:0 0 22px; }
  button { background:var(--card2); color:var(--text); border:1px solid var(--border);
    border-radius:10px; padding:9px 16px; font-size:14px; font-weight:600; cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button:active { transform:scale(.97); }
  button:disabled { opacity:.6; cursor:default; }
  .stamp { color:var(--muted); font-size:12px; }
</style>
</head>
<body>
  <div class="wrap">
    <h1>Outbound calls to the scraped sites</h1>
    <p class="sub">Browsing the app makes <b>none</b> of these — they happen only when
      we scrape (cold start / set&nbsp;PLZ) or open “Stores” (Overpass, cached 24h).
      Press <b>Refresh</b> to update.</p>

    <div class="bar">
      <button id="refresh" type="button" onclick="load()">↻ Refresh</button>
      <span class="stamp" id="stamp">loading…</span>
    </div>

    <div class="total"><span class="n" id="total">–</span>
      <small>total calls since the server started<br /><span id="since"></span></small></div>

    <h2>By source</h2>
    <div id="by_source"></div>

    <h2>Most recent calls</h2>
    <table id="recent"></table>

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
function ago(iso) {
  if (!iso) return "";
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return s + "s ago";
  const m = Math.floor(s / 60);
  if (m < 60) return m + "m ago";
  const h = Math.floor(m / 60);
  if (h < 24) return h + "h ago";
  return Math.floor(h / 24) + "d ago";
}
function recentRows(list) {
  if (!list || !list.length)
    return '<tr><td class="host" style="border:none">no calls yet — scrape or open “Stores”</td></tr>';
  return list.map(c =>
    '<tr><td class="when" title="'+fmtDate(c.at)+'">'+ago(c.at)+'</td>'+
    '<td class="src"><span class="dot"></span>'+c.source+'</td>'+
    '<td class="host">'+c.host+'</td></tr>'
  ).join('');
}
let lastTotal = null;
async function load() {
  const btn = document.getElementById('refresh');
  const stamp = document.getElementById('stamp');
  const label = btn.textContent;
  btn.disabled = true; btn.textContent = 'Refreshing…';
  let d;
  try { d = await (await fetch('/api/scrape-stats')).json(); }
  catch (e) {
    document.getElementById('total').textContent = '?';
    stamp.textContent = "couldn't reach the API";
    btn.disabled = false; btn.textContent = label;
    return;
  }
  const tot = document.getElementById('total');
  tot.textContent = d.total_calls;
  if (lastTotal !== null && d.total_calls !== lastTotal) {
    tot.classList.remove('pulse'); void tot.offsetWidth; tot.classList.add('pulse');
  }
  lastTotal = d.total_calls;
  document.getElementById('since').textContent = fmtDate(d.since);
  document.getElementById('by_source').innerHTML = rows(d.by_source);
  document.getElementById('recent').innerHTML = recentRows(d.recent);
  const hosts = d.by_host || {};
  document.getElementById('by_host').innerHTML =
    Object.keys(hosts).sort((a,b)=>hosts[b]-hosts[a]).map(h =>
      '<tr><td class="host">'+h+'</td><td class="c">'+hosts[h]+'</td></tr>').join('')
    || '<tr><td class="host" style="border:none">no calls yet</td></tr>';
  stamp.textContent = 'Refreshed at ' + new Date().toLocaleTimeString();
  btn.disabled = false; btn.textContent = label;
}
load();
</script>
</body>
</html>
"""
