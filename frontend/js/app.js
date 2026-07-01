/**
 * 到签签 — 主应用逻辑 v2.0
 */
const App = {
  user: null, token: null, currentTeam: null, currentTab: 'checkin',
  recordsMonth: Utils.currentMonth(),
  _regRole: 'employee', _codeTimer: null,

  init() {
    this.token = localStorage.getItem('dq_token');
    const u = localStorage.getItem('dq_user');
    if (u) try { this.user = JSON.parse(u); } catch(e) { this.user = null; }
    if (this.token && this.user) this.showMain();
    else this.showAuth();
  },

  // ===== 认证 =====
  showAuth() {
    document.getElementById('page-auth').classList.add('active');
    document.getElementById('page-main').classList.remove('active');
    document.getElementById('navbar').style.display = 'none';
  },
  switchAuthTab(tab) {
    document.getElementById('auth-form-login').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('auth-form-register').style.display = tab === 'register' ? 'block' : 'none';
    document.querySelectorAll('.auth-tab').forEach((t, i) => t.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register')));
    this._hideErrors();
  },
  selectRole(el, role) { this._regRole = role; document.querySelectorAll('.role-opt').forEach(o => o.classList.remove('selected')); el.classList.add('selected'); },
  _hideErrors() { ['auth-error','auth-error-reg'].forEach(id => { const e = document.getElementById(id); if (e) e.classList.remove('show'); }); },
  _showError(id, msg) { const e = document.getElementById(id); if (e) { e.textContent = msg; e.classList.add('show'); } },

  async sendCode() {
    const phone = document.getElementById('reg-phone').value.trim();
    const err = Utils.validatePhone(phone);
    if (err) { this._showError('auth-error-reg', err); return; }
    const btn = document.getElementById('btn-send-code');
    try {
      btn.disabled = true;
      const r = await api.sendCode(phone);
      // 测试模式：直接在页面上显示验证码
      const hint = document.getElementById('code-hint');
      if (r.debug_code) {
        if (hint) {
          hint.innerHTML = '验证码：<b style="color:var(--red);font-size:18px;letter-spacing:3px">' + r.debug_code + '</b>';
          hint.style.display = 'block';
        }
        document.getElementById('reg-code').value = r.debug_code;
        Utils.toast('验证码：' + r.debug_code);
      }
      let sec = 60;
      btn.textContent = sec + 's';
      this._codeTimer = setInterval(() => { sec--; btn.textContent = sec + 's'; if (sec <= 0) { clearInterval(this._codeTimer); btn.textContent = '获取验证码'; btn.disabled = false; }}, 1000);
    } catch(e) { Utils.toast(e.message, 'error'); btn.disabled = false; }
  },

  async doLogin() {
    const phone = document.getElementById('login-phone').value.trim();
    const pwd = document.getElementById('login-password').value;
    if (!phone || !pwd) { this._showError('auth-error', '请输入手机号和密码'); return; }
    try {
      const r = await api.login(phone, pwd);
      this._onAuth(r);
    } catch(e) { this._showError('auth-error', e.message); }
  },

  async doRegister() {
    const phone = document.getElementById('reg-phone').value.trim();
    const code = document.getElementById('reg-code').value.trim();
    const name = document.getElementById('reg-name').value.trim();
    const pwd = document.getElementById('reg-password').value;
    if (!phone || !code || !name || !pwd) { this._showError('auth-error-reg', '请填写所有字段'); return; }
    const pe = Utils.validatePassword(pwd);
    if (pe) { this._showError('auth-error-reg', pe); return; }
    try {
      const r = await api.register({ phone, code, password: pwd, display_name: name, role: this._regRole });
      this._onAuth(r);
    } catch(e) { this._showError('auth-error-reg', e.message); }
  },

  _onAuth(r) {
    this.token = r.access_token; this.user = r;
    localStorage.setItem('dq_token', r.access_token); localStorage.setItem('dq_user', JSON.stringify(r));
    this.showMain();
  },

  logout() {
    if (this._clockTimer) clearInterval(this._clockTimer);
    localStorage.removeItem('dq_token'); localStorage.removeItem('dq_user');
    this.token = null; this.user = null; this.currentTeam = null;
    this.showAuth();
  },

  // ===== 主页面 =====
  showMain() {
    document.getElementById('page-auth').classList.remove('active');
    document.getElementById('page-main').classList.add('active');
    document.getElementById('navbar').style.display = 'flex';
    document.getElementById('nav-username').textContent = this.user.display_name;
    this.loadTeams();
    this.updateUnreadCount();
    setInterval(() => this.updateUnreadCount(), 30000);
  },

  async loadTeams() {
    try {
      const teams = await api.getTeams();
      document.getElementById('team-selection').style.display = teams.length ? 'block' : 'block';
      document.getElementById('dashboard').style.display = 'none';
      const container = document.getElementById('team-list');
      if (teams.length === 0) {
        container.innerHTML = '<div class="empty">暂未加入任何团队，创建或加入一个吧</div>';
        return;
      }
      container.innerHTML = teams.map(t => `<div class="team-card" onclick="App.selectTeam(${t.id},'${Utils.escape(t.name)}',${t.is_admin},'${t.invite_code}','${t.admin_invite_code||''}')"><h3>${Utils.escape(t.name)}</h3><div class="card-meta">${t.member_count} 位成员 · ${t.is_admin ? '管理员' : '员工'}</div></div>`).join('');
    } catch(e) { Utils.toast(e.message, 'error'); }
  },

  selectTeam(id, name, isAdmin, inviteCode, adminInvite) {
    this.currentTeam = { id, name, is_admin: isAdmin, invite_code: inviteCode, admin_invite_code: adminInvite };
    document.getElementById('team-selection').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    document.getElementById('current-team-name').textContent = name;
    document.getElementById('dash-name').textContent = this.user.display_name;
    document.getElementById('date-display').textContent = Utils.dateDisplay();
    this._startClock();
    this.switchTab('checkin');
    // 管理员显示调试面板
    document.getElementById('debug-panel').style.display = isAdmin ? 'block' : 'none';
  },

  _startClock() {
    this._clockOffset = 0;
    this._fetchClockOffset();
    this._updateClock();
    this._clockTimer = setInterval(() => this._updateClock(), 1000);
  },

  async _fetchClockOffset() {
    try {
      const r = await api.debugGetTime();
      this._clockOffset = r.offset || 0;
    } catch(e) {}
  },

  _updateClock() {
    const el = document.getElementById('live-clock');
    if (el) {
      const now = new Date(Date.now() + (this._clockOffset || 0) * 1000);
      el.textContent = now.toLocaleTimeString('zh-CN', { hour12: false });
    }
  },

  switchTab(tab) {
    this.currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.textContent.includes(tab === 'checkin' ? '签到' : tab === 'records' ? '我的考勤' : tab === 'team-records' ? '团队考勤' : tab === 'scores' ? '量化分' : '成员')));
    ['checkin','records','team-records','scores','members'].forEach(t => { document.getElementById('tab-' + t).style.display = t === tab ? 'block' : 'none'; });
    if (tab === 'checkin') this.loadDashboard();
    else if (tab === 'records') this.loadRecords();
    else if (tab === 'team-records') this.loadTeamRecords();
    else if (tab === 'scores') this.loadScores();
    else if (tab === 'members') this.loadMembers();
  },

  // ===== 签到 =====
  async loadDashboard() {
    if (!this.currentTeam) return;
    try {
      const st = await api.getStatus(this.currentTeam.id);
      document.getElementById('am-time').textContent = st.record?.am_in ? Utils.formatShortTime(st.record.am_in) : '—';
      document.getElementById('pm-time').textContent = st.record?.pm_in ? Utils.formatShortTime(st.record.pm_in) : '—';
      // 状态更新
      const amStatus = document.getElementById('am-status');
      amStatus.textContent = st.record?.am_in ? (st.record.am_status === 'normal' ? '已签到' : Utils.statusText(st.record.am_status || 'absent')) : '未签到';
      amStatus.className = 'status-badge ' + (st.record?.am_status || 'absent');
      const pmStatus = document.getElementById('pm-status');
      pmStatus.textContent = st.record?.pm_in ? (st.record.pm_status === 'normal' ? '已签到' : Utils.statusText(st.record.pm_status || 'absent')) : '未签到';
      pmStatus.className = 'status-badge ' + (st.record?.pm_status || 'absent');
      // 按钮状态
      document.getElementById('btn-am-in').disabled = !st.can_am_in;
      document.getElementById('btn-am-out').disabled = !st.can_am_out;
      document.getElementById('btn-pm-in').disabled = !st.can_pm_in;
      document.getElementById('btn-pm-out').disabled = !st.can_pm_out;
      if (st.is_closed) {
        ['btn-am-in','btn-am-out','btn-pm-in','btn-pm-out'].forEach(id => document.getElementById(id).disabled = true);
      }
      // 提示
      const amHint = Utils.getCheckinHint(st.record?.am_in ? Utils.formatShortTime(st.record.am_in).substring(0,5) : '', 'am_in');
      document.getElementById('am-hint').innerHTML = amHint ? `<span class="${Utils.hintColor(amHint)}">${amHint}</span>` : '';
      const pmHint = Utils.getCheckinHint(st.record?.pm_in ? Utils.formatShortTime(st.record.pm_in).substring(0,5) : '', 'pm_in');
      document.getElementById('pm-hint').innerHTML = pmHint ? `<span class="${Utils.hintColor(pmHint)}">${pmHint}</span>` : '';
      // 统计
      this._loadStats();
    } catch(e) { Utils.toast(e.message, 'error'); }
  },

  async _loadStats() {
    try {
      const records = await api.getMyRecords(this.currentTeam.id, Utils.currentMonth());
      let total = 0, normal = 0, late = 0;
      records.forEach(r => { total++; if (r.am && (r.am.status === 'normal' || !r.am.status) && r.pm && (r.pm.status === 'normal' || !r.pm.status)) normal++; else late++; });
      document.getElementById('stat-days').textContent = total;
      document.getElementById('stat-normal').textContent = normal;
      document.getElementById('stat-late').textContent = late;
    } catch(e) {}
  },

  async doAmIn() { await this._doCheckin('amIn', 'btn-am-in', '上午签到成功'); },
  async doAmOut() { await this._doCheckin('amOut', 'btn-am-out', '上午签退成功'); },
  async doPmIn() { await this._doCheckin('pmIn', 'btn-pm-in', '下午签到成功'); },
  async doPmOut() { await this._doCheckin('pmOut', 'btn-pm-out', '下午签退成功'); },

  async _doCheckin(fn, btnId, msg) {
    try {
      const r = await api[fn](this.currentTeam.id);
      let fullMsg = msg;
      if (r.score_change !== undefined && r.score_change !== 0) {
        fullMsg += `（量化分${r.score_change > 0 ? '+' + r.score_change : r.score_change}）`;
      }
      Utils.toast(fullMsg);
      this.loadDashboard();
    } catch(e) { Utils.toast(e.message, 'error'); }
  },

  // ===== 我的考勤 =====
  async loadRecords() {
    try {
      const records = await api.getMyRecords(this.currentTeam.id, this.recordsMonth);
      document.getElementById('rec-month').textContent = Utils.formatMonth(this.recordsMonth);
      const tbody = document.getElementById('rec-body');
      if (!records.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty">📭 暂无记录</div></td></tr>'; return; }
      tbody.innerHTML = records.map(r => `<tr>
        <td>${Utils.formatDate(r.checkin_date)}</td>
        <td>${Utils.formatShortTime(r.am?.time_in)}</td>
        <td>${Utils.formatShortTime(r.am?.time_out)}</td>
        <td>${Utils.formatShortTime(r.pm?.time_in)}</td>
        <td>${Utils.formatShortTime(r.pm?.time_out)}</td>
        <td><span class="status-cell ${r.am?.status||''}">${Utils.statusText(r.am?.status||'absent')} / ${Utils.statusText(r.pm?.status||'absent')}</span></td>
      </tr>`).join('');
    } catch(e) { Utils.toast(e.message, 'error'); }
  },
  prevMonth() { const [y,m] = this.recordsMonth.split('-').map(Number); this.recordsMonth = m === 1 ? `${y-1}-12` : `${y}-${String(m-1).padStart(2,'0')}`; this.loadRecords(); },
  nextMonth() { const [y,m] = this.recordsMonth.split('-').map(Number); this.recordsMonth = m === 12 ? `${y+1}-01` : `${y}-${String(m+1).padStart(2,'0')}`; this.loadRecords(); },

  // ===== 团队考勤 =====
  async loadTeamRecords() {
    try {
      const records = await api.getTeamToday(this.currentTeam.id);
      const tbody = document.getElementById('team-rec-body');
      if (!records.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty">📭 今日暂无记录</div></td></tr>'; return; }
      tbody.innerHTML = records.map(r => `<tr>
        <td>${Utils.escape(r.display_name)}</td>
        <td>${Utils.formatShortTime(r.am?.time_in)}</td>
        <td>${Utils.formatShortTime(r.am?.time_out)}</td>
        <td>${Utils.formatShortTime(r.pm?.time_in)}</td>
        <td>${Utils.formatShortTime(r.pm?.time_out)}</td>
        <td><span class="status-cell ${r.am?.status||''}">${Utils.statusText(r.am?.status||'absent')} / ${Utils.statusText(r.pm?.status||'absent')}</span></td>
      </tr>`).join('');
    } catch(e) { Utils.toast(e.message, 'error'); }
  },

  // ===== 量化分 =====
  _scoreExpanded: {},
  async loadScores() {
    try {
      const scores = await api.getScores(this.currentTeam.id);
      const container = document.getElementById('score-list');
      container.innerHTML = scores.map(s => {
        const color = s.score >= 50 ? 'score-green' : s.score >= 30 ? 'score-orange' : 'score-red';
        return `<div class="score-item" onclick="App.toggleScoreDetail(${s.user_id})">
          <span class="score-name">${Utils.escape(s.display_name)}</span>
          <span class="score-value ${color}">${s.score}</span>
        </div>
        <div class="score-detail" id="score-detail-${s.user_id}">加载中...</div>`;
      }).join('');
      // 加载每个成员的详细记录
      const records = await api.getScoreRecords(this.currentTeam.id);
      const grouped = {};
      records.forEach(r => { if (!grouped[r.user_id]) grouped[r.user_id] = []; grouped[r.user_id].push(r); });
      scores.forEach(s => {
        const detail = document.getElementById('score-detail-' + s.user_id);
        const userRecords = grouped[s.user_id] || [];
        detail.innerHTML = userRecords.length ? userRecords.slice(0, 10).map(r => {
          const cls = r.score_change >= 0 ? 'score-plus' : 'score-minus';
          return `<div class="score-record-row"><span>${r.reason || ''}</span><span class="${cls}">${r.score_change >= 0 ? '+' : ''}${r.score_change} → ${r.score_after}</span></div>`;
        }).join('') : '<div style="color:var(--gray-400);text-align:center;padding:8px">暂无记录</div>';
      });

      // 管理员量化分改动
      if (this.currentTeam.is_admin) {
        container.innerHTML += `<div style="margin-top:14px;background:#fff8e1;border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow)">
          <h4 style="margin:0;padding:12px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center" onclick="this.nextElementSibling.classList.toggle('show')">🔧 量化分改动 <span style="font-size:12px;color:var(--gray-400);font-weight:400">▼</span></h4>
          <div class="score-detail" style="padding:0 14px 14px">
            <div style="display:flex;gap:6px;flex-wrap:wrap;padding-top:8px">
            <select id="manual-user" style="padding:6px 8px;border-radius:6px;border:1px solid var(--gray-200)">${scores.map(s => `<option value="${s.user_id}">${Utils.escape(s.display_name)}</option>`).join('')}</select>
            ${[-5,-4,-3,-2,-1,1,2,3,4,5].map(v => `<button class="btn-sm" onclick="App.manualScore(${v})">${v>0?'+':''}${v}</button>`).join('')}
            <input type="number" id="manual-custom" placeholder="定义量化" style="width:80px;padding:6px 8px;border-radius:6px;border:1px solid var(--gray-200);font-size:13px">
            <button class="btn-sm" onclick="App.manualScoreCustom()">应用</button>
            </div>
          </div>
        </div>`;
      }
    } catch(e) { Utils.toast(e.message, 'error'); }
  },

  toggleScoreDetail(uid) {
    const el = document.getElementById('score-detail-' + uid);
    if (!el) return;
    el.classList.toggle('show');
  },

  async manualScore(val) {
    const uid = parseInt(document.getElementById('manual-user').value);
    const reason = prompt('改动原因：', '');
    if (reason === null) return;
    if (!reason.trim()) { Utils.toast('请填写改动原因', 'error'); return; }
    try { await api.manualScore(this.currentTeam.id, uid, val, reason.trim()); Utils.toast('操作成功'); this.loadScores(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  },
  async manualScoreCustom() {
    const uid = parseInt(document.getElementById('manual-user').value);
    const val = parseInt(document.getElementById('manual-custom').value);
    if (isNaN(val)) { Utils.toast('请输入有效数字', 'error'); return; }
    const reason = prompt('改动原因：', '');
    if (reason === null) return;
    if (!reason.trim()) { Utils.toast('请填写改动原因', 'error'); return; }
    try { await api.manualScore(this.currentTeam.id, uid, val, reason.trim()); Utils.toast('操作成功'); this.loadScores(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  },

  // ===== 成员 =====
  async loadMembers() {
    try {
      const members = await api.getMembers(this.currentTeam.id);
      const container = document.getElementById('member-list');
      container.innerHTML = members.map(m => `<div class="member-item">
        <div class="member-info"><div class="member-avatar">${m.display_name[0]}</div><div class="member-details"><h4>${Utils.escape(m.display_name)}</h4><span>@${Utils.escape(m.username)}</span></div></div>
        <span class="member-role-tag ${m.role}">${m.role==='admin'?'管理员':'员工'}</span>
      </div>`).join('');
      // 邀请码
      document.getElementById('team-invite-code').textContent = this.currentTeam.invite_code;
      document.getElementById('invite-banner').style.display = this.currentTeam.is_admin ? 'flex' : 'none';
      if (this.currentTeam.is_admin) this._genQR();
    } catch(e) { Utils.toast(e.message, 'error'); }
  },

  copyInviteCode() {
    const code = this.currentTeam?.invite_code;
    if (code) { navigator.clipboard.writeText(code).then(() => Utils.toast('已复制邀请码')).catch(() => Utils.toast('复制失败', 'error')); }
  },

  _genQR() {
    const container = document.getElementById('qrcode-container');
    container.innerHTML = '';
    if (typeof QRCode !== 'undefined') {
      new QRCode(container, { text: this.currentTeam.invite_code, width: 80, height: 80 });
    }
  },

  showQR() {
    const modal = document.getElementById('qr-modal');
    const container = document.getElementById('qr-big');
    container.innerHTML = '';
    if (typeof QRCode !== 'undefined') {
      new QRCode(container, { text: this.currentTeam.invite_code, width: 200, height: 200 });
    }
    modal.classList.add('active');
  },

  // ===== 团队操作 =====
  async createTeam() {
    const name = document.getElementById('new-team-name').value.trim();
    if (!name) { Utils.toast('请输入团队名称', 'error'); return; }
    try { await api.createTeam(name); Utils.toast('团队创建成功'); this.loadTeams(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  },
  async joinTeam() {
    const code = document.getElementById('join-code').value.trim();
    if (!code) { Utils.toast('请输入邀请码', 'error'); return; }
    try { await api.joinTeam(code); Utils.toast('成功加入团队'); this.loadTeams(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  },

  // ===== 信箱 =====
  async openMailbox() { document.getElementById('mailbox-modal').classList.add('active'); await this._loadMailbox(); },
  closeMailbox() { document.getElementById('mailbox-modal').classList.remove('active'); },
  async _loadMailbox() {
    try {
      const msgs = await api.getMailbox();
      const list = document.getElementById('mailbox-list');
      if (!msgs.length) { list.innerHTML = '<div class="empty">📭 暂无消息</div>'; return; }
      list.innerHTML = msgs.map(m => `<div class="mailbox-item ${m.is_read==='False'?'unread':''}">
        <div class="mailbox-item-header"><span class="sender">${Utils.escape(m.sender_name)}</span><span class="time">${Utils.formatTime(m.created_at)}</span></div>
        <div class="title-text">${Utils.escape(m.title)}</div>
        <div class="content-preview">${Utils.escape(m.content.substring(0,60))}${m.content.length>60?'...':''}</div>
        <div class="msg-actions">
          <button class="btn-sm" onclick="event.stopPropagation();App._doReadMsg(${m.id})">已读</button>
          <button class="btn-sm" onclick="event.stopPropagation();App._doDeleteMsg(${m.id})">删除</button>
        </div>
      </div>`).join('');
      this.updateUnreadCount();
    } catch(e) { Utils.toast(e.message, 'error'); }
  },
  async _doReadMsg(id) { try { await api.readMsg(id); this._loadMailbox(); } catch(e) { Utils.toast(e.message, 'error'); } },
  async _doDeleteMsg(id) { try { await api.deleteMsg(id); this._loadMailbox(); } catch(e) { Utils.toast(e.message, 'error'); } },
  async updateUnreadCount() {
    try {
      const r = await api.getUnreadCount();
      const badge = document.getElementById('mailbox-badge');
      badge.textContent = r.unread || ''; badge.style.display = r.unread > 0 ? 'flex' : 'none';
    } catch(e) {}
  },
  async readAllMsg() { try { await api.readAllMsg(); this._loadMailbox(); } catch(e) { Utils.toast(e.message, 'error'); } },

  // ===== 写消息 =====
  composeMsg() { document.getElementById('compose-modal').classList.add('active'); },
  closeCompose() { document.getElementById('compose-modal').classList.remove('active'); },
  async sendMsg() {
    const title = document.getElementById('compose-title').value.trim();
    const content = document.getElementById('compose-content').value.trim();
    if (!title || !content) { Utils.toast('请填写标题和内容', 'error'); return; }
    try {
      await api.sendReport(this.currentTeam.id, title, content);
      Utils.toast('消息已发送'); this.closeCompose();
    } catch(e) { Utils.toast(e.message, 'error'); }
  },

  // ===== 调试 =====
  async debugApplyTime() {
    const h = parseInt(document.getElementById('debug-hour').value);
    const m = parseInt(document.getElementById('debug-min').value);
    const now = new Date();
    const target = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0);
    const offset = (target.getTime() - now.getTime()) / 1000;
    try { await api.debugSetTime(offset); Utils.toast('时间已设置为 ' + h + ':' + String(m).padStart(2,'0')); this._fetchClockOffset(); this.loadDashboard(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  },
  async debugResetTime() { try { await api.debugResetTime(); this._fetchClockOffset(); Utils.toast('时间已重置'); this.loadDashboard(); } catch(e) { Utils.toast(e.message, 'error'); } },
  async debugPreset(type) {
    const presets = { am_early: [7,45], am_late: [8,15], pm_early: [13,45], pm_late: [14,20], am_out: [11,0], pm_out: [17,0] };
    const [h,m] = presets[type] || [8,0];
    const now = new Date(); const target = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0);
    try { await api.debugSetTime((target.getTime() - now.getTime()) / 1000); this._fetchClockOffset(); Utils.toast('时间预设: ' + type); this.loadDashboard(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  },
  async debugAddMember() {
    const phone = document.getElementById('debug-mem-phone').value.trim();
    const name = document.getElementById('debug-mem-name').value.trim();
    if (!phone || !name) { Utils.toast('请填写手机号和姓名', 'error'); return; }
    try { await api.debugAddMember(this.currentTeam.id, phone, name); Utils.toast('已添加成员 ' + name); this.loadMembers(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  },
  async debugResetCheckin() {
    try { await api.debugResetCheckin(this.currentTeam.id); Utils.toast('已清空今日签到'); this.loadDashboard(); }
    catch(e) { Utils.toast(e.message, 'error'); }
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
