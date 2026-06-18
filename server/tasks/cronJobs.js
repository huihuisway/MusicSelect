/**
 * 定时任务
 *   1. 每 30 分钟检查：窗口关闭后自动下载本周歌曲
 *   2. 每周五 19:05：归档上周歌曲、批准遗留 pending 歌曲
 */
import cron from 'node-cron';
import {
  findSongs, updateSongs, archiveSongs,
  findDownloadRecord, addDownloadRecord,
  getSkipWeek,
} from '../database/db.js';
import { getCurrentCycle, isInSubmissionWindow, formatDate, getMonday } from '../utils/dateUtils.js';
import { downloadSongsBatch } from '../utils/songDownloader.js';

// 辅助函数：获取有效的 weekStart（考虑管理员跳周覆盖）
function getEffectiveWeekStart() {
  const skipWeek = getSkipWeek();
  if (skipWeek) return skipWeek.weekStart;
  return getCurrentCycle().weekStart;
}

/**
 * 任务 1：窗口关闭后自动下载歌曲
 * 每 30 分钟运行一次，只在周日 20:00 - 23:59 之间执行
 */
async function autoDownloadSongs() {
  const now = new Date();
  const u = new Date(now.getTime() + 8 * 3600 * 1000); // UTC+8
  const day = u.getUTCDay();
  const h = u.getUTCHours();

  // 仅在周日 20:00 后触发
  if (day !== 0 || h < 20) return;
  if (isInSubmissionWindow(now)) return; // 窗口仍开放则跳过

  const weekStart = getEffectiveWeekStart();

  if (findDownloadRecord(weekStart)) {
    console.log(`[cron] ${weekStart} 歌曲已下载，跳过`);
    return;
  }

  const songs = findSongs({ weekStart, status: 'approved' });
  if (!songs.length) {
    console.log(`[cron] ${weekStart} 无已批准歌曲`);
    return;
  }

  console.log(`[cron] 开始下载 ${weekStart} 的 ${songs.length} 首歌曲…`);
  const result = await downloadSongsBatch(songs, weekStart);
  await addDownloadRecord(weekStart);
  console.log(`[cron] 下载完成：成功 ${result.successCount} / ${result.total}`);
}

/**
 * 任务 2：每周五 19:05 执行周期重置
 *   - 归档上周 Songs → SongArchives
 *   - 批准上周遗留 pending 歌曲
 *   - 清理过期评论
 */
async function weeklyReset() {
  const now = new Date();
  const monday = getMonday(now);
  // 上周 weekStart = 本周一 - 7 天
  const lastMon = new Date(monday);
  lastMon.setUTCDate(monday.getUTCDate() - 7);
  const lastWeek = formatDate(lastMon);

  console.log(`[cron] 执行周重置：归档 ${lastWeek}`);

  // 先批准遗留
  updateSongs({ weekStart: lastWeek, status: 'pending' }, { status: 'approved' });

  // 归档（内部已清理对应评论）
  const archived = archiveSongs(lastWeek);
  console.log(`[cron] 已归档 ${archived} 首歌曲并清理对应评论`);
}

export function startCronJobs() {
  // 每 30 分钟
  cron.schedule('*/30 * * * *', () => {
    autoDownloadSongs().catch((e) => console.error('[cron] autoDownload 出错:', e));
  });

  // ⚠️ node-cron 使用服务器系统时区。
  //    如果服务器时区为 UTC+8，用 '5 19 * * 5'
  //    如果服务器时区为 UTC，用 '5 11 * * 5'（默认）
  //    推荐将服务器设为 UTC，避免夏令时问题。
  const isUTC = new Date().getTimezoneOffset() === 0;
  const resetExpr = isUTC ? '5 11 * * 5' : '5 19 * * 5';

  cron.schedule(resetExpr, () => {
    weeklyReset().catch((e) => console.error('[cron] weeklyReset 出错:', e));
  });

  console.log(`[cron] 定时任务已启动 (周重置: ${resetExpr})`);
}
