import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五'];
const SLOTS_PER_DAY = 5;

/**
 * 日历组件
 * @param {{ days: Array, weekStart: string }} props
 */
export default function Calendar({ days = [], weekStart }) {
  return (
    <div className="grid grid-cols-5 gap-3">
      {days.map((day, i) => {
        const isEmpty = day.count === 0;
        const isFull = day.remaining === 0;

        return (
          <Link key={day.date} to={`/day/${day.date}`}>
            <motion.div
              whileHover={{ scale: 1.02 }}
              className={`border p-4 cursor-pointer transition-colors h-full ${
                isEmpty
                  ? 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700'
                  : isFull
                  ? 'border-primary-700/50 bg-primary-950/30 hover:border-primary-600'
                  : 'border-zinc-700 bg-zinc-900 hover:border-zinc-600'
              }`}
            >
              {/* 日期标题 */}
              <div className="flex items-baseline justify-between mb-3">
                <span className="text-xs font-medium text-zinc-500 uppercase">
                  {DAY_LABELS[i]}
                </span>
                <span className="text-xs text-zinc-600 tabular-nums">
                  {day.date.slice(5)}
                </span>
              </div>

              {/* 歌曲数量 */}
              <div className="text-2xl font-bold tabular-nums mb-1">
                {day.count}
                <span className="text-sm font-normal text-zinc-600">/{SLOTS_PER_DAY}</span>
              </div>

              {/* 进度条 */}
              <div className="w-full h-1 bg-zinc-800 overflow-hidden">
                <div
                  className={`h-full transition-all ${
                    isFull ? 'bg-primary-500' : 'bg-primary-600/60'
                  }`}
                  style={{ width: `${(day.count / SLOTS_PER_DAY) * 100}%` }}
                />
              </div>

              {/* 歌曲列表预览 */}
              {day.songs?.length > 0 && (
                <div className="mt-3 space-y-1">
                  {day.songs.slice(0, 3).map((song, idx) => (
                    <div key={song.songId} className="flex gap-1.5 items-center text-xs text-zinc-500">
                      <span className="text-zinc-700 tabular-nums">{idx + 1}</span>
                      <span className="truncate">{song.title}</span>
                    </div>
                  ))}
                  {day.count > 3 && (
                    <span className="text-xs text-zinc-700">+{day.count - 3} 首</span>
                  )}
                </div>
              )}

              {isEmpty && (
                <p className="mt-3 text-xs text-zinc-700">暂无歌曲</p>
              )}
            </motion.div>
          </Link>
        );
      })}
    </div>
  );
}
