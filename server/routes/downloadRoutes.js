import { findSongs, findOneSong, findDownloadRecord, addDownloadRecord, getSkipWeek } from '../database/db.js';
import { getCurrentCycle } from '../utils/dateUtils.js';
import { downloadAndConvert, downloadSongsBatch } from '../utils/songDownloader.js';
import { Router } from 'express';
const router = Router();

// 辅助函数：获取有效的 weekStart（考虑管理员跳周覆盖）
function getEffectiveWeekStart() {
  const skipWeek = getSkipWeek();
  if (skipWeek) return skipWeek.weekStart;
  return getCurrentCycle().weekStart;
}

// ──────────────────────────────────────────────
// GET /api/song/download/:songId ─ 下载单首歌曲 MP3
// ──────────────────────────────────────────────
router.get('/download/:songId', async (req, res) => {
  try {
    const { songId } = req.params;
    const song = findOneSong({ songId });
    if (!song) {
      return res.status(404).json({ success: false, code: 404, message: '歌曲不存在' });
    }

    const result = await downloadAndConvert(songId, song.title, song.artist, song.weekStart);
    if (!result.success) {
      return res.status(500).json({ success: false, code: 500, message: '下载失败' });
    }
    res.download(result.filePath);
  } catch (err) {
    console.error('[GET /download/:songId]', err);
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// POST /api/song/download ─ 批量下载指定周歌曲
// ──────────────────────────────────────────────
router.post('/download', async (req, res) => {
  try {
    const { weekStart } = req.body || {};
    const target = weekStart || getEffectiveWeekStart();

    if (findDownloadRecord(target)) {
      return res.status(409).json({ success: false, code: 409, message: '本周歌曲已下载' });
    }

    const songs = findSongs({ weekStart: target, status: 'approved' });
    if (!songs.length) {
      return res.status(404).json({ success: false, code: 404, message: '无可下载歌曲' });
    }

    const results = await downloadSongsBatch(songs, target);
    await addDownloadRecord(target);
    res.json({ success: true, data: { weekStart: target, ...results } });
  } catch (err) {
    console.error('[POST /download]', err);
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

export default router;
