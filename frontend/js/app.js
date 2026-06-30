/**
 * 签签到 — 主应用逻辑 + 路由
 */
const App = {
  // ===== 状态 =====
  user: null,
  token: null,
  currentTeam: null,
  currentTab: 'checkin',

  // ===== 初始化 =====
  init() {
    this.token = localStorage.getItem('qianqiandao_token');
    const savedUser = localStorage.getItem('qianqiandao_user');
    if (savedUser) {
      try {
        this.user = JSON.parse(savedUser);
      } catch(e) {
        this.user = null;
      }
    }

    if (this.token && this.user) {
      this.showMain();
    } else {
      this.showAuth();
    }
  },

  // ===== Token 管理 =====
  getToken() {
    return this.token || localStorage.getItem('qianqiandao_token');
  },

  setAuth(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem('qianqiandao_token', token);
    localStorage.setItem('qianqiandao_user', JSON.stringify(user));
  },

  logout() {
    this.token = null;
    this.user = null;
    this.currentTeam = null;
    localStorage.removeItem('qianqiandao_token');
    localStorage.removeItem('qianqiandao_user');
    this.showAuth();
  },

  // ===== 页面切换 =====
  showAuth() {
    document.getElementById('page-auth').classList.add('active');
    document.getElementById('page-main').classList.remove('active');
    document.getElementById('navbar').style.display = 'none';
    document.getElementById('auth-form-login').style.display = 'block';
    document.getElementById('auth-form-register').style.display = 'none';
    document.querySelectorAll('.auth-tab').forEach((t, i) => t.classList.toggle('active', i === 0));
  },

  showMain() {
    document.getElementById('page-auth').classList.remove('active');
    document.getElementById('page-main').classList.add('active');
    document.getElementById('navbar').style.display = 'flex';
    document.getElementById('nav-username').textContent = this.user.display_name;
    this.loadTeams();
  },

  // ===== 认证操作 =====
  async doLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('btn-login');
    
    if (!username || !password) {
      this.showAuthError('请填写用户名和密码');
      return;
    }

    btn.disabled = true;
    btn.textContent = '登录中...';
    this.hideAuthError();

    try {
      const data = await api.login({ username, password });
      this.setAuth(data.access_token, {
        user_id: data.user_id,
        username: data.username,
        display_name: data.display_name,
        role: data.role
      });
      this.showMain();
      Utils.showToast(`欢迎回来，${data.display_name}！`);
    } catch (err) {
      this.showAuthError(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = '登 录';
    }
  },

  async doRegister() {
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const displayName = document.getElementById('reg-display-name').value.trim();
    const btn = document.getElementById('btn-register');
    const role = document.querySelector('.role-option.selected')?.dataset.role || 'employee';

    if (!username || !password || !displayName) {
      this.showAuthError('请填写所有字段');
      return;
    }

    btn.disabled = true;
    btn.textContent = '注册中...';
    this.hideAuthError();

    try {
      const data = await api.register({ username, password, display_name: displayName, role });
      this.setAuth(data.access_token, {
        user_id: data.user_id,
        username: data.username,
        display_name: data.display_name,
        role: data.role
      });
      this.showMain();
      Utils.showToast('注册成功！欢迎加入签签到 🎉');
    } catch (err) {
      this.showAuthError(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = '注 册';
    }
  },

  showAuthError(msg) {
    const el = document.getElementById('auth-error');
    el.textContent = msg;
    el.classList.add('show');
  },

  hideAuthError() {
    document.getElementById('auth-error').classList.remove('show');
  },

  // ===== 团队管理 =====
  async loadTeams() {
    try {
      const teams = await api.getMyTeams();
      const container = document.getElementById('team-list');
      const teamSelectArea = document.getElementById('team-selection');

      if (teams.length === 0) {
        teamSelectArea.style.display = 'block';
        document.getElementById('dashboard-content').style.display = 'none';
        return;
      }

      teamSelectArea.style.display = 'none';
      document.getElementById('dashboard-content').style.display = 'block';

      // 渲染团队列表
      container.innerHTML = teams.map(t => `
        <div class="team-card ${this.currentTeam && this.currentTeam.id === t.id ? 'selected' : ''}" 
             onclick="App.selectTeam(${t.id}, '${t.name}', ${t.is_admin}, '${t.invite_code}')"
             style="${this.currentTeam && this.currentTeam.id === t.id ? 'border-color: var(--blue-light); box-shadow: var(--shadow);' : ''}">
          <h3>${Utils.escapeHtml(t.name)}</h3>
          <div class="meta">${t.member_count} 位成员</div>
          ${t.is_admin ? '<span class="badge">管理员</span>' : ''}
        </div>
      `).join('');

      // 如果没有选中团队，自动选第一个
      if (!this.currentTeam || !teams.find(t => t.id === this.currentTeam.id)) {
        const first = teams[0];
        this.selectTeam(first.id, first.name, first.is_admin, first.invite_code);
      }
    } catch (err) {
      Utils.showToast(err.message, 'error');
    }
  },

  selectTeam(id, name, isAdmin, inviteCode) {
    this.currentTeam = { id, name, is_admin: isAdmin, invite_code: inviteCode };
    document.getElementById('current-team-name').textContent = name;
    this.loadDashboard();
    this.loadTeams(); // 刷新选中状态
  },

  async createTeam() {
    const input = document.getElementById('new-team-name');
    const name = input.value.trim();
    if (!name) {
      Utils.showToast('请输入团队名称', 'error');
      return;
    }
    try {
      const team = await api.createTeam(name);
      Utils.showToast(`团队「${name}」创建成功！邀请码: ${team.invite_code}`);
      input.value = '';
      await this.loadTeams();
    } catch (err) {
      Utils.showToast(err.message, 'error');
    }
  },

  async joinTeam() {
    const input = document.getElementById('join-invite-code');
    const code = input.value.trim();
    if (!code) {
      Utils.showToast('请输入邀请码', 'error');
      return;
    }
    try {
      const result = await api.joinTeam(code);
      Utils.showToast(result.message);
      input.value = '';
      await this.loadTeams();
    } catch (err) {
      Utils.showToast(err.message, 'error');
    }
  },

  // ===== 签到 =====
  async doCheckin() {
    if (!this.currentTeam) {
      Utils.showToast('请先选择一个团队', 'error');
      return;
    }
    const btn = document.getElementById('btn-checkin-in');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 签到中...';

    try {
      const result = await api.checkinIn(this.currentTeam.id);
      Utils.showToast(result.message);
      this.loadDashboard();
    } catch (err) {
      Utils.showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '✅ 签 到';
    }
  },

  async doCheckout() {
    if (!this.currentTeam) return;
    const btn = document.getElementById('btn-checkin-out');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 签退中...';

    try {
      const result = await api.checkinOut(this.currentTeam.id);
      Utils.showToast(result.message);
      this.loadDashboard();
    } catch (err) {
      Utils.showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '🏠 签 退';
    }
  },

  async loadDashboard() {
    if (!this.currentTeam) return;
    try {
      const [status, stats] = await Promise.all([
        api.getTodayStatus(this.currentTeam.id),
        api.getStats(this.currentTeam.id, Utils.currentMonth())
      ]);

      // 更新签到状态卡片
      const statusIcon = document.getElementById('status-icon');
      const statusText = document.getElementById('status-text');
      const statusTime = document.getElementById('status-time');
      const statusBadge = document.getElementById('status-badge');
      const btnIn = document.getElementById('btn-checkin-in');
      const btnOut = document.getElementById('btn-checkin-out');

      if (status.checked_in) {
        statusIcon.textContent = status.checked_out ? '🏠' : '✅';
        statusText.textContent = status.checked_out ? '今日已完成签到' : '已签到，别忘了签退哦';
        statusTime.innerHTML = `签到时间：${Utils.formatDateTime(status.checkin_time)}${status.checked_out ? ` | 签退时间：${Utils.formatDateTime(status.checkout_time)}` : ''}`;
        statusBadge.textContent = Utils.statusText(status.status);
        statusBadge.className = `status-badge ${status.status}`;
        statusBadge.style.display = 'inline-block';
        btnIn.disabled = true;
        btnIn.innerHTML = '✅ 已签到';
        btnOut.disabled = status.checked_out;
        btnOut.innerHTML = status.checked_out ? '🏠 已签退' : '🏠 签 退';
      } else {
        statusIcon.textContent = '📋';
        statusText.textContent = '今天还没有签到';
        statusTime.textContent = Utils.dateDisplay();
        statusBadge.style.display = 'none';
        btnIn.disabled = false;
        btnIn.innerHTML = '✅ 签 到';
        btnOut.disabled = true;
        btnOut.innerHTML = '🏠 签 退';
      }

      // 更新快捷统计
      document.getElementById('stat-total').textContent = stats.total_days;
      document.getElementById('stat-normal').textContent = stats.normal;
      document.getElementById('stat-late').textContent = stats.late;
    } catch (err) {
      console.error('加载签到状态失败:', err);
    }
  },

  // ===== 标签页切换 =====
  switchTab(tab) {
    this.currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    document.getElementById(`tab-${tab}`).style.display = 'block';

    if (tab === 'records') this.loadRecords();
    if (tab === 'team-records') this.loadTeamRecords();
    if (tab === 'members') this.loadMembers();
  },

  // ===== 考勤记录 =====
  recordsMonth: null,
  recordsYear: null,

  async loadRecords() {
    if (!this.currentTeam) return;
    const now = new Date();
    if (!this.recordsYear) this.recordsYear = now.getFullYear();
    if (!this.recordsMonth) this.recordsMonth = now.getMonth() + 1;

    document.getElementById('records-month').textContent = 
      `${this.recordsYear}年${this.recordsMonth}月`;

    try {
      const records = await api.getMyRecords(
        this.currentTeam.id, this.recordsYear, this.recordsMonth
      );
      const tbody = document.getElementById('records-body');

      if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state">
          <div class="icon">📭</div><p>暂无考勤记录</p></div></td></tr>`;
        return;
      }

      tbody.innerHTML = records.map(r => `
        <tr>
          <td>${Utils.formatDate(r.checkin_date)}</td>
          <td>${Utils.formatDateTime(r.checkin_time)}</td>
          <td>${Utils.formatDateTime(r.checkout_time)}</td>
          <td><span class="status-cell ${r.status}">${Utils.statusText(r.status)}</span></td>
        </tr>
      `).join('');
    } catch (err) {
      Utils.showToast(err.message, 'error');
    }
  },

  prevMonth() {
    if (this.recordsMonth === 1) {
      this.recordsMonth = 12;
      this.recordsYear--;
    } else {
      this.recordsMonth--;
    }
    this.loadRecords();
  },

  nextMonth() {
    const now = new Date();
    const maxMonth = (this.recordsYear === now.getFullYear()) ? now.getMonth() + 1 : 12;
    if (this.recordsMonth >= maxMonth && this.recordsYear >= now.getFullYear()) return;
    if (this.recordsMonth === 12) {
      this.recordsMonth = 1;
      this.recordsYear++;
    } else {
      this.recordsMonth++;
    }
    this.loadRecords();
  },

  // ===== 团队考勤记录 =====
  async loadTeamRecords() {
    if (!this.currentTeam) return;
    try {
      const today = Utils.today();
      const records = await api.getTeamRecords(this.currentTeam.id, today);
      const tbody = document.getElementById('team-records-body');

      if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state">
          <div class="icon">📭</div><p>今日暂无签到记录</p></div></td></tr>`;
        return;
      }

      tbody.innerHTML = records.map(r => `
        <tr>
          <td>${Utils.escapeHtml(r.display_name)}</td>
          <td>${Utils.formatDate(r.checkin_date)}</td>
          <td>${Utils.formatDateTime(r.checkin_time)}</td>
          <td>${Utils.formatDateTime(r.checkout_time)}</td>
          <td><span class="status-cell ${r.status}">${Utils.statusText(r.status)}</span></td>
        </tr>
      `).join('');
    } catch (err) {
      Utils.showToast(err.message, 'error');
    }
  },

  // ===== 团队成员 =====
  async loadMembers() {
    if (!this.currentTeam) return;
    try {
      const members = await api.getTeamMembers(this.currentTeam.id);
      const container = document.getElementById('member-list');

      // 邀请码横幅
      document.getElementById('team-invite-code').textContent = this.currentTeam.invite_code;
      document.getElementById('invite-banner').style.display = 
        this.currentTeam.is_admin ? 'flex' : 'none';

      container.innerHTML = members.map(m => `
        <div class="member-item">
          <div class="member-info">
            <div class="member-avatar">${m.display_name[0]}</div>
            <div class="member-details">
              <h4>${Utils.escapeHtml(m.display_name)}</h4>
              <span>@${Utils.escapeHtml(m.username)}</span>
            </div>
          </div>
          <span class="member-role ${m.role}">${m.role === 'admin' ? '管理员' : '员工'}</span>
        </div>
      `).join('');
    } catch (err) {
      Utils.showToast(err.message, 'error');
    }
  },

  copyInviteCode() {
    const code = this.currentTeam?.invite_code;
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        Utils.showToast('邀请码已复制到剪贴板！');
      });
    }
  }
};

// ===== 页面加载完成后初始化 =====
document.addEventListener('DOMContentLoaded', () => {
  App.init();

  // 认证表单事件
  document.getElementById('login-username').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('login-password').focus();
  });
  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') App.doLogin();
  });
  document.getElementById('reg-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') App.doRegister();
  });

  // 角色选择器
  document.querySelectorAll('.role-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.role-option').forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
    });
  });

  // 创建团队回车
  document.getElementById('new-team-name').addEventListener('keydown', e => {
    if (e.key === 'Enter') App.createTeam();
  });

  // 加入团队回车
  document.getElementById('join-invite-code').addEventListener('keydown', e => {
    if (e.key === 'Enter') App.joinTeam();
  });
});
