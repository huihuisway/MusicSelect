import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五'];

/**
 * 迷你日历条 —— 横向 5 格，点击滚动到对应日期分区
 */
export default function MiniCalendar({ days = [], weekStart }) {
  const scrollToDay = (date) => {
    const el = document.getElementById(`day-${date}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="grid grid-cols-5 gap-2">
      {days.map((day, i) => {
        const isEmpty = day.count === 0;
        const isFull = day.remaining === 0;

        return (
          <motion.button
            key={day.date}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => scrollToDay(day.date)}
            className={`border p-3 text-left transition-colors cursor-pointer ${
              isEmpty
                ? 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700'
                : isFull
                ? 'border-primary-700/50 bg-primary-950/20 hover:border-primary-600'
                : 'border-zinc-700 bg-zinc-900 hover:border-zinc-600'
            }`}
          >
            <div className="flex items-baseline justify-between mb-1">
              <span className="text-xs font-medium text-zinc-500">{DAY_LABELS[i]}</span>
              <span className="text-[10px] text-zinc-600 tabular-nums">{day.date.slice(5)}</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-bold tabular-nums">{day.count}</span>
              <span className="text-xs text-zinc-600">/5</span>
            </div>
            {/* 进度条 */}
            <div className="w-full h-0.5 bg-zinc-800 mt-2 overflow-hidden">
              <div
                className={`h-full transition-all ${isFull ? 'bg-primary-500' : 'bg-primary-600/50'}`}
                style={{ width: `${(day.count / 5) * 100}%` }}
              />
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}
