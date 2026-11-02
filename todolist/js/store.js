import { todayKey } from './date.js';
import {
  createTodo, normalizeText, isValidText, sanitizeTodos, carryOverCandidates, PRIORITIES,
} from './todo.js';

const PREFIX = 'todayTodo:v1:';
const KEYS = {
  todos: `${PREFIX}todos`,
  settings: `${PREFIX}settings`,
  lastOpened: `${PREFIX}lastOpenedDate`,
};
const THEMES = ['system', 'light', 'dark'];
const FILTERS = ['all', 'active', 'done'];

function storageAvailable() {
  try {
    const key = `${PREFIX}__test`;
    localStorage.setItem(key, '1');
    localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

function readRaw(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeRaw(key, value) {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

// 파싱 실패 시 원본을 '.corrupt'로 백업하고 기본값으로 시작
function readJSON(key, fallback) {
  const raw = readRaw(key);
  if (raw == null) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    writeRaw(`${key}.corrupt`, raw);
    return fallback;
  }
}

function loadSettings(raw) {
  const s = raw && typeof raw === 'object' ? raw : {};
  return {
    theme: THEMES.includes(s.theme) ? s.theme : 'system',
    filter: FILTERS.includes(s.filter) ? s.filter : 'all',
  };
}

function mapTodo(state, id, fn) {
  return { ...state, todos: state.todos.map((t) => (t.id === id ? fn(t) : t)) };
}

export function reduce(state, action) {
  switch (action.type) {
    case 'ADD':
      if (!isValidText(action.text)) return state;
      return { ...state, todos: [...state.todos, createTodo(action.text, action.priority, state.today)] };

    case 'TOGGLE':
      return mapTodo(state, action.id, (t) => {
        const { completedAt, ...rest } = t;
        return t.done ? { ...rest, done: false } : { ...rest, done: true, completedAt: Date.now() };
      });

    case 'START_EDIT':
      return { ...state, editingId: action.id };

    case 'CANCEL_EDIT':
      return state.editingId ? { ...state, editingId: null } : state;

    case 'EDIT': {
      // 유효하지 않은 입력(빈 값 등)은 원래 텍스트를 유지하고 편집만 종료
      const next = isValidText(action.text)
        ? mapTodo(state, action.id, (t) => ({ ...t, text: normalizeText(action.text) }))
        : state;
      return { ...next, editingId: null };
    }

    case 'DELETE': {
      const index = state.todos.findIndex((t) => t.id === action.id);
      if (index < 0) return state;
      return {
        ...state,
        todos: state.todos.filter((t) => t.id !== action.id),
        lastDeleted: { todo: state.todos[index], index },
        editingId: state.editingId === action.id ? null : state.editingId,
      };
    }

    case 'UNDO_DELETE': {
      if (!state.lastDeleted) return state;
      const { todo, index } = state.lastDeleted;
      const todos = [...state.todos];
      todos.splice(Math.min(index, todos.length), 0, todo);
      return { ...state, todos, lastDeleted: null };
    }

    case 'CLEAR_UNDO':
      return state.lastDeleted?.todo.id === action.id ? { ...state, lastDeleted: null } : state;

    case 'SET_PRIORITY':
      if (!PRIORITIES.includes(action.priority)) return state;
      return mapTodo(state, action.id, (t) => ({ ...t, priority: action.priority }));

    case 'CLEAR_DONE':
      return { ...state, todos: state.todos.filter((t) => !(t.done && t.date === state.today)) };

    case 'CARRY_OVER':
      return {
        ...state,
        todos: state.todos.map((t) => (!t.done && t.date < state.today ? { ...t, date: state.today } : t)),
        showCarry: false,
      };

    case 'DISMISS_CARRY':
      return { ...state, showCarry: false };

    case 'SET_FILTER':
      if (!FILTERS.includes(action.filter)) return state;
      return { ...state, settings: { ...state.settings, filter: action.filter } };

    case 'SET_THEME':
      if (!THEMES.includes(action.theme)) return state;
      return { ...state, settings: { ...state.settings, theme: action.theme } };

    case 'DAY_CHANGED':
      if (action.today === state.today) return state;
      return {
        ...state,
        today: action.today,
        editingId: null,
        showCarry: carryOverCandidates(state.todos, action.today).length > 0,
      };

    default:
      return state;
  }
}

export function createStore() {
  const storageOk = storageAvailable();
  const today = todayKey();
  const todos = storageOk ? sanitizeTodos(readJSON(KEYS.todos, [])) : [];
  const settings = loadSettings(storageOk ? readJSON(KEYS.settings, null) : null);
  const lastOpened = storageOk ? readRaw(KEYS.lastOpened) : null;

  let state = {
    todos,
    settings,
    today,
    storageOk,
    editingId: null,
    lastDeleted: null,
    // 이월 배너는 날짜가 바뀐 뒤 처음 열 때 한 번만
    showCarry: lastOpened !== today && carryOverCandidates(todos, today).length > 0,
  };
  if (storageOk) writeRaw(KEYS.lastOpened, today);

  const listeners = new Set();

  function persist(prev, next) {
    if (!next.storageOk) return true;
    let ok = true;
    if (prev.todos !== next.todos) ok = writeRaw(KEYS.todos, JSON.stringify(next.todos)) && ok;
    if (prev.settings !== next.settings) ok = writeRaw(KEYS.settings, JSON.stringify(next.settings)) && ok;
    if (prev.today !== next.today) ok = writeRaw(KEYS.lastOpened, next.today) && ok;
    return ok;
  }

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    dispatch(action) {
      const prev = state;
      const next = reduce(prev, action);
      if (next === prev) return;
      state = persist(prev, next) ? next : { ...next, storageOk: false };
      listeners.forEach((l) => l(state, action));
    },
  };
}
