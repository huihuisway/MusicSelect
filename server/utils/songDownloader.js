/**
 * 歌曲下载器
 * 从网易云下载 MP3 → ffmpeg 转码至 320 kbps → 保存到 downloader/<weekStart>/
 *
 * ffmpeg-static 为可选依赖：如未安装，转码步骤会跳过，直接保存原始文件。
 */
import axios from 'axios';
import { createWriteStream, renameSync } from 'fs';
import { mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { pipeline } from 'stream/promises';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

import { getSongUrl } from './neteaseApi.js';

// ffmpeg-static 可选加载
let ffmpegPath = 'ffmpeg'; // 回退到系统 PATH 中的 ffmpeg
try {
  ffmpegPath = (await import('ffmpeg-static')).default || ffmpegPath;
} catch {
  console.warn('[songDownloader] ffmpeg-static 未安装，将使用系统 ffmpeg 或跳过转码');
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DOWNLOAD_DIR = join(__dirname, '..', '..', 'downloader');

// ──────────────────────────────────────────────
// 下载并转码单首歌曲
// ──────────────────────────────────────────────
export async function downloadAndConvert(songId, title, artist, weekStart) {
  const weekDir = join(DOWNLOAD_DIR, weekStart);
  if (!existsSync(weekDir)) mkdirSync(weekDir, { recursive: true });

  const safeTitle = (title || '未知歌曲').replace(/[\\/:*?"<>|]/g, '_');
  const safeArtist = (artist || '未知歌手').replace(/[\\/:*?"<>|]/g, '_');

  const url = await getSongUrl(songId);
  if (!url) return { success: false, error: '未获取到下载链接' };

  const tmpPath = join(weekDir, `_tmp_${songId}.mp3`);
  const finalPath = join(weekDir, `${safeTitle} - ${safeArtist}.mp3`);

  try {
    // 下载原始文件
    const resp = await axios.get(url, { responseType: 'stream', timeout: 60000 });
    await pipeline(resp.data, createWriteStream(tmpPath));

    // ffmpeg 转码至 320 kbps；如失败则直接重命名保留原始文件
    try {
      await convertAudio(tmpPath, finalPath);
    } catch (ffmpegErr) {
      console.warn(`[songDownloader] 转码失败，保留原始文件: ${ffmpegErr.message}`);
      renameSync(tmpPath, finalPath);
    }
    return { success: true, filePath: finalPath };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// ──────────────────────────────────────────────
// ffmpeg 转码
// ──────────────────────────────────────────────
function convertAudio(input, output) {
  return new Promise((resolve, reject) => {
    const proc = spawn(ffmpegPath, [
      '-i', input,
      '-codec:a', 'libmp3lame',
      '-b:a', '320k',
      '-y',
      output,
    ]);
    proc.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`ffmpeg 退出 code=${code}`));
    });
    proc.on('error', reject);
  });
}

// ──────────────────────────────────────────────
// 批量下载
// ──────────────────────────────────────────────
export async function downloadSongsBatch(songs, weekStart) {
  const results = [];
  for (let i = 0; i < songs.length; i++) {
    const s = songs[i];
    const r = await downloadAndConvert(s.songId, s.title, s.artist, weekStart);
    results.push({ songId: s.songId, title: s.title, index: i + 1, ...r });
  }
  return {
    total: songs.length,
    successCount: results.filter((r) => r.success).length,
    failCount: results.filter((r) => !r.success).length,
    results,
  };
}
