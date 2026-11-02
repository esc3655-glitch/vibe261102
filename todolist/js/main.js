import { createStore } from './store.js';
import { render } from './render.js';
import { todayKey } from './date.js';
import { isValidText } from './todo.js';

const PRIORITY_CYCLE = { high: 'normal', normal: 'low', low: 'high' };
const THEME_CYCLE = { system: 'light', light: 'dark', dark: 'system' };
const UNDO_MS = 5000;
const DAY_CHECK_MS = 60 * 1000;

const store = createStore();
const { dispatch } = store;
const $ = (id) => document.getElementById(id);

store.subscribe(render);
render(store.getState());

const itemId = (target) => target.closest('.item')?.dataset.id;

// 할 일 추가
$('add-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = $('new-text');
  if (isValidText(input.value)) {
    dispatch({ type: 'ADD', text: input.value, priority: $('new-priority').value });
    input.value = '';
  }
  input.focus();
});

// 목록 이벤트 (위임)
const list = $('list');

list.addEventListener('change', (e) => {
  if (e.target.matches('.toggle')) dispatch({ type: 'TOGGLE', id: itemId(e.target) });
});

let undoTimer;

list.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const id = itemId(btn);
  const todo = store.getState().todos.find((t) => t.id === id);
  if (!todo) return;

  if (btn.dataset.action === 'priority') {
    dispatch({ type: 'SET_PRIORITY', id, priority: PRIORITY_CYCLE[todo.priority] });
  } else if (btn.dataset.action === 'edit') {
    dispatch({ type: 'START_EDIT', id });
  } else if (btn.dataset.action === 'delete') {
    dispatch({ type: 'DELETE', id });
    clearTimeout(undoTimer);
    undoTimer = setTimeout(() => dispatch({ type: 'CLEAR_UNDO', id }), UNDO_MS);
  }
});

list.addEventListener('dblclick', (e) => {
  if (e.target.matches('.text')) dispatch({ type: 'START_EDIT', id: itemId(e.target) });
});

list.addEventListener('keydown', (e) => {
  if (!e.target.matches('.edit-input')) return;
  // 한글 조합 중 Enter는 무시
  if (e.isComposing || e.keyCode === 229) return;
  if (e.key === 'Enter') {
    e.preventDefault();
    dispatch({ type: 'EDIT', id: itemId(e.target), text: e.target.value });
  } else if (e.key === 'Escape') {
    dispatch({ type: 'CANCEL_EDIT' });
  }
});

list.addEventListener('focusout', (e) => {
  if (!e.target.matches('.edit-input')) return;
  const id = itemId(e.target);
  if (store.getState().editingId === id) dispatch({ type: 'EDIT', id, text: e.target.value });
});

// 삭제 되돌리기
$('toast-undo').addEventListener('click', () => {
  clearTimeout(undoTimer);
  dispatch({ type: 'UNDO_DELETE' });
});

// 필터
document.querySelectorAll('[data-filter]').forEach((btn) => {
  btn.addEventListener('click', () => dispatch({ type: 'SET_FILTER', filter: btn.dataset.filter }));
});

// 완료 항목 일괄 삭제
$('clear-done').addEventListener('click', () => {
  if (confirm('오늘 완료한 항목을 모두 지울까요?')) dispatch({ type: 'CLEAR_DONE' });
});

// 미완료 이월
$('carry-accept').addEventListener('click', () => dispatch({ type: 'CARRY_OVER' }));
$('carry-dismiss').addEventListener('click', () => dispatch({ type: 'DISMISS_CARRY' }));

// 테마
$('theme-toggle').addEventListener('click', () => {
  dispatch({ type: 'SET_THEME', theme: THEME_CYCLE[store.getState().settings.theme] });
});

// 자정 경과 감지
const checkDay = () => dispatch({ type: 'DAY_CHANGED', today: todayKey() });
setInterval(checkDay, DAY_CHECK_MS);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') checkDay();
});
