document.addEventListener('DOMContentLoaded', () => {
  try {
  const page = document.getElementById('page-hotwords');
  if (!page) return;

  const tablesEl = document.getElementById('hw-tables');
  const wordsEl = document.getElementById('hw-words');
  let currentTableId = null;
  let allTables = [];

  async function loadTables() {
    try {
      const res = await fetch('/api/hotwords/tables');
      allTables = await res.json();
      if (allTables.length === 0) {
        tablesEl.innerHTML = '<div class="placeholder" style="padding:16px;">暂无词表，请新建</div>';
        return;
      }
      tablesEl.innerHTML = allTables.map(t => `
        <div class="hw-table-item${t.id === currentTableId ? ' active' : ''}"
             data-id="${t.id}" onclick="window._selectTable(${t.id})">
          <div class="hw-table-name">${escHtml(t.name)}</div>
          <div class="hw-table-count">${t.word_count}词</div>
        </div>
      `).join('');
      if (currentTableId && !allTables.find(t => t.id === currentTableId)) {
        currentTableId = null;
        wordsEl.innerHTML = '<div class="placeholder">请选择一个词表</div>';
      }
    } catch (e) {
      tablesEl.innerHTML = '<div class="placeholder">加载失败</div>';
    }
  }

  window._selectTable = async function(id) {
    currentTableId = id;
    document.querySelectorAll('.hw-table-item').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.id) === id);
    });
    try {
      const res = await fetch(`/api/hotwords/tables/${id}/words`);
      const words = await res.json();
      renderWords(words);
    } catch (e) {
      wordsEl.innerHTML = '<div class="placeholder">加载失败</div>';
    }
  };

  function renderWords(words) {
    if (words.length === 0) {
      wordsEl.innerHTML = '<div class="placeholder">暂无热词</div>';
      return;
    }
    wordsEl.innerHTML = words.map(w => `
      <div class="hw-word-chip" data-id="${w.id}">
        <label class="hw-word-checkbox">
          <input type="checkbox" class="hw-word-cb" value="${w.id}" onchange="window._onWordCheck()">
        </label>
        <span class="hw-word-text">${escHtml(w.word)}</span>
        <span class="hw-word-del" onclick="window._deleteWord(${w.id})">&times;</span>
      </div>
    `).join('');
  }

  window._deleteWord = async function(id) {
    await fetch(`/api/hotwords/words/${id}`, { method: 'DELETE' });
    window._selectTable(currentTableId);
    syncHotwords();
    loadTables();
  };

  const wordCheckCbs = new Set();
  window._onWordCheck = function() {
    document.querySelectorAll('.hw-word-cb:checked').forEach(cb => wordCheckCbs.add(parseInt(cb.value)));
    document.querySelectorAll('.hw-word-cb:not(:checked)').forEach(cb => wordCheckCbs.delete(parseInt(cb.value)));
    document.getElementById('hw-del-selected').disabled = wordCheckCbs.size === 0;
  };

  document.getElementById('hw-add-word-btn').onclick = async () => {
    const input = document.getElementById('hw-add-word-input');
    const word = input.value.trim();
    if (!word) return;
    const err = validateWord(word);
    if (err) { alert(err); return; }
    try {
      const res = await fetch(`/api/hotwords/tables/${currentTableId}/words`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word })
      });
      if (!res.ok) {
        const data = await res.json();
        alert(data.error || '添加失败');
        return;
      }
      input.value = '';
      window._selectTable(currentTableId);
      syncHotwords();
      loadTables();
    } catch (e) {
      alert('添加失败');
    }
  };

  document.getElementById('hw-add-word-input').onkeydown = (e) => {
    if (e.key === 'Enter') document.getElementById('hw-add-word-btn').click();
  };

  document.getElementById('hw-del-selected').onclick = async () => {
    if (wordCheckCbs.size === 0) return;
    if (!confirm(`确定删除 ${wordCheckCbs.size} 个热词？`)) return;
    await fetch('/api/hotwords/words/delete_bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: Array.from(wordCheckCbs) })
    });
    wordCheckCbs.clear();
    document.getElementById('hw-del-selected').disabled = true;
    window._selectTable(currentTableId);
    syncHotwords();
    loadTables();
  };

  document.getElementById('hw-new-table-btn').onclick = () => {
    const name = prompt('请输入词表名称：');
    if (!name || !name.trim()) return;
    fetch('/api/hotwords/tables', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim() })
    }).then(res => {
      if (!res.ok) { alert('创建失败'); return; }
      return res.json();
    }).then(t => {
      currentTableId = t.id;
      loadTables();
      window._selectTable(currentTableId);
    });
  };

  document.getElementById('hw-rename-table-btn').onclick = () => {
    if (!currentTableId) { alert('请先选择词表'); return; }
    const table = allTables.find(t => t.id === currentTableId);
    const name = prompt('请输入新名称：', table ? table.name : '');
    if (!name || !name.trim()) return;
    fetch(`/api/hotwords/tables/${currentTableId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim() })
    }).then(res => {
      if (!res.ok) { alert('重命名失败'); return; }
      loadTables();
    });
  };

  document.getElementById('hw-del-table-btn').onclick = () => {
    if (!currentTableId) { alert('请先选择词表'); return; }
    const table = allTables.find(t => t.id === currentTableId);
    if (!confirm(`确定删除词表"${table ? table.name : ''}"及其所有热词？`)) return;
    fetch(`/api/hotwords/tables/${currentTableId}`, { method: 'DELETE' }).then(res => {
      if (!res.ok) { alert('删除失败'); return; }
      currentTableId = null;
      wordsEl.innerHTML = '<div class="placeholder">请选择一个词表</div>';
      loadTables();
    });
  };

  document.getElementById('hw-import-btn').onclick = () => {
    document.getElementById('hw-import-modal').style.display = 'flex';
  };

  document.getElementById('hw-import-close').onclick = () => {
    document.getElementById('hw-import-modal').style.display = 'none';
  };

  document.getElementById('hw-import-submit').onclick = async () => {
    if (!currentTableId) { alert('请先选择词表'); return; }
    const text = document.getElementById('hw-import-text').value.trim();
    if (!text) { alert('请输入热词'); return; }
    const words = text.split('\n').map(w => w.trim()).filter(Boolean);
    if (words.length === 0) { alert('请输入热词'); return; }
    try {
      const res = await fetch(`/api/hotwords/tables/${currentTableId}/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ words })
      });
      const data = await res.json();
      alert(data.message || `导入完成`);
      document.getElementById('hw-import-text').value = '';
      document.getElementById('hw-import-modal').style.display = 'none';
      window._selectTable(currentTableId);
      syncHotwords();
      loadTables();
    } catch (e) {
      alert('导入失败');
    }
  };

  document.getElementById('hw-import-file').onchange = function() {
    const file = this.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
      const text = e.target.result;
      const words = text.split('\n').map(w => w.trim()).filter(Boolean);
      if (words.length === 0) { alert('文件中无有效热词'); return; }
      try {
        const res = await fetch(`/api/hotwords/tables/${currentTableId}/import`, {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: words.join('\n')
        });
        const data = await res.json();
        alert(data.message || `导入完成`);
        document.getElementById('hw-import-file').value = '';
        document.getElementById('hw-import-modal').style.display = 'none';
        window._selectTable(currentTableId);
        syncHotwords();
        loadTables();
      } catch (e) {
        alert('导入失败');
      }
    };
    reader.readAsText(file);
  };

  function validateWord(word) {
    if (!word || !word.trim()) return '热词不能为空';
    if (new Blob([word]).size > 30) return '热词不能超过 30 字节（约 10 个汉字或 30 个字母）';
    if (!/^[\u4e00-\u9fa5a-zA-Z0-9 ]+$/.test(word)) return '热词仅允许中文汉字、英文字母、数字和空格';
    return null;
  }

  function syncHotwords() {
    if (!currentTableId) return;
    const socket = window._getSocket && window._getSocket();
    if (socket && socket.connected) {
      socket.emit('update_hotwords', { table_id: currentTableId });
    }
  }

  function escHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  loadTables();
  } catch (e) { console.error('hotwords init error:', e); }
});
