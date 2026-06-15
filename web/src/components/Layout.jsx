import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function Layout({ children }) {
  const location = useLocation();

  const links = [
    { to: '/', label: '本周歌单' },
    { to: '/history', label: '历史歌单' },
  ];

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* ── 顶部导航 ── */}
      <nav className="border-b border-zinc-800 sticky top-0 z-50 bg-zinc-950/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18V5l12-2v13" />
                <circle cx="6" cy="18" r="3" />
                <circle cx="18" cy="16" r="3" />
              </svg>
            </div>
            <span className="text-lg font-semibold tracking-tight">MusicSelect</span>
          </Link>

          <div className="flex gap-1">
            {links.map((l) => {
              const active = location.pathname === l.to;
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    active
                      ? 'text-white bg-zinc-800'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* ── 主内容 ── */}
      <motion.main
        key={location.pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="max-w-6xl mx-auto px-6 py-8"
      >
        {children}
      </motion.main>
    </div>
  );
}
