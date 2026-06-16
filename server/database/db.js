import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { mkdirSync, existsSync } from 'fs';
import { Low } from 'lowdb';
import { JSONFile } from 'lowdb/node';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DB_PATH = join(__dirname, '..', '..', 'data', 'db.json');

// 确保 data 目录存在
const dataDir = join(__dirname, '..', '..', 'data');
if (!existsSync(dataDir)) mkdirSync(dataDir, { recursive: true });

const defaultData = {
  songs: [],
  comments: [],
  songArchives: [],
  downloadRecords: [],
  closedDates: [], // [{ date: 'YYYY-MM-DD', weekStart: 'YYYY-MM-DD', reason: '' }]
};

const adapter = new JSONFile(DB_PATH);
const db = new Low(adapter, defaultData);

await db.read();
db.data = db.data || { ...defaultData };
db.data.songs = db.data.songs || [];
db.data.comments = db.data.comments || [];
db.data.songArchives = db.data.songArchives || [];
db.data.downloadRecords = db.data.downloadRecords || [];
db.data.closedDates = db.data.closedDates || [];
await db.write();

// --------------- 辅助 ---------------
const save = () => db.write();

const songIds = (arr) => new Set(arr.map((s) => s.songId));

// --------------- Songs ---------------
export const findSongs = (filter = {}) =>
  db.data.songs.filter((s) => Object.entries(filter).every(([k, v]) => s[k] === v));

export const findOneSong = (filter) =>
  db.data.songs.find((s) => Object.entries(filter).every(([k, v]) => s[k] === v)) || null;

export const countSongs = (filter = {}) => findSongs(filter).length;

export const addSong = (song) => {
  db.data.songs.push(song);
  return save();
};

export const updateSongs = (filter, updates) => {
  let n = 0;
  db.data.songs = db.data.songs.map((s) => {
    if (Object.entries(filter).every(([k, v]) => s[k] === v)) { n++; return { ...s, ...updates }; }
    return s;
  });
  if (n) save();
  return n;
};

export const removeSongs = (filter) => {
  const before = db.data.songs.length;
  db.data.songs = db.data.songs.filter(
    (s) => !Object.entries(filter).every(([k, v]) => s[k] === v),
  );
  if (db.data.songs.length !== before) save();
  return before - db.data.songs.length;
};

// --------------- Archives ---------------
export const archiveSongs = (weekStart) => {
  const songs = db.data.songs.filter((s) => s.weekStart === weekStart);
  if (!songs.length) return 0;
  // 归档歌曲
  db.data.songArchives.push(...songs.map((s) => ({ ...s, archivedAt: new Date().toISOString() })));
  db.data.songs = db.data.songs.filter((s) => s.weekStart !== weekStart);
  // 清理已归档歌曲的评论
  const archivedIds = new Set(songs.map((s) => s.songId));
  db.data.comments = db.data.comments.filter((c) => !archivedIds.has(c.songId));
  save();
  return songs.length;
};

export const findArchives = (filter = {}) =>
  db.data.songArchives.filter((s) => Object.entries(filter).every(([k, v]) => s[k] === v));

export const getArchiveWeeks = () => [...new Set(db.data.songArchives.map((s) => s.weekStart))].sort();

// --------------- Comments ---------------
export const findComments = (filter = {}) =>
  db.data.comments.filter((c) => Object.entries(filter).every(([k, v]) => c[k] === v));

export const addComment = (comment) => {
  db.data.comments.push(comment);
  return save();
};

export const removeComments = (filter) => {
  const before = db.data.comments.length;
  db.data.comments = db.data.comments.filter(
    (c) => !Object.entries(filter).every(([k, v]) => c[k] === v),
  );
  if (db.data.comments.length !== before) save();
  return before - db.data.comments.length;
};

// --------------- Download Records ---------------
export const findDownloadRecord = (weekStart) =>
  db.data.downloadRecords.find((r) => r.weekStart === weekStart) || null;

export const addDownloadRecord = (weekStart) => {
  db.data.downloadRecords.push({ weekStart, downloadedAt: new Date().toISOString() });
  return save();
};

// --------------- Reset ---------------
export const resetWeek = (weekStart) => {
  removeComments({ weekStart });
  return save();
};

// --------------- Closed Dates ---------------
export const findClosedDates = (weekStart) =>
  db.data.closedDates.filter((c) => c.weekStart === weekStart);

export const findAllClosedDates = () => db.data.closedDates;

export const isDateClosed = (date) =>
  db.data.closedDates.some((c) => c.date === date);

export const addClosedDate = (date, weekStart, reason = '') => {
  if (db.data.closedDates.some((c) => c.date === date)) return false;
  db.data.closedDates.push({ date, weekStart, reason });
  save();
  return true;
};

export const removeClosedDate = (date) => {
  const before = db.data.closedDates.length;
  db.data.closedDates = db.data.closedDates.filter((c) => c.date !== date);
  if (db.data.closedDates.length !== before) save();
  return before - db.data.closedDates.length;
};
