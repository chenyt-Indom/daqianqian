/**
 * 签签到 — API 请求封装
 */
const API_BASE = 'http://localhost:8000/api';

const api = {
  /**
   * 通用请求方法
   */
  async request(method, path, body = null, auth = true) {
    const headers = { 'Content-Type': 'application/json' };
    
    if (auth) {
      const token = App.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    const options = { method, headers };
    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const res = await fetch(`${API_BASE}${path}`, options);
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || '请求失败');
      }
      
      return data;
    } catch (err) {
      if (err.message === 'Failed to fetch') {
        throw new Error('无法连接到服务器，请确认后端已启动');
      }
      throw err;
    }
  },

  // ===== 认证 =====
  register(data) {
    return this.request('POST', '/auth/register', data, false);
  },

  login(data) {
    return this.request('POST', '/auth/login', data, false);
  },

  // ===== 团队 =====
  createTeam(name) {
    return this.request('POST', '/teams/create', { name });
  },

  joinTeam(inviteCode) {
    return this.request('POST', '/teams/join', { invite_code: inviteCode });
  },

  getMyTeams() {
    return this.request('GET', '/teams/my');
  },

  getTeamMembers(teamId) {
    return this.request('GET', `/teams/${teamId}/members`);
  },

  // ===== 签到 =====
  checkinIn(teamId) {
    const params = teamId ? `?team_id=${teamId}` : '';
    return this.request('POST', `/checkin/in${params}`);
  },

  checkinOut(teamId) {
    const params = teamId ? `?team_id=${teamId}` : '';
    return this.request('POST', `/checkin/out${params}`);
  },

  getTodayStatus(teamId) {
    const params = teamId ? `?team_id=${teamId}` : '';
    return this.request('GET', `/checkin/today${params}`);
  },

  getMyRecords(teamId, year, month) {
    let params = teamId ? `?team_id=${teamId}` : '';
    if (year) params += `${params ? '&' : '?'}year=${year}`;
    if (month) params += `${params ? '&' : '?'}month=${month}`;
    return this.request('GET', `/checkin/records${params}`);
  },

  getTeamRecords(teamId, date) {
    let params = teamId ? `?team_id=${teamId}` : '';
    if (date) params += `${params ? '&' : '?'}date_filter=${date}`;
    return this.request('GET', `/checkin/team-records${params}`);
  },

  getStats(teamId, month) {
    let params = teamId ? `?team_id=${teamId}` : '';
    if (month) params += `${params ? '&' : '?'}month=${month}`;
    return this.request('GET', `/checkin/stats${params}`);
  }
};
