import { motion } from 'framer-motion';
import SongCard from './SongCard';

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五'];

/**
 * 单日分区 —— 日期标题 + 歌曲列表
 */
export default function DaySection({ day, index }) {
  const isEmpty = day.count === 0;

  return (
    <section id={`day-${day.date}`} className="scroll-mt-20">
      {/* 日期分隔标题 */}
      <div className="flex items-center gap-3 mb-3 mt-6 first:mt-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-zinc-300">{DAY_LABELS[index]}</span>
          <span className="text-xs text-zinc-600 tabular-nums">{day.date.slice(5)}</span>
        </div>
        <div className="flex-1 h-px bg-zinc-800" />
        <span className="text-xs text-zinc-600 tabular-nums">
          {day.count}/5
        </span>
      </div>

      {/* 歌曲列表 */}
      {isEmpty ? (
        <div className="border border-dashed border-zinc-800/60 py-6 text-center text-sm text-zinc-700">
          暂无歌曲
        </div>
      ) : (
        <div className="space-y-2">
          {day.songs
            .sort((a, b) => (a.playPosition || 99) - (b.playPosition || 99))
            .map((song, i) => (
              <motion.div
                key={song.songId}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <SongCard song={song} index={song.playPosition || i + 1} showComments />
              </motion.div>
            ))}
        </div>
      )}
    </section>
  );
}
