/**
 * 到签签 — API 调用 v2.0
 */
const BASE = '/api';
const api = {
  async _fetch(url, opts = {}) {
    const token = localStorage.getItem('dq_token');
    const h = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (token) h['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE}${url}`, { ...opts, headers: h });
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: '请求失败' })); throw new Error(e.detail || '网络错误'); }
    return res.json();
  },
  _get(url, params = {}) {
    const q = new URLSearchParams(params).toString();
    return this._fetch(`${url}${q ? '?' + q : ''}`);
  },
  _post(url, data) { return this._fetch(url, { method: 'POST', body: JSON.stringify(data) }); },

  // 认证
  sendCode(phone) { return this._post('/auth/send-code', { phone }); },
  register(data) { return this._post('/auth/register', data); },
  login(phone, password) { return this._post('/auth/login', { phone, password }); },

  // 团队
  getTeams() { return this._get('/team/list'); },
  createTeam(name) { return this._post('/team/create', { name }); },
  joinTeam(invite_code) { return this._post('/team/join', { invite_code }); },
  getMembers(team_id) { return this._get('/team/members', { team_id }); },

  // 签到
  amIn(team_id) { return this._post('/checkin/am-in?team_id=' + team_id, {}); },
  amOut(team_id) { return this._post('/checkin/am-out?team_id=' + team_id, {}); },
  pmIn(team_id) { return this._post('/checkin/pm-in?team_id=' + team_id, {}); },
  pmOut(team_id) { return this._post('/checkin/pm-out?team_id=' + team_id, {}); },
  getStatus(team_id) { return this._get('/checkin/status', { team_id }); },
  getTeamToday(team_id) { return this._get('/checkin/today', { team_id }); },
  getMyRecords(team_id, month) { return this._get('/checkin/my-records', { team_id, month }); },

  // 量化分
  getScores(team_id) { return this._get('/checkin/scores', { team_id }); },
  getMyScore(team_id) { return this._get('/checkin/my-score', { team_id }); },
  getScoreRecords(team_id) { return this._get('/checkin/score-records', { team_id }); },
  manualScore(team_id, user_id, score_change, reason) { return this._post('/checkin/manual-score', { team_id, user_id, score_change, reason }); },

  // 信箱
  getMailbox() { return this._get('/mailbox/list'); },
  getUnreadCount() { return this._get('/mailbox/unread'); },
  readMsg(msg_id) { return this._post('/mailbox/read', { msg_id }); },
  readAllMsg() { return this._post('/mailbox/read-all', {}); },
  deleteMsg(msg_id) { return this._post('/mailbox/delete', { msg_id }); },
  sendReport(team_id, title, content) { return this._post('/mailbox/report', { team_id, title, content }); },

  // 调试
  debugAddMember(team_id, phone, display_name) { return this._post('/debug/add-member', { team_id, phone, display_name }); },
  debugSetTime(offset_seconds) { return this._post('/debug/set-time', { offset_seconds }); },
  debugGetTime() { return this._get('/debug/time'); },
  debugResetTime() { return this._post('/debug/reset-time', {}); },
  debugResetCheckin(team_id) { return this._post('/debug/reset-checkin', { team_id }); },
};
