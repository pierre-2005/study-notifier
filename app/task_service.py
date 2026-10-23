"""Shared task transitions and bounded hierarchy operations.

Callers hold a write transaction before reading tasks. No network side effects.
"""
from fastapi import HTTPException

from app.lifeos import now, next_due, task_access

MAX_DEPTH = 8
STATUSES = ('todo', 'doing', 'blocked', 'done')


def transition(db, uid, task_id, status, *, completing=()):
    if status not in STATUSES:
        raise HTTPException(422, 'Invalid task status')
    task = task_access(db, uid, task_id, edit=True)
    if status == 'done' and task['status'] != 'done':
        blockers = db.execute('''SELECT t.id FROM life_task_dependencies d
            JOIN life_tasks t ON t.id=d.depends_on_id
            WHERE d.task_id=? AND t.status!='done' ''', (task_id,)).fetchall()
        if any(row['id'] not in completing for row in blockers):
            raise HTTPException(409, 'Complete prerequisites before finishing this task')
    if status == task['status']:
        return task
    ts = now()
    db.execute('UPDATE life_tasks SET status=?,completed_at=?,updated_at=? WHERE id=?',
               (status, ts if status == 'done' else None, ts, task_id))
    from app.consolidation import mirror_legacy_status
    mirror_legacy_status(db, task_id, status)
    if status == 'done' and task['recurrence'] != 'none':
        existing = db.execute('SELECT 1 FROM life_task_successors WHERE source_id=?', (task_id,)).fetchone()
        if not existing:
            cur = db.execute('''INSERT INTO life_tasks
                (owner_id,project_id,parent_id,title,description,status,priority,area,due_on,
                 estimated_minutes,recurrence,position,created_at,updated_at)
                VALUES(?,?,?,?,?,'todo',?,?,?,?,?,?,?,?)''',
                (task['owner_id'], task['project_id'], task['parent_id'], task['title'],
                 task['description'], task['priority'], task['area'],
                 next_due(task['due_on'], task['recurrence']), task['estimated_minutes'],
                 task['recurrence'], task['position'] + 1, ts, ts))
            db.execute('INSERT INTO life_task_successors(source_id,successor_id) VALUES(?,?)',
                       (task_id, cur.lastrowid))
    return task


def validate_parent(db, uid, task_id, parent_id, project_id):
    """Check both ancestor depth and the depth of the entire moved subtree."""
    if parent_id is None:
        parent_depth = 0
    else:
        seen = {task_id} if task_id else set()
        current, parent_depth = parent_id, 0
        while current is not None:
            if current in seen:
                raise HTTPException(409, 'This would create a circular task hierarchy')
            seen.add(current)
            parent = task_access(db, uid, current, edit=True)
            if parent['project_id'] != project_id:
                raise HTTPException(422, 'Parent must belong to the same project')
            current = parent['parent_id']
            parent_depth += 1
            if parent_depth > MAX_DEPTH:
                raise HTTPException(422, 'Tasks support up to eight nested levels')
    height = 0
    if task_id:
        # The visited set bounds traversal even for damaged legacy cycles.
        rows = db.execute('SELECT id,parent_id FROM life_tasks WHERE project_id IS ?', (project_id,)).fetchall()
        children = {}
        for row in rows:
            children.setdefault(row['parent_id'], []).append(row['id'])
        stack, visited = [(task_id, 0)], set()
        while stack:
            current, depth = stack.pop()
            if current in visited:
                raise HTTPException(409, 'Repair the circular hierarchy before moving this task')
            visited.add(current)
            height = max(height, depth)
            stack.extend((child, depth + 1) for child in children.get(current, []))
    if parent_depth + height > MAX_DEPTH:
        raise HTTPException(422, 'The moved subtasks would exceed eight nested levels')


def task_forest(rows):
    """Never lose an orphan/cyclic legacy task or return a recursive JSON graph."""
    nodes = {r['id']: {**dict(r), 'children': [], 'subtask_total': 0, 'subtask_done': 0} for r in rows}
    roots = []
    for node in nodes.values():
        parent = nodes.get(node['parent_id'])
        seen, current, depth = {node['id']}, parent, 0
        while current:
            if current['id'] in seen or depth >= MAX_DEPTH:
                parent = None
                break
            seen.add(current['id'])
            current = nodes.get(current['parent_id'])
            depth += 1
        if parent:
            parent['children'].append(node)
        else:
            roots.append(node)
    def count(node):
        for child in node['children']:
            count(child)
            node['subtask_total'] += 1 + child['subtask_total']
            node['subtask_done'] += int(child['status'] == 'done') + child['subtask_done']
    for root in roots:
        count(root)
    return roots
