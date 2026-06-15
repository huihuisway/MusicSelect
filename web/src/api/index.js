import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

// ── 歌曲 ──────────────────────────────────────
export const getCurrentSongs = (week) =>
  api.get('/song/list', { params: week ? { week } : {} }).then((r) => r.data.data);

export const getDaySongs = (date) =>
  api.get('/song/list', { params: { date } }).then((r) => r.data.data);

export const getCurrentCycle = () =>
  api.get('/song/current-cycle').then((r) => r.data.data);

export const getCalendar = (week) =>
  api.get('/song/calendar', { params: week ? { week } : {} }).then((r) => r.data.data);

export const getHistoryWeeks = () =>
  api.get('/song/history').then((r) => r.data.data);

export const getHistoryWeek = (week) =>
  api.get('/song/history', { params: { week } }).then((r) => r.data.data);

export const getSongStats = () =>
  api.get('/song/stats').then((r) => r.data.data);

// ── 评论 ──────────────────────────────────────
export const getComments = (songId) =>
  api.get('/comment', { params: { songId } }).then((r) => r.data.data);

export default api;
