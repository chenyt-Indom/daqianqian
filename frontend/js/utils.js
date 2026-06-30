/**
 * 签签到 — 工具函数
 */
const Utils = {
  /**
   * 格式化日期时间
   */
  formatDateTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    const h = d.getHours().toString().padStart(2, '0');
    const m = d.getMinutes().toString().padStart(2, '0');
    const s = d.getSeconds().toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
  },

  /**
   * 格式化日期
   */
  formatDate(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    return `${parts[1]}月${parts[2]}日`;
  },

  /**
   * 获取当前日期字符串 YYYY-MM-DD
   */
  today() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  },

  /**
   * 获取当前月份 YYYY-MM
   */
  currentMonth() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
  },

  /**
   * 中文星期
   */
  weekdayCN() {
    const days = ['日', '一', '二', '三', '四', '五', '六'];
    return '周' + days[new Date().getDay()];
  },

  /**
   * 中文日期显示
   */
  dateDisplay() {
    const d = new Date();
    return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日 ${this.weekdayCN()}`;
  },

  /**
   * 状态中文映射
   */
  statusText(status) {
    const map = {
      'normal': '正常',
      'late': '迟到',
      'early': '早退',
      'absent': '未签到'
    };
    return map[status] || status;
  },

  /**
   * Toast 提示
   */
  showToast(message, type = 'success') {
    let toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      toast.className = 'toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  },

  /**
   * 转义 HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
};
