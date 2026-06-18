import {
  findSongs, findOneSong, addSong, updateSongs,
  countSongs, findArchives, getArchiveWeeks,
  findClosedDates, isDateClosed, addClosedDate, removeClosedDate,
  getSkipWeek, activateSkipWeek, deactivateSkipWeek,
} from '../database/db.js';
import {
  getCurrentCycle, isInSubmissionWindow, getUTC8Now,
  parseNeteaseUrl, formatDate, getMonday,
} from '../utils/dateUtils.js';
import { getSongDetail, checkSongUrl, searchSongs } from '../utils/neteaseApi.js';
import { downloadAndConvert } from '../utils/songDownloader.js';

import { Router } from 'express';
const router = Router();

// ──────────────────────────────────────────────
// 辅助函数：获取有效的周期信息（考虑管理员覆盖）
// ──────────────────────────────────────────────
function getEffectiveCycle() {
  const cycle = getCurrentCycle();
  const skipWeek = getSkipWeek();

  // 如果有管理员跳周覆盖，使用覆盖的 weekStart
  if (skipWeek) {
    return {
      ...cycle,
      weekStart: skipWeek.weekStart,
      submissionOpen: true, // 跳周后立即开放点歌窗口
      isSkippedByAdmin: true,
      skipWeekInfo: skipWeek,
      countdown: { total: 0, hours: 0, minutes: 0, seconds: 0, text: '管理员已开放点歌' },
    };
  }

  return cycle;
}

// ──────────────────────────────────────────────
// POST /api/song/submit ─ 提交点歌
// ──────────────────────────────────────────────
router.post('/submit', async (req, res) => {
  try {
    const { link, submitterName, submitterClass, message, uid, preferredPlayDate, preferredPlayPosition } = req.body;

    if (!link) {
      return res.status(400).json({
        success: false, code: 400,
        message: '缺少必填字段：link',
      });
    }

    // 检查是否点了过去的日期（不再检查窗口期）
    if (preferredPlayDate) {
      const now = getUTC8Now();
      const todayStr = formatDate(now);
      const noonToday = new Date(now);
      noonToday.setUTCHours(12, 0, 0, 0);

      if (preferredPlayDate < todayStr) {
        return res.status(403).json({ success: false, code: 403, message: '不能点过去日期的歌哦' });
      }
      if (preferredPlayDate === todayStr && now >= noonToday) {
        return res.status(403).json({ success: false, code: 403, message: '已过中午 12:00，今天的歌已不能点，请选择明天或之后' });
      }
    }

    const { weekStart } = getEffectiveCycle();

    // 检查日期是否被关闭
    if (preferredPlayDate && isDateClosed(preferredPlayDate)) {
      return res.status(403).json({ success: false, code: 403, message: `${preferredPlayDate} 已关闭点歌（休息日），请选择其他日期` });
    }

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
      submitterName: submitterName || '',
      submitterClass: submitterClass || '',
      message: message || '',
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

    const { weekStart } = getEffectiveCycle();
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
    const { weekStart } = getEffectiveCycle();
    const useWeek = week || weekStart;

    // 历史周走 archives
    if (week && week !== weekStart) {
      const archived = findArchives({ weekStart: week });
      const songs = date ? archived.filter((s) => s.playDate === date) : archived;
      return res.json({ success: true, data: { weekStart: week, count: songs.length, songs } });
    }

    // 本周显示所有歌曲（不再根据窗口期过滤状态）
    const all = findSongs({ weekStart: useWeek });
    const songs = date ? all.filter((s) => s.playDate === date) : all;

    res.json({ success: true, data: { weekStart: useWeek, count: songs.length, songs } });
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
    const cycle = getEffectiveCycle();
    const { weekStart } = cycle;
    const submitted = countSongs({ weekStart });
    const quota = parseInt(process.env.WEEKLY_QUOTA) || 25;

    // 计算每天的歌曲数量
    const songs = findSongs({ weekStart });
    const songsByDay = {};
    for (const song of songs) {
      if (song.playDate) {
        songsByDay[song.playDate] = (songsByDay[song.playDate] || 0) + 1;
      }
    }

    // 获取关闭的日期
    const closedDates = findClosedDates(weekStart).map((c) => c.date);

    res.json({
      success: true,
      data: {
        ...cycle,
        songsByDay,
        closedDates,
        submittedCount: submitted,
        weeklyQuota: quota,
        remaining: quota - submitted,
      },
    });
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
    const { weekStart } = getEffectiveCycle();
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
    const cycle = getEffectiveCycle();
    const { weekStart } = cycle;
    const submitted = countSongs({ weekStart });
    const quota = parseInt(process.env.WEEKLY_QUOTA) || 25;
    res.json({ success: true, data: { weekStart, weeklyQuota: quota, submittedCount: submitted, remaining: quota - submitted, isOpen: cycle.submissionOpen } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/closed-dates ─ 获取关闭日期
// ──────────────────────────────────────────────
router.get('/closed-dates', async (req, res) => {
  try {
    const { weekStart } = req.query;
    if (weekStart) {
      const dates = findClosedDates(weekStart);
      return res.json({ success: true, data: { weekStart, closedDates: dates } });
    }
    // 返回所有关闭日期
    const all = findClosedDates();
    res.json({ success: true, data: { closedDates: all } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// POST /api/closed-dates ─ 添加关闭日期
// ──────────────────────────────────────────────
router.post('/closed-dates', async (req, res) => {
  try {
    const { date, weekStart, reason } = req.body;
    if (!date || !weekStart) {
      return res.status(400).json({ success: false, code: 400, message: '缺少 date 或 weekStart' });
    }
    const added = addClosedDate(date, weekStart, reason || '');
    if (!added) {
      return res.status(409).json({ success: false, code: 409, message: '该日期已关闭' });
    }
    res.status(201).json({ success: true, data: { date, weekStart, reason } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// DELETE /api/closed-dates ─ 移除关闭日期
// ──────────────────────────────────────────────
router.delete('/closed-dates', async (req, res) => {
  try {
    const { date } = req.body;
    if (!date) {
      return res.status(400).json({ success: false, code: 400, message: '缺少 date' });
    }
    const removed = removeClosedDate(date);
    if (!removed) {
      return res.status(404).json({ success: false, code: 404, message: '该日期未关闭' });
    }
    res.json({ success: true, data: { date } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/admin/skip-week ─ 获取跳周状态
// ──────────────────────────────────────────────
router.get('/admin/skip-week', async (_req, res) => {
  try {
    const skipWeek = getSkipWeek();
    const effectiveCycle = getEffectiveCycle();

    res.json({
      success: true,
      data: {
        skipWeek,
        isActive: !!skipWeek,
        currentWeekStart: effectiveCycle.weekStart,
        isSubmissionOpen: effectiveCycle.submissionOpen,
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// POST /api/admin/skip-week ─ 激活跳周
// ──────────────────────────────────────────────
router.post('/admin/skip-week', async (req, res) => {
  try {
    const { activatedBy } = req.body;

    // 检查是否已经激活
    const existing = getSkipWeek();
    if (existing) {
      return res.status(409).json({
        success: false,
        code: 409,
        message: '跳周已激活',
        data: existing,
      });
    }

    // 计算下一周的 weekStart
    const now = new Date();
    const nextMonday = getMonday(now);
    nextMonday.setUTCDate(nextMonday.getUTCDate() + 7);
    const nextWeekStart = formatDate(nextMonday);

    // 激活跳周
    const skipWeek = activateSkipWeek(nextWeekStart, activatedBy || 'unknown');

    res.status(201).json({
      success: true,
      data: {
        ...skipWeek,
        message: `已跳到下一周（${nextWeekStart}），点歌窗口已开放`,
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// DELETE /api/admin/skip-week ─ 撤销跳周
// ──────────────────────────────────────────────
router.delete('/admin/skip-week', async (_req, res) => {
  try {
    const was = deactivateSkipWeek();

    if (!was) {
      return res.status(404).json({
        success: false,
        code: 404,
        message: '跳周未激活',
      });
    }

    res.json({
      success: true,
      data: {
        deactivated: was,
        message: '已撤销跳周，恢复正常周期',
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

export default router;
