/* lex lab — the page.
 *
 * docs/lab-brief.md, THE ONE DESIGN LAW: every number is a citation, and a
 * number the UI cannot cite does not render. That is not a convention here,
 * it is the only path to the DOM: `value()` below is the sole way a datum
 * becomes an element, and a payload with neither `cite` nor `unavailable`
 * returns nothing at all. The server is shaped to match (lab/cite.py), so
 * the two halves fail together rather than drifting apart.
 */

const $ = (sel, root = document) => root.querySelector(sel);
const api = (path) => fetch(path).then((r) => r.json());

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
};

const state = { view: 'runs', runs: [], selected: null, status: null };

/* ---------------------------------------------------------------- values */

const HASHISH = /^[0-9a-f]{12,}$/i;

/** The only way a datum reaches the page. */
function value(payload, { format, hash = false, empty = false } = {}) {
  if (!payload || typeof payload !== 'object') return null;   // uncitable: nothing renders

  if ('unavailable' in payload) {
    const node = el('span', {
      class: 'cited uncited' + (payload.attention ? ' attention' : ''),
      text: payload.label || 'unavailable',
    });
    node._cite = { unavailable: payload.unavailable };
    return node;
  }
  if (!payload.cite) return null;                              // ditto
  if (payload.v === null || payload.v === undefined) return null;

  const raw = String(payload.v);
  const shown = hash && HASHISH.test(raw) ? raw.slice(0, 8)
              : format ? format(payload.v) : raw;
  const node = el('span', {
    class: 'cited link' + (empty ? ' dim' : ''),
    text: shown,
  });
  node._cite = { ...payload.cite, full: raw };
  return node;
}

/** A value, or the honest absence of one — never a blank cell. */
function cell(payload, opts) {
  return value(payload, opts) || el('span', { class: 'dim mono', text: '—' });
}

const secs = (n) => {
  if (n < 60) return `${n}s`;
  const m = Math.floor(n / 60);
  return `${m}m${String(n % 60).padStart(2, '0')}s`;
};
const thousands = (n) => n.toLocaleString('en-US');

/* --------------------------------------------------------------- tooltip */

const tip = $('#tip');
let tipHideTimer = null;

function showTip(node) {
  const c = node._cite;
  if (!c) return;
  clearTimeout(tipHideTimer);
  tip.replaceChildren();
  if (c.unavailable) {
    tip.append(el('span', { class: 'note', text: c.unavailable }));
  } else {
    if (c.full && c.full.length > 8) tip.append(el('div', { class: 'path', text: c.full }));
    tip.append(el('div', {}, el('span', { class: 'path', text: c.path }),
                            c.field ? ' · ' : null,
                            c.field ? el('span', { class: 'field', text: c.field }) : null));
    if (c.how) tip.append(el('span', { class: 'note', text: `derived: ${c.how}` }));
    if (c.note) tip.append(el('span', { class: 'note', text: c.note }));
    if (c.path && !c.path.startsWith('(')) {
      // "Clicking goes there" lives HERE, not on the cell. A cell click
      // belongs to the row — stealing it made every dispatch unselectable,
      // and the provenance affordance is what the pointer is already in.
      tip.append(el('button', { class: 'go link', onclick: () => { hideTip(); openFile(c.path); } },
                    `open ${c.path}`));
    }
    if (c.full && c.full.length > 8) {
      tip.append(el('button', { class: 'go link', onclick: () => copy(c.full) }, 'copy full value'));
    }
  }
  const box = node.getBoundingClientRect();
  tip.style.display = 'block';
  const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = `${Math.min(box.left, window.innerWidth - w - 10)}px`;
  tip.style.top = `${box.bottom + h + 8 > window.innerHeight ? box.top - h - 6 : box.bottom + 6}px`;
}

function hideTip() { tip.style.display = 'none'; }

document.addEventListener('mouseover', (e) => {
  const node = e.target.closest('.cited');
  if (node) showTip(node);
});
document.addEventListener('mouseout', (e) => {
  if (e.target.closest('.cited')) tipHideTimer = setTimeout(hideTip, 260);
});
// The tooltip is reachable: the pointer can travel into it without it
// vanishing, which is what makes the citation clickable at all.
tip.addEventListener('mouseenter', () => clearTimeout(tipHideTimer));
tip.addEventListener('mouseleave', hideTip);

function copy(text) {
  navigator.clipboard?.writeText(text);
  const flash = el('div', { class: 'copied', text: 'copied' });
  const box = tip.getBoundingClientRect();
  flash.style.left = `${box.left}px`; flash.style.top = `${box.top - 22}px`;
  document.body.append(flash);
  setTimeout(() => flash.remove(), 800);
}

/* ------------------------------------------------------------------ rail */

const VIEWS = [
  { id: 'session', label: 'Session', pending: 'the lex loop over SSE' },
  { id: 'runs', label: 'Runs' },
  { id: 'law', label: 'Law', pending: 'the findings ledger F1–F38' },
  { id: 'graph', label: 'Graph', pending: 'the plan DAG' },
  { id: 'evals', label: 'Evals', pending: 'harness.evals as small multiples' },
  { id: 'monarch', label: 'Monarch', pending: 'vision.md, serif, confirm-to-save' },
  { id: 'lab', label: 'Lab', pending: 'provider knobs and record diffing' },
];

function renderRail() {
  $('#nav').replaceChildren(...VIEWS.map((v) =>
    el('button', {
      class: v.pending ? 'pending' : '',
      'aria-current': String(state.view === v.id),
      onclick: () => go(v.id),
    }, el('span', { text: v.label }),
       v.id === 'runs' ? el('span', { class: 'n', text: String(state.runs.length) }) : null)));
}

/* ------------------------------------------------------------ status bar */

function renderStatus() {
  const s = state.status;
  const bar = $('#statusbar');
  if (!s) { bar.replaceChildren(el('span', { class: 'cell', text: 'reading…' })); return; }

  const provider = value(s.provider), model = value(s.model);
  const f36 = value(s.f36);
  const settled = s.f36 && s.f36.v === 'landed';

  bar.replaceChildren(
    el('span', { class: 'cell' }, el('span', { class: 'k', text: 'provider' }),
       provider || el('span', { class: 'cited uncited', text: 'none' }),
       el('span', { class: 'k', text: '·' }), model || el('span', { class: 'dim', text: 'default' })),
    el('span', { class: 'cell' }, el('span', { class: 'k', text: 'commit' }), cell(s.commit, { hash: true })),
    el('span', { class: 'cell', id: 'planhash' }, el('span', { class: 'k', text: 'plan' }),
       el('span', { class: 'dim', text: 'compiling…' })),
    el('span', { class: 'cell' }, el('span', { class: 'k', text: 'F36' }),
       el('span', { class: 'badge' + (settled ? ' settled' : '') },
          f36 || el('span', { text: 'unknown' }))),
    el('span', { class: 'cell' }, el('span', { class: 'k', text: 'session tokens' }),
       el('span', { class: 'cited uncited', text: 'no session' })),
  );
  // The token meter has nothing to meter until the Session view exists; it
  // says so rather than showing a zero it cannot cite.
  const meter = bar.lastChild.lastChild;
  meter._cite = { unavailable: 'no browser session yet — the Session view is not built; the terminal session reports its own totals at exit (lex/usage.py)' };

  api('/api/plan-hash').then((h) => {
    const holder = $('#planhash');
    if (holder) holder.replaceChildren(el('span', { class: 'k', text: 'plan' }),
                                       cell(h, { hash: true }));
  });
}

/* ------------------------------------------------------------- runs view */

const COLUMNS = [
  { key: 'id', label: 'dispatch', get: (r) => cell(r.id), sort: (r) => r.id.v },
  { key: 'node', label: 'node', get: (r) => cell(r.node), sort: (r) => r.node.v || '' },
  { key: 'role', label: 'role', get: (r) => {
      const v = value(r.role);
      return v ? el('span', { class: 'chip role' }, v) : el('span', { class: 'dim mono', text: '—' });
    }, sort: (r) => r.role.v || '' },
  { key: 'gate', label: 'diff gate', get: (r) => gateChip(r.gate), sort: (r) => r.gate.v || '' },
  { key: 'wall_clock', label: 'wall clock', num: true,
    get: (r) => cell(r.wall_clock, { format: secs }), sort: (r) => r.wall_clock.v ?? -1 },
  { key: 'tokens_in', label: 'tokens in', num: true,
    get: (r) => cell(r.tokens_in, { format: thousands }), sort: (r) => r.tokens_in.v ?? -1 },
  { key: 'tokens_out', label: 'tokens out', num: true,
    get: (r) => cell(r.tokens_out, { format: thousands }), sort: (r) => r.tokens_out.v ?? -1 },
  { key: 'reads_out_of_packet', label: 'reads out', num: true,
    get: (r) => cell(r.reads_out_of_packet), sort: (r) => r.reads_out_of_packet.v ?? -1 },
  { key: 'artifacts', label: 'artifacts', num: true,
    get: (r) => cell(r.artifacts, { empty: r.artifacts.v === 0 }), sort: (r) => r.artifacts.v ?? -1 },
  { key: 'packet_hash', label: 'packet', get: (r) => cell(r.packet_hash, { hash: true }),
    sort: (r) => r.packet_hash.v || '' },
];

function gateChip(payload) {
  const inner = value(payload);
  if (!inner) return el('span', { class: 'dim mono', text: '—' });
  const kind = { clean: 'clean', violated: 'violated' }[payload.v] ||
               (payload.v === 'recorded as prose' ? 'unknown' : 'unknown');
  return el('span', { class: `chip ${kind}` }, inner);
}

let sort = { key: 'id', dir: 1 };

function renderRuns() {
  const stage = $('#stage');
  const head = el('header', { class: 'view-head' },
    el('h1', { text: 'Runs' }),
    el('span', { class: 'sub' }, `${state.runs.length} dispatch records · `,
       el('b', { text: 'docs/evidence/*/dispatch_record_*.json' })));

  if (!state.runs.length) {
    stage.replaceChildren(head, el('div', { class: 'empty' },
      'no dispatch records yet — ', el('b', { text: 'runs/' }), ' is empty and no ',
      el('b', { text: 'docs/evidence/*/dispatch_record_*.json' }), ' exists. ',
      'A record lands when ', el('b', { text: 'harness.dispatch harvest' }), ' completes.'));
    return;
  }

  const rows = [...state.runs].sort((a, b) => {
    const col = COLUMNS.find((c) => c.key === sort.key);
    const x = col.sort(a), y = col.sort(b);
    return (x > y ? 1 : x < y ? -1 : 0) * sort.dir;
  });

  const table = el('table', { class: 'ledger' },
    el('thead', {}, el('tr', {}, COLUMNS.map((c) =>
      el('th', {
        class: 'sortable' + (c.num ? ' num' : ''),
        onclick: () => { sort = { key: c.key, dir: sort.key === c.key ? -sort.dir : 1 }; renderRuns(); },
      }, c.label, sort.key === c.key ? el('span', { class: 'caret', text: sort.dir > 0 ? ' ↑' : ' ↓' }) : null)))),
    el('tbody', {}, rows.map((r) =>
      el('tr', {
        'aria-selected': String(state.selected === r.id.v),
        onclick: () => selectRun(r.id.v),
      }, COLUMNS.map((c) => el('td', { class: c.num ? 'num' : '' }, c.get(r)))))));

  stage.replaceChildren(head, table);
}

/* ------------------------------------------------------------- inspector */

function closeInspector() {
  state.selected = null;
  $('#shell').classList.remove('with-inspector');
  $('#inspector').replaceChildren();
  renderRuns();
}

function inspectorFrame(title, ...sections) {
  $('#shell').classList.add('with-inspector');
  $('#inspector').replaceChildren(
    el('div', { class: 'insp-head' }, el('h2', { text: title }),
       el('button', { class: 'close', text: '×', onclick: closeInspector })),
    // replaceChildren() stringifies null into a literal "null" node; el()
    // already drops them, this is the one place that does not go through it.
    ...sections.filter(Boolean));
  $('#inspector').classList.add('fade');
}

async function selectRun(id) {
  state.selected = id;
  renderRuns();
  const d = await api(`/api/runs/${encodeURIComponent(id)}`);
  const rec = d.record;
  const kv = (label, text, opts = {}) => [el('dt', { text: label }),
    el('dd', {}, text === undefined || text === null || text === ''
      ? el('span', { class: 'dim mono', text: '—' })
      : citedLiteral(String(text), d.path, opts.field || label, opts))];

  inspectorFrame(`dispatch ${id}`,
    el('div', { class: 'insp-section' }, el('h3', { text: 'record' }),
      el('dl', { class: 'kv' },
        kv('node', rec.node, { field: 'node' }),
        kv('role', rec.role, { field: 'role' }),
        kv('commit', rec.commit, { field: 'commit', hash: true }),
        kv('packet', rec.packet_hash, { field: 'packet_hash', hash: true }),
        kv('spec plan', rec.spec_plan_hash, { field: 'spec_plan_hash', hash: true }),
        kv('dispatch plan', rec.dispatch_plan_hash, { field: 'dispatch_plan_hash', hash: true }),
        kv('fence sha256', rec.fence_sha256, { field: 'fence_sha256', hash: true }),
        kv('started', rec.started, { field: 'started' }),
        kv('finished', rec.finished, { field: 'finished' }),
        kv('generator', rec.generator, { field: 'generator' }))),

    rec.verdict ? el('div', { class: 'insp-section' }, el('h3', { text: 'verdict, as recorded' }),
      el('div', { class: 'law', style: 'font-size:13px' }, String(rec.verdict))) : null,

    el('div', { class: 'insp-section' }, el('h3', { text: `fence — ${Object.keys(d.fence_allowed).length} writable` }),
      Object.keys(d.fence_allowed).length
        ? el('ul', { class: 'files' }, Object.entries(d.fence_allowed).map(([p, at]) =>
            el('li', { onclick: () => openFile(p) }, p, el('span', { class: 'ext', text: `  ${at}` }))))
        : el('div', { class: 'empty', style: 'padding:0' },
            'no writable paths — a tester dispatch fences every tracked file (fence.json allowed: {})')),

    el('div', { class: 'insp-section' }, el('h3', { text: `artifacts — ${d.artifacts.length}` }),
      d.artifacts.length
        ? el('ul', { class: 'files' }, d.artifacts.map((a) =>
            el('li', { onclick: () => openFile(`${d.evidence_dir}/${a}`) }, a)))
        : el('div', { class: 'empty', style: 'padding:0' },
            'no artifacts recorded in ', el('b', { text: d.path }))),

    d.reads_out_of_packet ? el('div', { class: 'insp-section' },
      el('h3', { text: `reads outside the packet — ${d.reads_out_of_packet.length}` }),
      el('ul', { class: 'files' }, d.reads_out_of_packet.map((r) =>
        el('li', { onclick: () => openFile(r.path) }, r.path,
           el('span', { class: 'ext', text: `  ${r.tool}` }))))) : null,

    el('div', { class: 'insp-section' }, el('h3', { text: 'source' }),
      el('ul', { class: 'files' }, el('li', { onclick: () => openFile(d.path) }, d.path))));
}

/** A literal from a record that the inspector shows: still cited. */
function citedLiteral(text, path, field, { hash = false } = {}) {
  return value({ v: text, cite: { path, field } }, { hash });
}

async function openFile(path) {
  const payload = await api(`/api/file?path=${encodeURIComponent(path)}`);
  if (payload.detail) {
    inspectorFrame(path, el('div', { class: 'insp-section' },
      el('div', { class: 'empty', style: 'padding:0', text: payload.detail })));
    return;
  }
  const isLaw = /\.md$/.test(payload.path) && /reports|docs/.test(payload.path);
  inspectorFrame(payload.path,
    el('div', { class: 'insp-section' },
      el('pre', { class: 'source' + (isLaw ? ' law' : ''), text: payload.text }),
      payload.truncated ? el('div', { class: 'dim mono', text: '… truncated' }) : null),
    state.selected ? el('div', { class: 'insp-section' },
      el('ul', { class: 'files' },
        el('li', { onclick: () => selectRun(state.selected) },
           `← back to dispatch ${state.selected}`))) : null);
}

/* --------------------------------------------------------------- routing */

function go(view) {
  state.view = view;
  renderRail();
  if (view === 'runs') return renderRuns();
  const meta = VIEWS.find((v) => v.id === view);
  $('#stage').replaceChildren(
    el('header', { class: 'view-head' }, el('h1', { text: meta.label }),
       el('span', { class: 'sub', text: 'not built yet' })),
    el('div', { class: 'empty' },
      `${meta.label} is sequenced after the screenshot checkpoint — `,
      el('b', { text: meta.pending }), '. ',
      'Nothing is stubbed here: the view renders when it has real data to cite ',
      '(docs/lab-brief.md, SEQUENCE).'));
}

async function boot() {
  renderRail();
  renderStatus();
  const [status, runs] = await Promise.all([api('/api/status'), api('/api/runs')]);
  state.status = status;
  state.runs = runs.rows;
  renderRail();
  renderStatus();
  go('runs');
}

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeInspector(); });
boot();
