import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { getComments } from '../api';

/**
 * 评论列表组件
 * @param {{ songId: string }} props
 */
export default function CommentList({ songId }) {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getComments(songId)
      .then((data) => { if (!cancelled) setComments(data.comments); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [songId]);

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <div key={i} className="h-14 bg-zinc-800/30 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!comments.length) {
    return <p className="text-sm text-zinc-600 py-2">暂无评论</p>;
  }

  return (
    <div className="space-y-2.5">
      {comments.map((c, i) => (
        <motion.div
          key={c.id}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="bg-zinc-800/20 border border-zinc-800/40 p-3"
        >
          <div className="flex items-center justify-end mb-1.5">
            <span className="text-xs text-zinc-700 tabular-nums">
              {c.createTime?.slice(5, 16).replace('T', ' ')}
            </span>
          </div>
          <p className="text-sm text-zinc-400 leading-relaxed whitespace-pre-wrap">{c.content}</p>
        </motion.div>
      ))}
    </div>
  );
}
