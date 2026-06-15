/**
 * 网易云音乐 API 封装（带 node-cache 1 h 缓存）
 * 依赖：NeteaseCloudMusicApiEnhanced 运行在 NETEASE_API_BASE
 */
import axios from 'axios';
import NodeCache from 'node-cache';

const cache = new NodeCache({ stdTTL: 3600 });
const BASE = process.env.NETEASE_API_BASE || 'http://localhost:3030';

// ──────────────────────────────────────────────
// 获取歌曲详情
// ──────────────────────────────────────────────
export async function getSongDetail(songId) {
  const cached = cache.get(`detail_${songId}`);
  if (cached) return cached;

  try {
    const { data } = await axios.get(`${BASE}/song/detail`, {
      params: { ids: songId },
      timeout: 10000,
    });
    const song = data?.songs?.[0];
    if (!song) return null;

    const info = {
      songId: String(song.id),
      title: song.name,
      artist: (song.ar || []).map((a) => a.name).join(' / '),
      album: song.al?.name || '未知专辑',
      coverUrl: song.al?.picUrl || '',
    };
    cache.set(`detail_${songId}`, info);
    return info;
  } catch (err) {
    console.error(`[neteaseApi] getSongDetail(${songId})`, err.message);
    return null;
  }
}

// ──────────────────────────────────────────────
// 获取 MP3 下载链接（320 kbps）
// ──────────────────────────────────────────────
export async function getSongUrl(songId) {
  try {
    const { data } = await axios.get(`${BASE}/api/song/enhance/download/url`, {
      params: { id: songId, br: 320000 },
      timeout: 10000,
    });
    return data?.data?.url || null;
  } catch (err) {
    console.error(`[neteaseApi] getSongUrl(${songId})`, err.message);
    return null;
  }
}

// ──────────────────────────────────────────────
// 检查歌曲是否有可用的下载链接
// ──────────────────────────────────────────────
export async function checkSongUrl(songId) {
  const url = await getSongUrl(songId);
  return !!url;
}
