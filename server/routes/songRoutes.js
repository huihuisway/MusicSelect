import {
  findSongs, findOneSong, addSong, updateSongs,
  countSongs, findArchives, getArchiveWeeks,
} from '../database/db.js';
import {
  getCurrentCycle, isInSubmissionWindow,
  parseNeteaseUrl, formatDate, getMonday,
} from '../utils/dateUtils.js';
import { getSongDetail, checkSongUrl, searchSongs } from '../utils/neteaseApi.js';
import { downloadAndConvert } from '../utils/songDownloader.js';

import { Router } from 'express';
const router = Router();

// ──────────────────────────────────────────────
// POST /api/song/submit ─ 提交点歌
// ──────────────────────────────────────────────
router.post('/submit', async (req, res) => {
  try {
    const { link, submitterName, submitterClass, message, uid, preferredPlayDate, preferredPlayPosition } = req.body;

    if (!link || !submitterName || !submitterClass || !message) {
      return res.status(400).json({
        success: false, code: 400,
        message: '缺少必填字段：link, submitterName, submitterClass, message',
      });
    }

    if (!isInSubmissionWindow()) {
      return res.status(403).json({ success: false, code: 403, message: '当前不在点歌窗口期内' });
    }

    const { weekStart } = getCurrentCycle();

    if (uid && countSongs({ weekStart, uid }) >= 1) {
      return res.status(409).json({ success: false, code: 409, message: '你本周已经点过一首歌了，每人每周限点一首' });
    }

    if (countSongs({ weekStart }) >= (parseInt(process.env.WEEKLY_QUOTA) || 25)) {
      return res.status(429).json({ success: false, code: 429, message: '本周点歌名额已满' });
    }

    const songId = parseNeteaseUrl(link);
    if (!songId) {
      return res.status(400).json({ success: false, code: 400, message: '无法解析网易云音乐链接' });
    }

    if (findOneSong({ songId, weekStart })) {
      return res.status(409).json({ success: false, code: 409, message: '该歌曲已在本周歌单中' });
    }

    if (preferredPlayDate) {
      const monday = getMonday(new Date(weekStart));
      const playDate = formatDate(getMonday(new Date(preferredPlayDate + 'T00:00:00+08:00')));
      const weekMonday = formatDate(monday);
      if (playDate !== weekMonday) {
        return res.status(400).json({ success: false, code: 400, message: '播放日期不在本周范围内' });
      }
      if (preferredPlayPosition < 1 || preferredPlayPosition > 5) {
        return res.status(400).json({ success: false, code: 400, message: '播放位置须在 1-5 之间' });
      }
      const existing = countSongs({ weekStart, playDate: preferredPlayDate });
      if (existing >= 5) {
        return res.status(429).json({ success: false, code: 429, message: '该日期已无空位' });
      }
    }

    const detail = await getSongDetail(songId);
    if (!detail) {
      return res.status(404).json({ success: false, code: 404, message: '未找到该歌曲' });
    }

    const song = {
      songId,
      title: detail.title,
      artist: detail.artist,
      album: detail.album,
      coverUrl: detail.coverUrl,
      submitterName,
      submitterClass,
      message,
      uid: uid || null,
      submitTime: new Date().toISOString(),
      weekStart,
      playDate: preferredPlayDate || null,
      playPosition: preferredPlayPosition || null,
      status: 'pending',
    };

    await addSong(song);

    res.status(201).json({
      success: true,
      data: { songId, title: detail.title, artist: detail.artist, album: detail.album, coverUrl: detail.coverUrl, submitTime: song.submitTime },
    });
  } catch (err) {
    console.error('[POST /submit]', err);
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// POST /api/song/check ─ 检查歌曲
// ──────────────────────────────────────────────
router.post('/check', async (req, res) => {
  try {
    const { link, uid } = req.body;
    if (!link) return res.status(400).json({ success: false, code: 400, message: '缺少 link 字段' });

    const songId = parseNeteaseUrl(link);
    if (!songId) return res.status(400).json({ success: false, code: 400, message: '无法解析链接' });

    const detail = await getSongDetail(songId);
    if (!detail) return res.status(404).json({ success: false, code: 404, message: '未找到该歌曲' });

    const { weekStart } = getCurrentCycle();
    const exists = !!findOneSong({ songId, weekStart });
    const available = await checkSongUrl(songId);
    const hasSubmittedThisWeek = uid ? countSongs({ weekStart, uid }) >= 1 : false;

    res.json({ success: true, data: { songId, title: detail.title, artist: detail.artist, album: detail.album, coverUrl: detail.coverUrl, alreadySubmitted: exists, isAvailable: available, hasSubmittedThisWeek } });
  } catch (err) {
    console.error('[POST /check]', err);
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/song/search ─ 搜索歌曲
// ──────────────────────────────────────────────
router.get('/search', async (req, res) => {
  try {
    const { keywords, limit } = req.query;
    if (!keywords) {
      return res.status(400).json({ success: false, code: 400, message: '缺少 keywords 参数' });
    }

    const results = await searchSongs(keywords, parseInt(limit) || 5);
    res.json({ success: true, data: { results } });
  } catch (err) {
    console.error('[GET /search]', err);
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/song/list ─ 当前周期歌曲列表
// ──────────────────────────────────────────────
router.get('/list', async (req, res) => {
  try {
    const { week, date } = req.query;
    const { weekStart } = getCurrentCycle();
    const useWeek = week || weekStart;

    // 历史周走 archives
    if (week && week !== weekStart) {
      const archived = findArchives({ weekStart: week });
      const songs = date ? archived.filter((s) => s.playDate === date) : archived;
      return res.json({ success: true, data: { weekStart: week, count: songs.length, songs } });
    }

    const all = findSongs({ weekStart: useWeek });
    const isOver = !isInSubmissionWindow() && (!week || week === weekStart);
    const visible = isOver ? all.filter((s) => s.status === 'approved') : all;
    const songs = date ? visible.filter((s) => s.playDate === date) : visible;

    res.json({ success: true, data: { weekStart: useWeek, isSubmissionOver: isOver, count: songs.length, songs } });
  } catch (err) {
    console.error('[GET /list]', err);
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/song/current-cycle ─ 当前周期信息
// ──────────────────────────────────────────────
router.get('/current-cycle', async (_req, res) => {
  try {
    const cycle = getCurrentCycle();
    const submitted = countSongs({ weekStart: cycle.weekStart });
    const quota = parseInt(process.env.WEEKLY_QUOTA) || 25;
    res.json({ success: true, data: { ...cycle, submittedCount: submitted, weeklyQuota: quota, remaining: quota - submitted } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/song/calendar ─ 日历视图数据
// ──────────────────────────────────────────────
router.get('/calendar', async (req, res) => {
  try {
    const { week } = req.query;
    const { weekStart } = getCurrentCycle();
    const useWeek = week || weekStart;
    const songs = findSongs({ weekStart: useWeek });
    const monday = getMonday(new Date(useWeek));

    const days = Array.from({ length: 5 }, (_, i) => {
      const d = new Date(monday);
      d.setDate(d.getDate() + i);
      const dateStr = formatDate(d);
      const daySongs = songs.filter((s) => s.playDate === dateStr);
      return {
        date: dateStr,
        dayOfWeek: i + 1,
        dayLabel: ['周一', '周二', '周三', '周四', '周五'][i],
        songs: daySongs.sort((a, b) => (a.playPosition || 99) - (b.playPosition || 99)),
        count: daySongs.length,
        remaining: 5 - daySongs.length,
      };
    });

    const total = songs.length;
    res.json({ success: true, data: { weekStart: useWeek, days, total, remaining: (parseInt(process.env.WEEKLY_QUOTA) || 25) - total } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/song/history ─ 历史歌单
// ──────────────────────────────────────────────
router.get('/history', async (req, res) => {
  try {
    const { week } = req.query;
    if (week) {
      const archived = findArchives({ weekStart: week });
      return res.json({ success: true, data: { weekStart: week, count: archived.length, songs: archived } });
    }
    res.json({ success: true, data: { weeks: getArchiveWeeks() } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/song/stats ─ 本周统计
// ──────────────────────────────────────────────
router.get('/stats', async (_req, res) => {
  try {
    const { weekStart } = getCurrentCycle();
    const submitted = countSongs({ weekStart });
    const quota = parseInt(process.env.WEEKLY_QUOTA) || 25;
    res.json({ success: true, data: { weekStart, weeklyQuota: quota, submittedCount: submitted, remaining: quota - submitted, isOpen: isInSubmissionWindow() } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

export default router;
