import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import SongCard from '../components/SongCard';
import { getHistoryWeek } from '../api';

export default function WeekDetail() {
  const { week } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getHistoryWeek(week)
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [week]);

  return (
    <div className="space-y-6">
      <div>
        <Link to="/history" className="text-sm text-zinc-600 hover:text-zinc-400 transition-colors mb-3 inline-flex items-center gap-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          返回历史列表
        </Link>

        <h1 className="text-2xl font-bold mt-2">{week}</h1>
        <p className="text-zinc-500 text-sm mt-1">
          {data ? `${data.count} 首歌曲` : '加载中…'}
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-zinc-900 animate-pulse" />
          ))}
        </div>
      ) : !data?.songs?.length ? (
        <div className="text-center py-20 text-zinc-600 border border-zinc-800/40 bg-zinc-900/20">
          <p>该周暂无歌曲</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.songs.map((song, i) => (
            <motion.div
              key={song.songId}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <SongCard song={song} index={i + 1} showComments />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
