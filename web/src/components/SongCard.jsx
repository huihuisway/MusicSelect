import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CommentList from './CommentList';

/**
 * 歌曲卡片组件
 * @param {{ song: object, index?: number, showComments?: boolean }} props
 */
export default function SongCard({ song, index, showComments = false }) {
  const [showCommentsState, setShowCommentsState] = useState(false);

  return (
    <div className="border border-zinc-800 bg-zinc-900/50 overflow-hidden group hover:border-zinc-700 transition-colors">
      <div className="flex gap-4 p-4">
        {/* 序号 */}
        {index != null && (
          <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-zinc-800 text-zinc-400 text-sm font-bold tabular-nums self-start">
            {index}
          </div>
        )}

        {/* 封面 */}
        <div className="flex-shrink-0 w-16 h-16 bg-zinc-800 overflow-hidden">
          {song.coverUrl ? (
            <img
              src={song.coverUrl}
              alt={song.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
              loading="lazy"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-700">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
              </svg>
            </div>
          )}
        </div>

        {/* 信息 */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-base truncate mb-0.5">{song.title}</h3>
          <p className="text-sm text-zinc-400 truncate">{song.artist}</p>
          <p className="text-xs text-zinc-600 truncate mt-0.5">{song.album}</p>

          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs text-zinc-500">
              {song.submitterClass} · {song.submitterName}
            </span>
            {song.playPosition && (
              <span className="text-xs px-1.5 py-0.5 bg-zinc-800 text-zinc-500 tabular-nums">
                #{song.playPosition}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 留言 */}
      {song.message && (
        <div className="px-4 pb-3 -mt-1">
          <p className="text-sm text-zinc-300 border-l-2 border-primary-600/50 pl-3 italic leading-relaxed">
            &ldquo;{song.message}&rdquo;
          </p>
        </div>
      )}

      {/* 评论入口 */}
      {showComments && (
        <div className="border-t border-zinc-800/60">
          <button
            onClick={() => setShowCommentsState(!showCommentsState)}
            className="w-full px-4 py-2.5 text-xs text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/40 transition-colors flex items-center gap-1.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            {showCommentsState ? '收起评论' : '查看评论'}
          </button>

          <AnimatePresence>
            {showCommentsState && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-4">
                  <CommentList songId={song.songId} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
