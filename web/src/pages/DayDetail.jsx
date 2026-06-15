import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import SongCard from '../components/SongCard';
import { getDaySongs } from '../api';

const DAY_NAMES = { 1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五' };

export default function DayDetail() {
  const { date } = useParams();
  const [songs, setSongs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDaySongs(date)
      .then((data) => { if (!cancelled) setSongs(data.songs); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [date]);

  const dayOfWeek = new Date(date + 'T00:00:00+08:00').getDay();
  const dayLabel = DAY_NAMES[dayOfWeek === 0 ? 7 : dayOfWeek] || '';

  return (
    <div className="space-y-6">
      <div>
        <Link to="/" className="text-sm text-zinc-600 hover:text-zinc-400 transition-colors mb-3 inline-flex items-center gap-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          返回本周
        </Link>

        <h1 className="text-2xl font-bold mt-2">
          {date}
          <span className="text-zinc-500 text-lg font-normal ml-2">{dayLabel}</span>
        </h1>
        <p className="text-zinc-500 text-sm mt-1">共 {songs.length} 首歌曲</p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-zinc-900 animate-pulse" />
          ))}
        </div>
      ) : songs.length === 0 ? (
        <div className="text-center py-20 text-zinc-600 border border-zinc-800/40 bg-zinc-900/20">
          <p>当日暂无歌曲</p>
        </div>
      ) : (
        <div className="space-y-3">
          {songs
            .sort((a, b) => (a.playPosition || 99) - (b.playPosition || 99))
            .map((song, i) => (
              <motion.div
                key={song.songId}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <SongCard song={song} index={song.playPosition || i + 1} showComments />
              </motion.div>
            ))}
        </div>
      )}
    </div>
  );
}
