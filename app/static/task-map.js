(() => {
  'use strict';
  const root = document.querySelector('[data-task-map]');
  if (!root) return;
  const $ = selector => root.querySelector(selector);
  const pid = Number(root.dataset.projectId), title = root.dataset.projectName;
  const workspace = $('[data-map-window]'), viewport = $('[data-map-viewport]');
  const world = $('[data-map-world]'), nodeLayer = $('[data-map-nodes]'), lines = $('[data-map-lines]');
  const status = $('[data-map-status]'), overview = $('[data-map-overview-svg]');
  const W = 320, H = 168, COLUMN = 500, ROW_GAP = 72;
  const labels = {todo: 'To do', doing: 'In progress', blocked: 'Blocked', done: 'Done'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
  let data = JSON.parse($('[data-map-initial]').textContent);
  let nodes = new Map(), children = new Map(), points = new Map(), elements = new Map(), incident = new Map(), edges = [];
  let selected = null, focusRoot = null, hub = {x: 0, y: 0}, pan = {x: 40, y: 40, z: 1};
  let built = false, needsRender = true, pointer = null, gesture = null, frame = 0, suppressClick = false;
  let layoutTimer = 0, layoutSaving = false, layoutConflict = false, pendingReset = false, mutation = false, undoArrange = null;
  const dirty = new Map(), activePointers = new Map(), collapsed = new Set();
  let bounds = {x: 0, y: 0, width: W, height: H}, visible = new Set(), search = '';
  const SVG = 'http://www.w3.org/2000/svg';
  const preferenceKey = 'mlo.map-view.' + (document.body.dataset.userId || 'guest') + '.' + pid;
  let orientation = 'horizontal', taskFilter = 'all', matched = new Set();
  try {
    const saved = JSON.parse(localStorage.getItem(preferenceKey) || '{}');
    if (['horizontal', 'vertical'].includes(saved.orientation)) orientation = saved.orientation;
    if (['all', 'open', 'done', 'todo', 'doing', 'blocked'].includes(saved.filter)) taskFilter = saved.filter;
  } catch {}
  function rememberView() {
    try { localStorage.setItem(preferenceKey, JSON.stringify({orientation, filter: taskFilter})); } catch {}
  }
  // Server coordinates remain in the original horizontal space. Rotating the
  // view never rewrites saved positions or introduces a new database migration.
  const BREADTH_SCALE = (W + ROW_GAP) / (H + ROW_GAP), DEPTH_SCALE = (H + 150) / COLUMN;
  function toView(p) { return orientation === 'vertical' ? {x: p.y * BREADTH_SCALE, y: p.x * DEPTH_SCALE} : {...p}; }
  function fromView(p) { return orientation === 'vertical' ? {x: p.y / DEPTH_SCALE, y: p.x / BREADTH_SCALE} : {...p}; }
  function matchesStatus(n) { return taskFilter === 'all' || (taskFilter === 'open' ? n.status !== 'done' : n.status === taskFilter); }
  $('[data-map-orientation]').value = orientation;
  $('[data-map-filter]').value = taskFilter;

  function say(text, error = false) {
    status.textContent = text;
    status.classList.toggle('is-error', error);
  }
  function index() {
    nodes = new Map(data.nodes.map(n => [n.id, n]));
    children = new Map();
    for (const n of data.nodes) {
      if (!children.has(n.parent_id)) children.set(n.parent_id, []);
      children.get(n.parent_id).push(n);
    }
    for (const group of children.values()) group.sort((a, b) => a.position - b.position || a.id - b.id);
  }
  function roots() { return data.nodes.filter(n => !nodes.has(n.parent_id)); }
  async function request(path, {method = 'GET', body} = {}) {
    const response = await fetch('/api/v4/projects/' + pid + path, {
      method, credentials: 'same-origin',
      headers: {Accept: 'application/json', ...(body ? {'Content-Type': 'application/json'} : {})},
      ...(body ? {body: JSON.stringify(body)} : {})
    });
    if (!(response.headers.get('content-type') || '').includes('application/json')) throw Error('Sign in again, then retry.');
    const result = await response.json();
    if (!response.ok) {
      const error = Error(typeof result.detail === 'string' ? result.detail : 'Unable to save this change.');
      error.status = response.status;
      throw error;
    }
    return result;
  }
  function preview() {
    const total = data.total ?? data.nodes.length, done = data.nodes.filter(n => n.status === 'done').length;
    $('[data-map-preview-count]').textContent = total.toLocaleString() + ' tasks' + (data.limit ? '' : ' · ' + done.toLocaleString() + ' completed');
    const sample = roots().slice(0, 3);
    const shorten = (text, max) => text.length > max ? text.slice(0, max - 1) + '…' : text;
    let html = '<rect class="map-preview-hub" x="18" y="114" width="204" height="72" rx="14"/><text class="map-preview-text" x="36" y="155">' + esc(shorten(title, 23)) + '</text>';
    sample.forEach((n, i) => {
      const y = sample.length === 1 ? 114 : sample.length === 2 ? 54 + i * 140 : 14 + i * 100;
      html += '<path class="map-preview-line" d="M222 150H260V' + (y + 36) + 'H310"/><rect class="map-preview-node" x="310" y="' + y + '" width="308" height="72" rx="12"/><circle class="map-preview-dot" cx="329" cy="' + (y + 22) + '" r="4"/><text class="map-preview-text" x="342" y="' + (y + 27) + '">' + esc(shorten(n.title, 32)) + '</text><text class="map-preview-text" x="328" y="' + (y + 53) + '" style="font-size:11px;font-weight:400">' + esc(labels[n.status]) + ' · ' + (children.get(n.id)?.length || 0) + ' subtasks</text>';
    });
    if (!sample.length) html += '<text class="map-preview-text" x="300" y="155">' + (data.limit ? 'Open List or Board' : 'Add your first task') + '</text>';
    $('[data-map-preview]').innerHTML = html;
    document.querySelectorAll('[data-project-task-total]').forEach(el => el.textContent = total);
    if (!data.limit) document.querySelectorAll('[data-project-task-done]').forEach(el => el.textContent = done);
  }
  function defaults() {
    const positions = new Map(), heights = new Map(), seen = new Set();
    function measure(n, trail = new Set()) {
      if (trail.has(n.id)) return H;
      if (heights.has(n.id)) return heights.get(n.id);
      const next = new Set(trail); next.add(n.id);
      const group = (children.get(n.id) || []).filter(c => visible.has(c.id));
      const height = Math.max(H, group.reduce((sum, c) => sum + measure(c, next), 0) + Math.max(0, group.length - 1) * ROW_GAP);
      heights.set(n.id, height);
      return height;
    }
    function place(n, depth, top) {
      if (seen.has(n.id)) return;
      seen.add(n.id);
      positions.set(n.id, {x: COLUMN * depth + COLUMN, y: top + (measure(n) - H) / 2});
      let y = top;
      for (const child of (children.get(n.id) || []).filter(c => visible.has(c.id))) {
        place(child, depth + 1, y);
        y += measure(child) + ROW_GAP;
      }
    }
    let y = 40;
    for (const n of roots().filter(n => visible.has(n.id))) { place(n, 0, y); y += measure(n) + ROW_GAP * 1.7; }
    for (const n of data.nodes) if (visible.has(n.id) && !seen.has(n.id)) { place(n, 0, y); y += measure(n) + ROW_GAP; }
    // Hidden cards still need in-memory coordinates, but cannot reserve space in
    // the visible tree. Their automatic parking positions are never persisted.
    for (const n of data.nodes) if (!seen.has(n.id)) {
      positions.set(n.id, {x: COLUMN, y}); y += H + ROW_GAP;
    }
    return new Map([...positions].map(([id, p]) => [id, toView(p)]));
  }
  function freePoint(point, id, occupied = points) {
    const p = {x: clamp(point.x, -1000000, 1000000), y: clamp(point.y, -1000000, 1000000)};
    const hits = candidate => [...occupied].some(([other, q]) => other !== id && Math.abs(q.x - candidate.x) < W + 44 && Math.abs(q.y - candidate.y) < H + 44);
    if (!hits(p)) return p;
    for (let ring = 1; ring <= data.nodes.length + 1; ring++) {
      for (const direction of [1, -1]) {
        const candidate = orientation === 'vertical'
          ? {x: clamp(p.x + direction * ring * (W + ROW_GAP), -1000000, 1000000), y: p.y}
          : {x: p.x, y: clamp(p.y + direction * ring * (H + ROW_GAP), -1000000, 1000000)};
        if (!hits(candidate)) return candidate;
      }
    }
    return p;
  }
  function branchIds() {
    if (!focusRoot || !nodes.has(focusRoot)) {
      const ids = new Set(), pending = roots().map(n => n.id);
      while (pending.length) {
        const id = pending.pop(); if (ids.has(id)) continue; ids.add(id);
        if (!collapsed.has(id)) pending.push(...(children.get(id) || []).map(n => n.id));
      }
      return ids;
    }
    const ids = new Set(), pending = [focusRoot];
    while (pending.length) {
      const id = pending.pop();
      if (ids.has(id)) continue;
      ids.add(id);
      if (!collapsed.has(id)) pending.push(...(children.get(id) || []).map(n => n.id));
    }
    let parent = nodes.get(focusRoot)?.parent_id;
    while (nodes.has(parent) && !ids.has(parent)) { ids.add(parent); parent = nodes.get(parent).parent_id; }
    for (const edge of data.edges) if (edge.kind === 'prerequisite' && (edge.from === focusRoot || edge.to === focusRoot)) {
      ids.add(edge.from); ids.add(edge.to);
    }
    return ids;
  }
  function activeIds() {
    const branch = branchIds();
    // A filtered descendant must remain discoverable under a folded ancestor.
    // Only matching cards and their explicitly marked ancestor context survive.
    if (taskFilter === 'all') { matched = new Set(branch); return branch; }
    const candidates = focusRoot ? new Set() : new Set(nodes.keys());
    if (focusRoot) {
      const pending = [focusRoot];
      while (pending.length) {
        const id = pending.pop(); if (candidates.has(id)) continue;
        candidates.add(id); pending.push(...(children.get(id) || []).map(n => n.id));
      }
    }
    matched = new Set([...candidates].filter(id => matchesStatus(nodes.get(id))));
    const ids = new Set(matched);
    for (const id of matched) {
      let parent = nodes.get(id)?.parent_id;
      const visited = new Set();
      while (nodes.has(parent) && !visited.has(parent)) {
        visited.add(parent); ids.add(parent); parent = nodes.get(parent).parent_id;
      }
    }
    return ids;
  }
  function sceneBounds() {
    const list = [...visible].map(id => points.get(id)).filter(Boolean);
    if (!focusRoot && list.length) list.push(hub);
    if (!list.length) return {x: 0, y: 0, width: W, height: H};
    const x = Math.min(...list.map(p => p.x)) - 48, y = Math.min(...list.map(p => p.y)) - 48;
    return {x, y, width: Math.max(...list.map(p => p.x)) + W + 48 - x, height: Math.max(...list.map(p => p.y)) + H + 48 - y};
  }
  function updateOverview() {
    const rect = overview.querySelector('[data-overview-view]');
    if (!rect || !workspace.open) return;
    rect.setAttribute('x', -pan.x / pan.z);
    rect.setAttribute('y', -pan.y / pan.z);
    rect.setAttribute('width', viewport.clientWidth / pan.z);
    rect.setAttribute('height', viewport.clientHeight / pan.z);
  }
  function setTransform() {
    world.style.transform = 'translate(' + pan.x + 'px,' + pan.y + 'px) scale(' + pan.z + ')';
    $('[data-map-scale]').textContent = Math.round(pan.z * 100) + '%';
    updateOverview();
    if (workspace.open && viewport.clientWidth) oldSize = {w: viewport.clientWidth, h: viewport.clientHeight};
  }
  function centerOn(id, actual = false) {
    const p = points.get(id);
    if (!p || !workspace.open) return;
    if (actual) pan.z = clamp((viewport.clientWidth - 64) / (W + 40), .65, 1);
    pan.x = viewport.clientWidth / 2 - (p.x + W / 2) * pan.z;
    pan.y = viewport.clientHeight / 2 - (p.y + H / 2) * pan.z;
    setTransform();
  }
  function fit() {
    if (!points.size || !workspace.open) return;
    bounds = sceneBounds();
    pan.z = clamp(Math.min((viewport.clientWidth - 48) / bounds.width, (viewport.clientHeight - 60) / bounds.height, 1), .12, 2);
    pan.x = (viewport.clientWidth - bounds.width * pan.z) / 2 - bounds.x * pan.z;
    pan.y = (viewport.clientHeight - bounds.height * pan.z) / 2 - bounds.y * pan.z;
    setTransform();
  }
  function home() {
    if (!data.nodes.length) return;
    const b = sceneBounds(), z = Math.min((viewport.clientWidth - 48) / b.width, (viewport.clientHeight - 60) / b.height, 1);
    if (z >= .8) fit();
    else {
      const firstId = visible.has(selected) ? selected : roots().find(n => visible.has(n.id))?.id ?? [...visible][0];
      const first = points.get(firstId);
      if (!first) { fit(); return; }
      pan.z = clamp((viewport.clientWidth - 64) / (W + 56), .65, 1);
      const branchTop = visible.size > 12 ? first.y : Math.min(first.y, ...(children.get(firstId) || []).filter(n => visible.has(n.id)).map(n => points.get(n.id).y));
      pan.x = 36 - first.x * pan.z; pan.y = 36 - branchTop * pan.z;
      setTransform();
    }
  }
  function zoom(factor, x = viewport.clientWidth / 2, y = viewport.clientHeight / 2) {
    const z = clamp(pan.z * factor, .12, 2);
    pan.x = x - (x - pan.x) * z / pan.z;
    pan.y = y - (y - pan.y) * z / pan.z;
    pan.z = z; setTransform();
  }
  // Rounded orthogonal lanes separate sibling wires, with ports spread down each card.
  function roundedPath(list) {
    const p = list.filter((point, i) => !i || point.x !== list[i - 1].x || point.y !== list[i - 1].y);
    if (!p.length) return '';
    let d = 'M' + p[0].x + ' ' + p[0].y;
    for (let i = 1; i < p.length - 1; i++) {
      const a = p[i - 1], b = p[i], c = p[i + 1], ab = Math.hypot(b.x - a.x, b.y - a.y), bc = Math.hypot(c.x - b.x, c.y - b.y);
      const r = Math.min(16, ab / 2, bc / 2);
      const before = {x: b.x + (a.x - b.x) * r / ab, y: b.y + (a.y - b.y) * r / ab};
      const after = {x: b.x + (c.x - b.x) * r / bc, y: b.y + (c.y - b.y) * r / bc};
      d += 'L' + before.x + ' ' + before.y + 'Q' + b.x + ' ' + b.y + ' ' + after.x + ' ' + after.y;
    }
    const last = p.at(-1);
    return d + 'L' + last.x + ' ' + last.y;
  }
  function edgePath(edge) {
    const a = edge.from === 0 ? hub : points.get(edge.from), b = points.get(edge.to);
    if (!a || !b) return '';
    if (orientation === 'vertical') {
      const start = {x: a.x + 30 + edge.sourcePort * (W - 60), y: a.y + H};
      const targetX = b.x + 30 + edge.targetPort * (W - 60);
      if (b.y >= a.y + H + 50) {
        const end = {x: targetX, y: b.y};
        const lane = start.y + Math.max(26, (end.y - start.y) * (.35 + .3 * edge.sourcePort));
        return roundedPath([start, {x: start.x, y: lane}, {x: targetX, y: lane}, end]);
      }
      const end = {x: targetX, y: b.y + H}, lane = Math.max(start.y, end.y) + 64 + edge.lane * 18;
      return roundedPath([start, {x: start.x, y: lane}, {x: targetX, y: lane}, end]);
    }
    const forward = b.x >= a.x + W + 50;
    const sourceY = a.y + 30 + edge.sourcePort * (H - 60), targetY = b.y + 30 + edge.targetPort * (H - 60);
    const start = {x: a.x + W, y: sourceY};
    if (forward) {
      const end = {x: b.x, y: targetY};
      const lane = start.x + Math.max(26, (end.x - start.x) * (.35 + .3 * edge.sourcePort));
      return roundedPath([start, {x: lane, y: sourceY}, {x: lane, y: targetY}, end]);
    }
    // Backward/same-column prerequisites use a separate return lane beside the cards.
    const end = {x: b.x + W, y: targetY}, lane = Math.max(start.x, end.x) + 64 + edge.lane * 18;
    return roundedPath([start, {x: lane, y: sourceY}, {x: lane, y: targetY}, end]);
  }
  function moveNode(id, point) {
    points.set(id, point);
    const el = elements.get(id);
    if (el) el.style.transform = 'translate(' + point.x + 'px,' + point.y + 'px)';
    for (const edge of incident.get(id) || []) edge.path.setAttribute('d', edgePath(edge));
    const mini = overview.querySelector('[data-overview-node="' + id + '"]');
    if (mini) { mini.setAttribute('x', point.x); mini.setAttribute('y', point.y); }
  }
  function edgeVisibility() {
    const mode = $('[data-map-connections]').value;
    for (const edge of edges) {
      const related = edge.from === selected || edge.to === selected;
      edge.path.hidden = !(visible.has(edge.to) && (edge.from === 0 ? !focusRoot : visible.has(edge.from))) ||
        (mode === 'prerequisite' && edge.kind !== 'prerequisite') ||
        (mode === 'structure' && edge.kind === 'prerequisite' && !related);
      // SVG does not implement HTMLElement.hidden consistently.
      edge.path.style.display = edge.path.hidden ? 'none' : '';
      edge.path.classList.toggle('is-related', related);
      edge.path.classList.toggle('is-background', !!selected && !related);
    }
  }
  function drawOverview() {
    bounds = sceneBounds();
    overview.setAttribute('viewBox', [bounds.x, bounds.y, bounds.width, bounds.height].join(' '));
    overview.innerHTML = [...visible].map(id => {
      const p = points.get(id);
      return '<rect data-overview-node="' + id + '" class="' + (id === selected ? 'map-overview-selected' : 'map-overview-node') + '" x="' + p.x + '" y="' + p.y + '" width="' + W + '" height="' + H + '" rx="18"/>';
    }).join('') + '<rect class="map-overview-viewport" data-overview-view rx="12"/>';
    $('[data-map-overview]').hidden = !data.nodes.length;
    updateOverview();
  }
  function applyVisibility() {
    visible = activeIds();
    const matches = data.nodes.filter(n => visible.has(n.id) && n.title.toLocaleLowerCase().includes(search));
    for (const [id, el] of elements) {
      el.hidden = !visible.has(id);
      el.classList.toggle('is-muted', !!search && !nodes.get(id).title.toLocaleLowerCase().includes(search));
      const context = taskFilter !== 'all' && visible.has(id) && !matched.has(id);
      el.classList.toggle('is-filter-context', context);
      el.querySelector('[data-map-context]').hidden = !context;
      const toggle = el.querySelector('[data-map-toggle]');
      if (toggle) {
        toggle.disabled = taskFilter !== 'all';
        toggle.title = taskFilter === 'all' ? 'Expand or fold subtasks' : 'Filtered views expand matching branches. Choose All tasks to fold them.';
      }
    }
    const noResults = $('[data-map-no-results]');
    noResults.hidden = !!matches.length || !data.nodes.length;
    noResults.textContent = taskFilter !== 'all' ? 'No matching tasks. Try All tasks or clear your search.' : 'No matching tasks. Try another name.';
    $('[data-map-shown]').textContent = data.limit ? data.total.toLocaleString() + ' tasks — use List or Board' :
      taskFilter === 'all' ? visible.size.toLocaleString() + ' of ' + data.nodes.length.toLocaleString() + ' tasks shown' :
      matched.size.toLocaleString() + ' matching · ' + (visible.size - matched.size).toLocaleString() + ' ancestors for context';
    const expandAll = $('[data-map-expand-all]');
    if (expandAll) { expandAll.hidden = taskFilter !== 'all' || visible.size === data.nodes.length || !!data.limit; expandAll.textContent = 'Show all ' + data.nodes.length.toLocaleString() + ' tasks'; }
    $('[data-map-focus-strip]').hidden = !focusRoot;
    if (focusRoot && nodes.has(focusRoot)) $('[data-map-focus-title]').textContent = nodes.get(focusRoot).title;
    world.querySelector('.task-map-hub').hidden = !!focusRoot || !visible.size;
    if (selected && !visible.has(selected)) select(null);
    edgeVisibility(); drawOverview();
  }
  function select(id, focus = false) {
    selected = id === null ? null : Number(id);
    const n = nodes.get(selected);
    if (!n) selected = null;
    $('[data-map-selection]').hidden = !n;
    $('[data-map-selection-empty]').hidden = !!n;
    for (const [tid, el] of elements) {
      el.classList.toggle('is-selected', tid === selected);
      el.setAttribute('aria-current', String(tid === selected));
    }
    if (n) {
      $('[data-map-selected-title]').textContent = n.title;
      $('[data-map-selected-status]').textContent = labels[n.status];
      const prerequisites = data.edges.filter(e => e.kind === 'prerequisite' && e.to === n.id);
      const facts = [['Due', n.due_on || 'No due date'], ['Subtask of', nodes.get(n.parent_id)?.title || 'Project'], ['Subtasks', String(children.get(n.id)?.length || 0)], ['Must finish first', prerequisites.length ? prerequisites.map(e => nodes.get(e.from)?.title || '').join(', ') : 'None']];
      $('[data-map-selected-facts]').innerHTML = facts.map(([key, value]) => '<div><dt>' + esc(key) + '</dt><dd>' + esc(value) + '</dd></div>').join('');
      const siblings = (children.get(n.parent_id) || []).filter(t => t.status === n.status), i = siblings.findIndex(t => t.id === n.id);
      if ($('[data-map-earlier]')) { $('[data-map-earlier]').disabled = i <= 0; $('[data-map-later]').disabled = i === siblings.length - 1; }
      if (focus) elements.get(selected)?.focus({preventScroll: true});
    }
    edgeVisibility();
    overview.querySelectorAll('[data-overview-node]').forEach(el => el.setAttribute('class', Number(el.dataset.overviewNode) === selected ? 'map-overview-selected' : 'map-overview-node'));
  }
  function buildEdges() {
    lines.querySelectorAll('[data-map-edge]').forEach(el => el.remove());
    incident = new Map(); edges = [];
    const sourceGroups = new Map(), targetGroups = new Map();
    for (const edge of [...data.edges, ...roots().map(n => ({from: 0, to: n.id, kind: 'project'}))]) {
      if (edge.from !== 0 && !points.has(edge.from) || !points.has(edge.to)) continue;
      const item = {...edge, sourcePort: .5, targetPort: .5, lane: 0};
      edges.push(item);
      if (!sourceGroups.has(item.from)) sourceGroups.set(item.from, []);
      if (!targetGroups.has(item.to)) targetGroups.set(item.to, []);
      sourceGroups.get(item.from).push(item); targetGroups.get(item.to).push(item);
    }
    for (const group of sourceGroups.values()) {
      const axis = orientation === 'vertical' ? 'x' : 'y';
      group.sort((a, b) => points.get(a.to)[axis] - points.get(b.to)[axis] || a.to - b.to);
      group.forEach((e, i) => { e.sourcePort = (i + 1) / (group.length + 1); e.lane = i % 8; });
    }
    for (const group of targetGroups.values()) group.forEach((e, i) => e.targetPort = (i + 1) / (group.length + 1));
    for (const edge of edges) {
      const path = document.createElementNS(SVG, 'path');
      path.dataset.mapEdge = edge.kind; path.dataset.mapFrom = edge.from; path.dataset.mapTo = edge.to;
      path.setAttribute('d', edgePath(edge));
      if (edge.kind === 'prerequisite') path.setAttribute('marker-end', 'url(#task-map-arrow)');
      lines.append(path); edge.path = path;
      for (const id of [edge.from, edge.to]) {
        if (!incident.has(id)) incident.set(id, []);
        incident.get(id).push(edge);
      }
    }
  }
  function render(initial = false) {
    index(); preview(); needsRender = true;
    if (!built && !workspace.open) return;
    visible = activeIds();
    const defaultsMap = defaults(), placed = new Map();
    const placementOrder = [...data.nodes].sort((a, b) => Number(visible.has(b.id)) - Number(visible.has(a.id)));
    for (const n of placementOrder) {
      const point = [points.get(n.id), data.positions[n.id] ? toView(data.positions[n.id]) : null, defaultsMap.get(n.id)].find(p => Number.isFinite(p?.x) && Number.isFinite(p?.y));
      placed.set(n.id, freePoint(point, n.id, placed));
    }
    points = placed;
    nodeLayer.innerHTML = data.nodes.map(n => {
      const p = points.get(n.id), count = children.get(n.id)?.length || 0;
      return '<article class="task-map-node ' + (n.status === 'done' ? 'is-complete' : '') + '" data-map-node="' + n.id + '" tabindex="0" aria-label="' + esc(n.title + ', ' + labels[n.status] + '. Arrow keys move this card; Enter opens it.') + '" style="transform:translate(' + p.x + 'px,' + p.y + 'px)"><div class="task-map-node-head">' +
        (data.can_edit ? '<button type="button" class="mlo-check ' + (n.status === 'done' ? 'is-done' : '') + '" data-map-complete="' + n.id + '" aria-pressed="' + (n.status === 'done') + '" aria-label="' + esc((n.status === 'done' ? 'Reopen ' : 'Complete ') + n.title) + '"></button>' : '') +
        '<span class="task-map-node-status"><i class="v37-status-dot ' + n.status + '" aria-hidden="true"></i>' + labels[n.status] + '</span><span class="map-context-label" data-map-context hidden>Ancestor</span>' +
        (count ? '<button type="button" class="map-node-children" data-map-toggle="' + n.id + '" aria-expanded="' + !collapsed.has(n.id) + '" aria-label="' + esc((collapsed.has(n.id) ? 'Show ' : 'Hide ') + count + ' subtasks of ' + n.title) + '">' + count + ' subtasks <span aria-hidden="true">' + (collapsed.has(n.id) ? '›' : '⌄') + '</span></button>' : '') + '</div><a class="task-map-node-title" href="/life/tasks/' + n.id + '" title="' + esc(n.title) + '">' + esc(n.title) + '</a><div class="task-map-node-meta"><span>' + esc(n.due_on || 'No due date') + '</span>' + (['high', 'urgent'].includes(n.priority) ? '<span>' + esc(n.priority) + ' priority</span>' : '') + '</div></article>';
    }).join('');
    elements = new Map([...nodeLayer.querySelectorAll('[data-map-node]')].map(el => [Number(el.dataset.mapNode), el]));
    const rootPoints = roots().filter(n => visible.has(n.id)).map(n => points.get(n.id));
    hub = orientation === 'vertical'
      ? {x: rootPoints.length ? (rootPoints[0].x + rootPoints.at(-1).x) / 2 : 0, y: rootPoints.length ? Math.min(...rootPoints.map(p => p.y)) - COLUMN * DEPTH_SCALE : 0}
      : {x: rootPoints.length ? Math.min(...rootPoints.map(p => p.x)) - COLUMN : 0, y: rootPoints.length ? (rootPoints[0].y + rootPoints.at(-1).y) / 2 : 0};
    let hubElement = world.querySelector('.task-map-hub');
    if (!hubElement) { hubElement = document.createElement('div'); hubElement.className = 'task-map-hub'; world.append(hubElement); }
    hubElement.textContent = title;
    hubElement.style.transform = 'translate(' + hub.x + 'px,' + hub.y + 'px)';
    buildEdges(); applyVisibility(); select(selected);
    $('[data-map-empty]').hidden = !!data.nodes.length;
    if (data.limit) {
      root.querySelectorAll('[data-map-add],[data-map-empty-add],[data-map-arrange],[data-map-search]').forEach(el => el.disabled = true);
      $('[data-map-empty]').innerHTML = '<strong>Keep this big project in view</strong><p>The Task map supports up to ' + data.limit.toLocaleString() + ' tasks. Every task is still available in List and Board.</p><a class="mlo-btn mlo-primary" href="/life/projects/' + pid + '?view=list">Open task list</a>';
      say('Use List or Board for projects with more than ' + data.limit.toLocaleString() + ' tasks.');
    }
    built = true; needsRender = false;
    if (initial && workspace.open) {
      if (taskFilter !== 'all' && viewport.clientWidth >= 700) fit(); else home();
    } else setTransform();
  }
  function openWindow() {
    const firstOpen = !built;
    workspace.showModal();
    if (!built || needsRender) render(firstOpen);
    requestAnimationFrame(() => {
      if (firstOpen) { if (taskFilter !== 'all' && viewport.clientWidth >= 700) fit(); else home(); }
      viewport.focus({preventScroll: true}); updateOverview();
    });
  }
  function closeWindow() { workspace.close(); }
  workspace.addEventListener('close', () => {
    pointer = null; gesture = null; activePointers.clear();
    cancelAnimationFrame(frame); frame = 0;
    if ((dirty.size || pendingReset) && !layoutConflict) { clearTimeout(layoutTimer); saveLayout(); }
    preview(); $('[data-map-expand]').focus({preventScroll: true});
  });
  function changed(id) {
    undoArrange = null; $('[data-map-undo]').hidden = true;
    dirty.set(id, fromView(points.get(id)));
    say('Saving layout…'); clearTimeout(layoutTimer); layoutTimer = setTimeout(saveLayout, 350);
  }
  async function saveLayout(reset = false) {
    pendingReset ||= reset;
    if (layoutSaving || layoutConflict) return;
    layoutSaving = true; $('[data-map-retry]').hidden = true;
    say('Saving layout…'); undoButton.disabled = true;
    const batch = new Map(dirty), resetting = pendingReset;
    try {
      const result = await request('/map/layout', {method: 'PUT', body: {points: [...batch].map(([id, p]) => ({id, ...p})), expected_version: data.version, reset: resetting}});
      pendingReset = false; data.version = result.version; data.positions = result.positions;
      for (const [id, p] of batch) if (dirty.get(id)?.x === p.x && dirty.get(id)?.y === p.y) dirty.delete(id);
      say(dirty.size ? 'Saving newer layout…' : 'Layout saved to your account.');
    } catch (error) {
      layoutConflict = error.status === 409;
      say(error.message, true);
      $('[data-map-retry]').hidden = false;
      $('[data-map-retry]').textContent = layoutConflict ? 'Reload saved layout' : 'Retry layout save';
    } finally {
      layoutSaving = false; undoButton.disabled = false;
      $('[data-map-undo]').hidden = !undoArrange || layoutConflict;
      if (dirty.size && !layoutConflict && $('[data-map-retry]').hidden) layoutTimer = setTimeout(saveLayout, 350);
    }
  }
  function openTask(id) { elements.get(id)?.querySelector('.task-map-node-title').click(); }
  async function reload() {
    data = await request('/map'); render();
    if (workspace.open && selected) select(selected, true);
  }
  async function mutate(path, body) {
    if (mutation) return false;
    mutation = true; say('Saving task…');
    try {
      const result = await request(path, {method: 'POST', body});
      if (result.board) {
        const all = [], walk = n => { all.push(n); n.children.forEach(walk); };
        Object.values(result.board.columns).flat().forEach(walk);
        data.nodes = all; data.total = all.length;
        data.edges = data.edges.filter(e => e.kind !== 'parent');
        const ids = new Set(all.map(n => n.id));
        data.edges.push(...all.filter(n => ids.has(n.parent_id)).map(n => ({from: n.parent_id, to: n.id, kind: 'parent'})));
      } else data = result;
      render(); say('Task saved.'); return true;
    } catch (error) { say(error.message, true); return false; }
    finally { mutation = false; }
  }
  function dialog(markup) {
    const d = document.createElement('dialog');
    d.className = 'task-map-dialog'; d.setAttribute('aria-labelledby', 'map-dialog-title'); d.innerHTML = markup;
    document.body.append(d);
    d.addEventListener('close', () => { d.remove(); if (selected) select(selected, true); else viewport.focus({preventScroll: true}); });
    d.querySelector('[data-cancel]').onclick = () => d.close();
    d.showModal(); return d;
  }
  function addTask(parent = null) {
    const d = dialog('<form><h2 id="map-dialog-title">' + (parent ? 'Add a subtask' : 'Add a task') + '</h2><p class="map-dialog-intro">' + (parent ? 'Break this task into a clear next step.' : 'Start with a name. You can add details when you need them.') + '</p><label>Task name<input name="title" required maxlength="240" autocomplete="off"></label><label>Subtask of<select name="parent_id"><option value="">Project — top-level task</option>' + data.nodes.map(n => '<option value="' + n.id + '" ' + (n.id === parent ? 'selected' : '') + '>' + esc(n.title) + '</option>').join('') + '</select></label><p role="alert"></p><div class="record-actions"><button class="mlo-btn mlo-secondary" type="button" data-cancel>Cancel</button><button class="mlo-btn mlo-primary" type="submit">Add task</button></div></form>');
    d.querySelector('input').focus();
    d.querySelector('form').onsubmit = async e => {
      e.preventDefault();
      const button = e.target.querySelector('[type=submit]');
      if (button.disabled) return;
      button.disabled = true;
      try {
        const body = new URLSearchParams(new FormData(e.target)); body.set('project_id', pid);
        const response = await fetch('/life/tasks', {method: 'POST', credentials: 'same-origin', headers: {Accept: 'application/json', 'X-MLO-Action': 'fetch'}, body});
        const item = await response.json();
        if (!response.ok) throw Error(item.detail || 'Could not add task.');
        selected = item.id; window.MLOTasks.created(item);
        d.close(); select(selected, true); centerOn(selected, true); say('Task added.');
      } catch (error) { d.querySelector('[role=alert]').textContent = error.message; button.disabled = false; }
    };
  }
  function relationships() {
    const n = nodes.get(selected);
    if (!n) return;
    const prerequisites = data.edges.filter(e => e.kind === 'prerequisite' && e.to === n.id).map(e => e.from);
    const others = data.nodes.filter(t => t.id !== n.id);
    const d = dialog('<form><h2 id="map-dialog-title">Connect this task</h2><p class="map-dialog-intro">' + esc(n.title) + '</p><label>Subtask of<select name="parent_id"><option value="">Project — top-level task</option>' + others.map(t => '<option value="' + t.id + '" ' + (t.id === n.parent_id ? 'selected' : '') + '>' + esc(t.title) + '</option>').join('') + '</select></label><p class="map-dialog-intro">A subtask belongs inside another task. A prerequisite is a task that must finish before this one can be completed.</p><label>Find a prerequisite<input type="search" data-prerequisite-search placeholder="Search task names" autocomplete="off"></label><fieldset class="task-map-prerequisites"><legend>Must finish first</legend>' + others.map(t => '<label data-prerequisite-title="' + esc(t.title.toLocaleLowerCase()) + '"><input type="checkbox" name="prerequisite" value="' + t.id + '" ' + (prerequisites.includes(t.id) ? 'checked' : '') + '><span>' + esc(t.title) + '</span></label>').join('') + (others.length ? '' : '<p>No other tasks yet.</p>') + '</fieldset><p class="map-prerequisite-summary" data-prerequisite-summary></p><p role="alert"></p><div class="record-actions"><button class="mlo-btn mlo-secondary" type="button" data-cancel>Cancel</button><button class="mlo-btn mlo-primary" type="submit">Save connections</button></div></form>');
    const summary = () => d.querySelector('[data-prerequisite-summary]').textContent = d.querySelectorAll('[name=prerequisite]:checked').length + ' prerequisites selected';
    summary(); d.addEventListener('change', summary);
    d.querySelector('[data-prerequisite-search]').addEventListener('input', e => {
      const q = e.target.value.trim().toLocaleLowerCase();
      d.querySelectorAll('[data-prerequisite-title]').forEach(el => el.hidden = !el.dataset.prerequisiteTitle.includes(q) && !el.querySelector('input').checked);
    });
    d.querySelector('form').onsubmit = async e => {
      e.preventDefault();
      const button = e.target.querySelector('[type=submit]'); button.disabled = true;
      const fd = new FormData(e.target);
      try {
        data = await request('/map/relationships', {method: 'POST', body: {task_id: n.id, parent_id: fd.get('parent_id') ? Number(fd.get('parent_id')) : null, prerequisites: fd.getAll('prerequisite').map(Number), expected_updated_at: n.updated_at}});
        render(); d.close(); say('Connections saved.');
      } catch (error) { d.querySelector('[role=alert]').textContent = error.message; button.disabled = false; }
    };
  }
  function arrange() {
    if (layoutConflict) { say('Reload the saved layout before arranging again.', true); return; }
    if (layoutSaving) { say('Wait for the current layout save, then arrange.'); return; }
    undoArrange = {
      points: new Map([...points].map(([id, p]) => [id, {...p}])),
      positions: {...data.positions},
      pending: new Map([...dirty].map(([id, p]) => [id, {...p}]))
    };
    clearTimeout(layoutTimer); points.clear(); data.positions = {}; dirty.clear();
    render(); fit(); say('Arranging…'); saveLayout(true);
  }
  function reflow() {
    // Preserve explicitly saved/unsaved card positions; recompute only automatic ones.
    points = new Map([...points].filter(([id]) => data.positions[id] || dirty.has(id)));
    render();
  }
  const allButton = document.createElement('button');
  allButton.type = 'button'; allButton.className = 'mlo-link-btn'; allButton.dataset.mapExpandAll = ''; allButton.hidden = true;
  status.parentElement.append(allButton);
  const undoButton = document.createElement('button');
  undoButton.type = 'button'; undoButton.className = 'mlo-link-btn'; undoButton.dataset.mapUndo = ''; undoButton.hidden = true; undoButton.textContent = 'Undo arrange';
  status.parentElement.append(undoButton);
  root.addEventListener('click', e => {
    const button = e.target.closest('button');
    if (!button) return;
    if (button.matches('[data-map-expand]')) openWindow();
    else if (button.matches('[data-map-close]')) closeWindow();
    else if (button.matches('[data-map-fit]')) fit();
    else if (button.dataset.mapZoom) zoom(button.dataset.mapZoom === '1' ? 1.2 : 1 / 1.2);
    else if (button.matches('[data-map-actual]')) zoom(1 / pan.z);
    else if (button.matches('[data-map-add],[data-map-empty-add]')) addTask();
    else if (button.matches('[data-map-child]')) addTask(selected);
    else if (button.matches('[data-map-relate]')) relationships();
    else if (button.matches('[data-map-open]')) openTask(selected);
    else if (button.matches('[data-map-clear]')) select(null);
    else if (button.dataset.mapToggle) {
      const id = Number(button.dataset.mapToggle);
      if (collapsed.has(id)) collapsed.delete(id); else collapsed.add(id);
      reflow(); select(id); centerOn(id);
    } else if (button.matches('[data-map-expand-all]')) { collapsed.clear(); focusRoot = null; reflow(); fit(); }
    else if (button.matches('[data-map-arrange]')) arrange();
    else if (button.matches('[data-map-undo]')) {
      if (!undoArrange || layoutSaving || layoutConflict) return;
      const previous = undoArrange;
      points = new Map(previous.points); data.positions = {...previous.positions}; undoArrange = null;
      dirty.clear();
      // Automatic, especially folded, card positions must stay automatic after Undo.
      for (const [id, p] of Object.entries(previous.positions)) if (nodes.has(Number(id))) dirty.set(Number(id), {...p});
      for (const [id, p] of previous.pending) if (nodes.has(id)) dirty.set(id, {...p});
      render(); saveLayout(true);
    } else if (button.matches('[data-map-focus]')) {
      search = ''; $('[data-map-search]').value = ''; focusRoot = selected; reflow(); fit();
    } else if (button.matches('[data-map-show-all]')) { focusRoot = null; search = ''; $('[data-map-search]').value = ''; reflow(); fit(); }
    else if (button.matches('[data-map-retry]')) {
      if (layoutConflict) {
        if ((dirty.size || pendingReset) && !confirm('Reload the saved layout? Your unsaved card positions will be replaced.')) return;
        dirty.clear(); points.clear(); pendingReset = false; layoutConflict = false; undoArrange = null;
        reload().then(() => { fit(); say('Saved layout loaded.'); $('[data-map-retry]').hidden = true; $('[data-map-undo]').hidden = true; }).catch(error => say(error.message, true));
      } else saveLayout();
    } else if (button.dataset.mapComplete) {
      const n = nodes.get(Number(button.dataset.mapComplete));
      mutate('/move', {task_id: n.id, status: n.status === 'done' ? 'todo' : 'done', expected_updated_at: n.updated_at});
    } else if (button.matches('[data-map-earlier],[data-map-later]')) {
      const n = nodes.get(selected);
      if (!n) return;
      const siblings = (children.get(n.parent_id) || []).filter(t => t.status === n.status), i = siblings.findIndex(t => t.id === n.id), earlier = button.hasAttribute('data-map-earlier');
      if (earlier && i === 0 || !earlier && i === siblings.length - 1) return;
      mutate('/move', {task_id: n.id, status: n.status, before_task_id: earlier ? siblings[i - 1].id : siblings[i + 2]?.id ?? null, expected_updated_at: n.updated_at});
    }
  });
  $('[data-map-connections]').addEventListener('change', edgeVisibility);
  $('[data-map-filter]').addEventListener('change', e => {
    taskFilter = e.target.value; rememberView(); reflow(); fit();
  });
  $('[data-map-orientation]').addEventListener('change', e => {
    const canonical = new Map([...points].map(([id, p]) => [id, fromView(p)]));
    orientation = e.target.value; rememberView();
    points = new Map([...canonical].map(([id, p]) => [id, toView(p)]));
    if (undoArrange) undoArrange.points = new Map([...undoArrange.points].map(([id, p]) => {
      // Undo snapshots belong to the previous orientation; transform them too.
      const raw = orientation === 'vertical' ? p : {x: p.y / DEPTH_SCALE, y: p.x / BREADTH_SCALE};
      return [id, toView(raw)];
    }));
    render(); fit();
  });
  $('[data-map-overview]').addEventListener('click', e => {
    if (!e.detail || !overview.contains(e.target)) { fit(); return; }
    const matrix = overview.getScreenCTM();
    if (!matrix) return;
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix.inverse());
    pan.x = viewport.clientWidth / 2 - point.x * pan.z; pan.y = viewport.clientHeight / 2 - point.y * pan.z; setTransform();
  });
  let searchTimer;
  $('[data-map-search]').addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      search = e.target.value.trim().toLocaleLowerCase();
      const scope = activeIds();
      if (search && focusRoot && !data.nodes.some(n => scope.has(n.id) && n.title.toLocaleLowerCase().includes(search))) focusRoot = null;
      const match = data.nodes.find(n => matchesStatus(n) && n.title.toLocaleLowerCase().includes(search));
      let expanded = false, parent = match?.parent_id;
      while (nodes.has(parent)) { expanded = collapsed.delete(parent) || expanded; parent = nodes.get(parent).parent_id; }
      if (expanded) reflow(); else applyVisibility();
      if (search && match) { select(match.id); centerOn(match.id, true); }
    }, 100);
  });
  function beginGesture() {
    if (pointer?.id && pointer.moved) changed(pointer.id);
    pointer = null;
    const [a, b] = [...activePointers.values()];
    gesture = {distance: Math.max(1, Math.hypot(b.x - a.x, b.y - a.y)), x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, pan: {...pan}};
  }
  viewport.addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    const control = e.target.closest('button,input,select,textarea');
    if (control && e.pointerType !== 'touch') return;
    activePointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (activePointers.size > 1) {
      for (const id of activePointers.keys()) viewport.setPointerCapture(id);
      if (activePointers.size === 2) beginGesture(); return;
    }
    // A one-finger tap still activates a control. A second finger turns the
    // interaction into a pinch even when the first finger landed on a button.
    if (control) return;
    viewport.setPointerCapture(e.pointerId);
    const node = e.target.closest('[data-map-node]'), id = node ? Number(node.dataset.mapNode) : null;
    pointer = {pointerId: e.pointerId, id, startX: e.clientX, startY: e.clientY, x: e.clientX, y: e.clientY, pan: {...pan}, point: id ? {...points.get(id)} : null, moved: false, link: e.target.closest('a')};
    // Opening the phone details pane on the first touch resizes the canvas
    // underneath the second finger. Select after a tap/drag completes instead.
    if (id && e.pointerType !== 'touch') select(id);
  });
  function drawPointer() {
    frame = 0;
    if (gesture && activePointers.size >= 2) {
      const [a, b] = [...activePointers.values()], rect = viewport.getBoundingClientRect();
      const z = clamp(gesture.pan.z * Math.hypot(b.x - a.x, b.y - a.y) / gesture.distance, .12, 2);
      pan.x = (a.x + b.x) / 2 - rect.left - (gesture.x - rect.left - gesture.pan.x) * z / gesture.pan.z;
      pan.y = (a.y + b.y) / 2 - rect.top - (gesture.y - rect.top - gesture.pan.y) * z / gesture.pan.z;
      pan.z = z; setTransform(); return;
    }
    if (!pointer) return;
    const dx = pointer.x - pointer.startX, dy = pointer.y - pointer.startY;
    if (pointer.id) moveNode(pointer.id, {x: clamp(pointer.point.x + dx / pan.z, -1000000, 1000000), y: clamp(pointer.point.y + dy / pan.z, -1000000, 1000000)});
    else { pan.x = pointer.pan.x + dx; pan.y = pointer.pan.y + dy; setTransform(); }
  }
  viewport.addEventListener('pointermove', e => {
    if (!activePointers.has(e.pointerId)) return;
    activePointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (gesture || pointer?.pointerId === e.pointerId) {
      if (pointer) {
        pointer.x = e.clientX; pointer.y = e.clientY;
        pointer.moved ||= Math.hypot(e.clientX - pointer.startX, e.clientY - pointer.startY) > 5;
      }
      if (gesture || pointer?.moved) {
        viewport.classList.add('is-dragging');
        if (!frame) frame = requestAnimationFrame(drawPointer);
      }
    }
  });
  function suppress() { suppressClick = true; setTimeout(() => suppressClick = false, 0); }
  viewport.addEventListener('pointerup', e => {
    if (!activePointers.has(e.pointerId)) return;
    cancelAnimationFrame(frame); frame = 0;
    if (gesture) {
      drawPointer(); activePointers.delete(e.pointerId); gesture = null; pointer = null; suppress();
    } else if (pointer?.pointerId === e.pointerId) {
      const p = pointer;
      if (p.moved) {
        drawPointer(); suppress();
        if (p.id) { moveNode(p.id, freePoint(points.get(p.id), p.id)); changed(p.id); drawOverview(); }
        else if (!p.id) setTransform();
      } else if (p.link) { p.link.click(); suppress(); }
      else if (!p.id) select(null);
      if (p.id) select(p.id);
      activePointers.delete(e.pointerId); pointer = null;
    } else activePointers.delete(e.pointerId);
    viewport.classList.remove('is-dragging');
  });
  viewport.addEventListener('pointercancel', e => {
    activePointers.delete(e.pointerId);
    if (pointer?.id) moveNode(pointer.id, pointer.point);
    pointer = null; gesture = null; cancelAnimationFrame(frame); frame = 0; viewport.classList.remove('is-dragging');
  });
  viewport.addEventListener('click', e => {
    if (suppressClick) { e.preventDefault(); e.stopImmediatePropagation(); }
    else { const node = e.target.closest('[data-map-node]'); if (node) select(node.dataset.mapNode); }
  }, true);
  viewport.addEventListener('focusin', e => {
    const node = e.target.closest('[data-map-node]');
    if (!node) return;
    const box = node.getBoundingClientRect(), view = viewport.getBoundingClientRect();
    if (box.left < view.left + 8 || box.right > view.right - 8 || box.top < view.top + 8 || box.bottom > view.bottom - 8) centerOn(Number(node.dataset.mapNode));
  });
  viewport.addEventListener('wheel', e => {
    e.preventDefault();
    const unit = e.deltaMode === 1 ? 32 : e.deltaMode === 2 ? viewport.clientHeight : 1;
    const dx = e.deltaX * unit, dy = e.deltaY * unit;
    if (e.ctrlKey || e.metaKey) { const rect = viewport.getBoundingClientRect(); zoom(Math.exp(-dy * .002), e.clientX - rect.left, e.clientY - rect.top); }
    else { pan.x -= e.shiftKey && !dx ? dy : dx; pan.y -= e.shiftKey ? 0 : dy; setTransform(); }
  }, {passive: false});
  viewport.addEventListener('keydown', e => {
    if (e.target.closest('input,select,button,a')) return;
    const node = e.target.closest('[data-map-node]'), step = e.shiftKey ? 80 : 24;
    if (e.key === 'Enter' && node) { e.preventDefault(); openTask(Number(node.dataset.mapNode)); return; }
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
      e.preventDefault();
      const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0, dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
      if (node) {
        const id = Number(node.dataset.mapNode), p = points.get(id);
        moveNode(id, freePoint({x: clamp(p.x + dx, -1000000, 1000000), y: clamp(p.y + dy, -1000000, 1000000)}, id));
        changed(id); drawOverview();
      } else { pan.x -= dx; pan.y -= dy; setTransform(); }
    } else if (e.key === '+' || e.key === '=') { e.preventDefault(); zoom(1.2); }
    else if (e.key === '-') { e.preventDefault(); zoom(1 / 1.2); }
    else if (e.key === '0') { e.preventDefault(); zoom(1 / pan.z); }
    else if (e.key.toLowerCase() === 'f') { e.preventDefault(); fit(); }
  });
  document.addEventListener('mlo:task-created', e => {
    const n = e.detail;
    if (Number(n.project_id) !== pid || nodes.has(n.id)) return;
    if (data.limit) { data.total++; preview(); return; }
    if (data.nodes.length >= 2000) { data.limit = 2000; data.total = data.nodes.length + 1; data.nodes = []; data.edges = []; render(); return; }
    data.nodes.push(n); data.total = data.nodes.length;
    if (n.parent_id) data.edges.push({from: n.parent_id, to: n.id, kind: 'parent'});
    const parent = points.get(n.parent_id);
    if (parent) points.set(n.id, freePoint(orientation === 'vertical' ? {x: parent.x + W + ROW_GAP, y: parent.y + H + 150} : {x: parent.x + COLUMN, y: parent.y + H + ROW_GAP}, n.id));
    undoArrange = null; undoButton.hidden = true; render(); say('Task added.');
  });
  document.addEventListener('mlo:task-updated', e => {
    if (e.detail?.project_id && Number(e.detail.project_id) !== pid) return;
    reload().catch(error => say(error.message, true));
  });
  window.addEventListener('beforeunload', e => { if (dirty.size || pendingReset) { e.preventDefault(); e.returnValue = ''; } });
  let oldSize = null, resized;
  new ResizeObserver(() => {
    clearTimeout(resized);
    resized = setTimeout(() => {
      if (!workspace.open || pointer || gesture) return;
      const size = {w: viewport.clientWidth, h: viewport.clientHeight};
      if (oldSize?.w && oldSize?.h) { pan.x += (size.w - oldSize.w) / 2; pan.y += (size.h - oldSize.h) / 2; }
      oldSize = size; setTransform();
      // Keep at least one card on screen when the window becomes much smaller.
      // Preserving the same center can otherwise strand a phone in empty space.
      if (visible.size && ![...visible].some(id => {
        const p = points.get(id), x = p.x * pan.z + pan.x, y = p.y * pan.z + pan.y;
        return x + W * pan.z > 0 && x < size.w && y + H * pan.z > 0 && y < size.h;
      })) centerOn(visible.has(selected) ? selected : roots().find(n => visible.has(n.id))?.id ?? [...visible][0]);
    }, 60);
  }).observe(viewport);
  index();
  if (data.nodes.length > 40) {
    for (const n of data.nodes) if (nodes.has(n.parent_id) && children.has(n.id)) collapsed.add(n.id);
  }
  preview();
})();
