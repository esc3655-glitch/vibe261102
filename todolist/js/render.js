import { formatKorean } from './date.js';
import {
  sortTodos, filterTodos, progress, carryOverCandidates, PRIORITY_LABEL, MAX_TEXT,
} from './todo.js';
import { ICONS } from './icons.js';

const $ = (id) => document.getElementById(id);

const THEME_ICON = { system: ICONS.system, light: ICONS.sun, dark: ICONS.moon };
const THEME_LABEL = { system: '시스템', light: '라이트', dark: '다크' };

function el(tag, props = {}) {
  return Object.assign(document.createElement(tag), props);
}

// 사용자 입력은 항상 textContent / value로만 넣는다 (HTML 삽입 금지)
function renderItem(todo, editing, draft) {
  const li = el('li', { className: `item${todo.done ? ' done' : ''}` });
  li.dataset.id = todo.id;

  const toggle = el('input', { type: 'checkbox', className: 'toggle', checked: todo.done });
  toggle.setAttribute('aria-label', `${todo.text} 완료`);

  const dot = el('button', { type: 'button', className: `dot dot-${todo.priority}` });
  dot.dataset.action = 'priority';
  dot.title = `우선순위: ${PRIORITY_LABEL[todo.priority]} (클릭하여 변경)`;
  dot.setAttribute('aria-label', dot.title);

  li.append(toggle, dot);

  if (editing) {
    const input = el('input', {
      type: 'text', className: 'edit-input', value: draft ?? todo.text, maxLength: MAX_TEXT,
    });
    input.setAttribute('aria-label', '할 일 수정');
    li.append(input);
  } else {
    li.append(el('span', { className: 'text', textContent: todo.text }));
    const edit = el('button', { type: 'button', className: 'item-btn', innerHTML: ICONS.pencil });
    edit.dataset.action = 'edit';
    edit.setAttribute('aria-label', `${todo.text} 수정`);
    li.append(edit);
  }

  const del = el('button', { type: 'button', className: 'item-btn delete', innerHTML: ICONS.close });
  del.dataset.action = 'delete';
  del.setAttribute('aria-label', `${todo.text} 삭제`);
  li.append(del);

  return li;
}

function emptyMessage(total, done, visibleCount, filter) {
  if (total === 0) return '오늘 할 일을 추가해 보세요 🐾';
  if (done === total && filter !== 'done') return '오늘 할 일을 모두 끝냈어요! 🐾🎉';
  if (visibleCount === 0) return filter === 'active' ? '진행 중인 할 일이 없어요' : '완료된 항목이 없어요';
  return '';
}

export function render(state) {
  const { settings, today } = state;

  const root = document.documentElement;
  if (settings.theme === 'system') delete root.dataset.theme;
  else root.dataset.theme = settings.theme;
  const themeBtn = $('theme-toggle');
  themeBtn.innerHTML = THEME_ICON[settings.theme];
  themeBtn.title = `테마: ${THEME_LABEL[settings.theme]} (클릭하여 변경)`;
  themeBtn.setAttribute('aria-label', themeBtn.title);

  $('today').textContent = formatKorean(today);
  $('storage-warning').hidden = state.storageOk;

  const todays = state.todos.filter((t) => t.date === today);
  const { total, done, percent } = progress(todays);
  $('progress-fill').style.width = `${percent}%`;
  $('progress-bar').setAttribute('aria-valuenow', String(percent));
  $('progress-text').textContent = total
    ? `${total}개 중 ${done}개 완료 (${percent}%)`
    : '아직 할 일이 없어요';

  const carryCount = carryOverCandidates(state.todos, today).length;
  $('carry-banner').hidden = !(state.showCarry && carryCount > 0);
  $('carry-text').textContent = `지난 날 못 끝낸 할 일 ${carryCount}개가 있어요. 오늘로 가져올까요?`;

  document.querySelectorAll('[data-filter]').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(btn.dataset.filter === settings.filter));
  });

  // 다시 그려도 편집 중인 입력값과 커서를 잃지 않도록 보존
  const list = $('list');
  const prevEdit = list.querySelector('.edit-input');
  const prevEditId = prevEdit?.closest('.item').dataset.id;
  const draft = prevEditId === state.editingId ? prevEdit.value : undefined;
  const hadFocus = prevEdit && document.activeElement === prevEdit;

  const visible = sortTodos(filterTodos(todays, settings.filter));
  list.replaceChildren(...visible.map((t) => renderItem(t, t.id === state.editingId, draft)));

  const editInput = list.querySelector('.edit-input');
  if (editInput && (draft === undefined || hadFocus)) {
    editInput.focus();
    if (draft === undefined) editInput.setSelectionRange(editInput.value.length, editInput.value.length);
  }

  const message = emptyMessage(total, done, visible.length, settings.filter);
  $('empty').textContent = message;
  $('empty').hidden = !message;

  $('clear-done').disabled = done === 0;

  $('toast').hidden = !state.lastDeleted;
  if (state.lastDeleted) $('toast-text').textContent = `'${state.lastDeleted.todo.text}' 삭제됨`;
}
