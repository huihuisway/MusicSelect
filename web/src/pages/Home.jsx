import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import MiniCalendar from '../components/MiniCalendar';
import DaySection from '../components/DaySection';
import { getCurrentCycle, getCalendar } from '../api';

export default function Home() {
  const [cycle, setCycle] = useState(null);
  const [calData, setCalData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getCurrentCycle(), getCalendar()])
      .then(([c, cal]) => { setCycle(c); setCalData(cal); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-28 bg-zinc-900 animate-pulse" />
        <div className="grid grid-cols-5 gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-zinc-900 animate-pulse" />
          ))}
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-24 bg-zinc-900 animate-pulse" />)}
        </div>
      </div>
    );
  }

  const days = calData?.days || [];
  const totalSongs = days.reduce((sum, d) => sum + d.count, 0);
  const daysWithSongs = days.filter((d) => d.count > 0);

  return (
    <div className="space-y-6">
      {/* ── 周期信息卡片 ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="border border-zinc-800 bg-zinc-900/40 p-5"
      >
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold">本周歌单</h1>
            <p className="text-zinc-500 text-sm mt-0.5">{calData?.weekStart}</p>
          </div>
          <div className="flex gap-6">
            <div className="text-right">
              <div className="text-2xl font-bold tabular-nums">
                {totalSongs}
                <span className="text-sm text-zinc-600 font-normal">/{cycle?.weeklyQuota || 25}</span>
              </div>
              <p className="text-xs text-zinc-500">已提交</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold tabular-nums text-primary-400">
                {calData?.remaining || 0}
              </div>
              <p className="text-xs text-zinc-500">剩余</p>
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${cycle?.submissionOpen ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
          <span className="text-sm text-zinc-400">
            {cycle?.submissionOpen ? '点歌窗口开放中' : '点歌窗口已关闭'}
          </span>
          {cycle?.countdown?.total > 0 && cycle?.submissionOpen && (
            <span className="text-sm text-zinc-600">· 距关闭 {cycle.countdown.text}</span>
          )}
        </div>
      </motion.div>

      {/* ── 迷你日历条 ── */}
      <MiniCalendar days={days} weekStart={calData?.weekStart} />

      {/* ── 歌曲流（按日期分组） ── */}
      <div>
        {daysWithSongs.length === 0 ? (
          <div className="text-center py-20 text-zinc-600 border border-zinc-800/40 bg-zinc-900/20">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto mb-3 text-zinc-700">
              <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
            </svg>
            <p>本周暂无歌曲</p>
          </div>
        ) : (
          days.map((day, i) => (
            <DaySection key={day.date} day={day} index={i} />
          ))
        )}
      </div>
    </div>
  );
}
