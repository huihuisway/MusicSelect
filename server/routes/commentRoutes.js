import { findComments, addComment, findSongs, findOneSong } from '../database/db.js';
import { Router } from 'express';
const router = Router();

// ──────────────────────────────────────────────
// POST /api/comment ─ 提交评论
// ──────────────────────────────────────────────
router.post('/', async (req, res) => {
  try {
    const { songId, content } = req.body;

    if (!songId || !content) {
      return res.status(400).json({
        success: false, code: 400,
        message: '缺少必填字段：songId, content',
      });
    }

    const song = findOneSong({ songId });
    if (!song) {
      return res.status(404).json({ success: false, code: 404, message: '歌曲不存在' });
    }

    const comment = {
      id: `c_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      songId,
      content,
      createTime: new Date().toISOString(),
    };

    await addComment(comment);
    res.status(201).json({ success: true, data: comment });
  } catch (err) {
    console.error('[POST /comment]', err);
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

// ──────────────────────────────────────────────
// GET /api/comment?songId=xxx ─ 获取评论列表
// ──────────────────────────────────────────────
router.get('/', async (req, res) => {
  try {
    const { songId } = req.query;
    if (!songId) {
      return res.status(400).json({ success: false, code: 400, message: '缺少 songId 参数' });
    }
    const comments = findComments({ songId }).sort(
      (a, b) => new Date(b.createTime) - new Date(a.createTime),
    );
    res.json({ success: true, data: { songId, count: comments.length, comments } });
  } catch (err) {
    res.status(500).json({ success: false, code: 500, message: err.message });
  }
});

export default router;
