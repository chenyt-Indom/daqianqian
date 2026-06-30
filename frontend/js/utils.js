/**
 * 到签签 — 工具函数 v2.0
 */
const Utils = {
  formatTime(iso) { if (!iso) return '—'; const d = new Date(iso); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`; },
  formatShortTime(iso) { if (!iso) return '—'; const d = new Date(iso); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`; },
  formatDate(ds) { if (!ds) return ''; const parts = ds.split('-'); return `${parseInt(parts[1])}月${parseInt(parts[2])}日`; },
  formatMonth(ym) { if (!ym) return ''; const [y,m] = ym.split('-'); return `${y}年${parseInt(m)}月`; },
  today() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; },
  currentMonth() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; },
  weekdayCN() { return '周' + ['日','一','二','三','四','五','六'][new Date().getDay()]; },
  dateDisplay() { const d = new Date(); return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日 ${this.weekdayCN()}`; },
  statusText(s) {
    const m = { normal:'正常', late:'上午迟到', late_pm:'下午迟到', early_am:'上午早退', early_pm:'下午早退', absent:'未签到', overdue_am:'签退超时' };
    return m[s] || s;
  },
  toast(msg, type='success') {
    const t = document.getElementById('toast');
    t.textContent = msg; t.className = `toast ${type} show`;
    clearTimeout(t._timer); t._timer = setTimeout(() => t.classList.remove('show'), 2500);
  },
  escape(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; },
  validatePassword(p) {
    if (p.length < 8) return '密码长度至少8位';
    if (!/[A-Z]/.test(p)) return '密码必须包含大写字母';
    if (!/[a-z]/.test(p)) return '密码必须包含小写字母';
    if (!/[0-9]/.test(p)) return '密码必须包含数字';
    if (!/[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\/\'`~]/.test(p)) return '密码必须包含特殊符号';
    return null;
  },
  validatePhone(p) { return /^1[3-9]\d{9}$/.test(p) ? null : '请输入有效的11位手机号'; },

  // 签到时间提示
  getCheckinHint(timeStr, type) {
    if (!timeStr) return '';
    const [h,m] = timeStr.split(':').map(Number);
    const mins = h * 60 + m;
    if (type === 'am_in') {
      const base = 8 * 60, diff = base - mins;
      if (diff > 0) { if (diff >= 31) return '+3 提前' + diff + '分钟'; if (diff >= 11) return '+2 提前' + diff + '分钟'; return '+1 提前' + diff + '分钟'; }
      const abs = Math.abs(diff);
      if (abs <= 10) return '-1 迟到' + abs + '分钟';
      if (abs <= 30) return '-3 迟到' + abs + '分钟';
      return '-5 迟到' + abs + '分钟';
    }
    if (type === 'pm_in') {
      const base = 14 * 60, diff = mins - base;
      if (diff > 0) { if (diff <= 10) return '-1 迟到' + diff + '分钟'; if (diff <= 30) return '-3 迟到' + diff + '分钟'; return '-5 迟到' + diff + '分钟'; }
      return '';
    }
    if (type === 'am_out') {
      const base = 12 * 60, diff = base - mins, hh = 13;
      if (h >= hh) return '-1 签退超时';
      if (diff > 0) { if (diff <= 30) return '-2 早退' + diff + '分钟'; return '-5 早退' + diff + '分钟'; }
      return '';
    }
    if (type === 'pm_out') {
      const base = 18 * 60, diff = base - mins;
      if (diff > 0) { if (diff <= 30) return '-2 早退' + diff + '分钟'; return '-5 早退' + diff + '分钟'; }
      return '';
    }
    return '';
  },
  hintColor(hint) {
    if (!hint) return '';
    if (hint.startsWith('+')) return 'hint-green';
    if (hint.startsWith('-')) return 'hint-red';
    return '';
  }
};
