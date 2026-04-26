// 完整日志页面逻辑
(function() {
    let allLogs = [];
    let filteredLogs = [];

    // 初始化
    document.addEventListener('DOMContentLoaded', () => {
        // 绑定事件
        document.getElementById('search-input').addEventListener('input', filterLogs);
        document.getElementById('channel-filter').addEventListener('change', filterLogs);
        document.getElementById('level-filter').addEventListener('change', filterLogs);

        // 先渲染一次空状态
        renderLogs();
        updateStats();

        // 立即尝试获取日志
        refreshLogs();

        // 定时刷新（从 opener 获取最新日志）
        setInterval(refreshLogs, 1000);

        // 监听 postMessage（用于接收初始日志和新日志）
        window.addEventListener('message', (e) => {
            if (!e.data) return;

            if (e.data.type === 'initLogs' && Array.isArray(e.data.logs)) {
                allLogs = e.data.logs;
                filterLogs();
            } else if (e.data.type === 'newLog' && e.data.log) {
                allLogs.push(e.data.log);
                filterLogs();
            } else if (e.data.type === 'clearLogs') {
                allLogs = [];
                filteredLogs = [];
                renderLogs();
                updateStats();
            }
        });
    });

    function refreshLogs() {
        if (window.opener && window.opener.sessionLogs) {
            const newLogs = window.opener.sessionLogs;
            if (newLogs.length !== allLogs.length) {
                allLogs = [...newLogs]; // 复制数组
                filterLogs();
            }
        }
    }

    function filterLogs() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const channelFilter = document.getElementById('channel-filter').value;
        const levelFilter = document.getElementById('level-filter').value;

        filteredLogs = allLogs.filter(log => {
            // 搜索过滤
            if (searchTerm) {
                const text = (log.message + log.channel + log.level).toLowerCase();
                if (!text.includes(searchTerm)) return false;
            }

            // 通道过滤
            if (channelFilter !== 'all' && log.channel !== channelFilter) {
                return false;
            }

            // 级别过滤
            if (levelFilter !== 'all' && log.level !== levelFilter) {
                return false;
            }

            return true;
        });

        renderLogs();
        updateStats();
    }

    function renderLogs() {
        const container = document.getElementById('log-container');
        const logsToRender = filteredLogs.length > 0 ? filteredLogs : allLogs;

        if (logsToRender.length === 0) {
            container.innerHTML = '<div class="no-logs">暂无日志 / No logs available<br><small>等待日志同步...</small></div>';
            return;
        }

        const searchTerm = document.getElementById('search-input').value;

        const html = logsToRender.map(log => {
            let message = escapeHtml(log.message);

            // 高亮搜索词
            if (searchTerm) {
                const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi');
                message = message.replace(regex, '<span class="highlight">$1</span>');
            }

            return `<div class="log-item">
                <span class="log-time">${log.timestamp}</span>
                <span class="log-level log-level-${log.level.toLowerCase()}">${log.level}</span>
                <span class="log-channel">[${log.channel}]</span>
                <span class="log-message">${message}</span>
            </div>`;
        }).join('');

        container.innerHTML = html;

        // 自动滚动到底部（如果接近底部）
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        if (isNearBottom) {
            container.scrollTop = container.scrollHeight;
        }
    }

    function updateStats() {
        const statsEl = document.getElementById('stats');
        const total = allLogs.length;
        const showing = filteredLogs.length > 0 ? filteredLogs.length : total;

        if (filteredLogs.length > 0) {
            statsEl.textContent = `显示 ${showing} / 共 ${total} 条日志`;
        } else {
            statsEl.textContent = `共 ${total} 条日志`;
        }
    }

    function exportLogs() {
        const logsToExport = filteredLogs.length > 0 ? filteredLogs : allLogs;

        if (logsToExport.length === 0) {
            alert('没有日志可导出 / No logs to export');
            return;
        }

        // 生成文本内容
        const content = logsToExport.map(log =>
            `[${log.timestamp}] [${log.level}] [${log.channel}] ${log.message}`
        ).join('\n');

        // 创建下载
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logs_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function clearAllLogs() {
        if (!confirm('确定要清空所有日志吗？\nAre you sure you want to clear all logs?')) {
            return;
        }

        allLogs = [];
        filteredLogs = [];

        // 同时清空 opener 的日志
        if (window.opener && window.opener.sessionLogs) {
            window.opener.sessionLogs = [];
            if (window.opener.clearLogs) {
                window.opener.clearLogs();
            }
        }

        renderLogs();
        updateStats();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // 暴露到全局供 HTML 调用
    window.exportLogs = exportLogs;
    window.clearAllLogs = clearAllLogs;
})();
