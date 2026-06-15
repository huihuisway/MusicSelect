import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { getHistoryWeeks } from '../api';

export default function History() {
  const [weeks, setWeeks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHistoryWeeks()
      .then((data) => setWeeks(data.weeks || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">历史歌单</h1>
        <p className="text-zinc-500 text-sm mt-1">查看往期歌曲列表</p>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 bg-zinc-900 animate-pulse" />
          ))}
        </div>
      ) : weeks.length === 0 ? (
        <div className="text-center py-20 text-zinc-600 border border-zinc-800/40 bg-zinc-900/20">
          <p>暂无历史记录</p>
        </div>
      ) : (
        <div className="space-y-2">
          {weeks
            .sort()
            .reverse()
            .map((week, i) => (
              <motion.div
                key={week}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <Link
                  to={`/history/${week}`}
                  className="flex items-center justify-between border border-zinc-800 bg-zinc-900/40 p-4 hover:border-zinc-700 hover:bg-zinc-900 transition-colors group"
                >
                  <div>
                    <div className="font-medium text-base">{week}</div>
                    <div className="text-sm text-zinc-600 mt-0.5">播放周期</div>
                  </div>
                  <svg
                    width="16" height="16" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    className="text-zinc-700 group-hover:text-zinc-400 transition-colors"
                  >
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                </Link>
              </motion.div>
            ))}
        </div>
      )}
    </div>
  );
}
