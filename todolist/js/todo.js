export const MAX_TEXT = 100;
export const PRIORITIES = ['high', 'normal', 'low'];
export const PRIORITY_LABEL = { high: '높음', normal: '보통', low: '낮음' };

const PRIORITY_RANK = { high: 0, normal: 1, low: 2 };

export function normalizeText(text) {
  return String(text ?? '').trim();
}

export function isValidText(text) {
  const s = normalizeText(text);
  return s.length > 0 && s.length <= MAX_TEXT;
}

function newId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

export function createTodo(text, priority, date) {
  return {
    id: newId(),
    text: normalizeText(text),
    done: false,
    priority: PRIORITIES.includes(priority) ? priority : 'normal',
    date,
    createdAt: Date.now(),
  };
}

// 저장소에서 읽은 값 중 형태가 올바른 항목만 남긴다
export function sanitizeTodos(value) {
  if (!Array.isArray(value)) return [];
  return value.filter((t) =>
    t && typeof t.id === 'string' && typeof t.text === 'string' && typeof t.date === 'string'
  ).map((t) => ({
    ...t,
    done: Boolean(t.done),
    priority: PRIORITIES.includes(t.priority) ? t.priority : 'normal',
    createdAt: Number(t.createdAt) || 0,
  }));
}

// 미완료 → 완료, 미완료 안에서는 우선순위 높은 순 → 생성 순
export function sortTodos(list) {
  return [...list].sort((a, b) =>
    Number(a.done) - Number(b.done) ||
    PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority] ||
    a.createdAt - b.createdAt
  );
}

export function filterTodos(list, filter) {
  if (filter === 'active') return list.filter((t) => !t.done);
  if (filter === 'done') return list.filter((t) => t.done);
  return list;
}

export function progress(list) {
  const total = list.length;
  const done = list.filter((t) => t.done).length;
  return { total, done, percent: total ? Math.round((done / total) * 100) : 0 };
}

export function carryOverCandidates(todos, today) {
  return todos.filter((t) => !t.done && t.date < today);
}
