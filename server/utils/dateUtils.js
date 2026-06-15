/**
 * 日期工具模块 —— 所有时间均基于 UTC+8（北京时间）
 *
 * 周期规则：
 *   点歌窗口：每周五 19:00 — 周日 20:00
 *   播放周期：下周一至周五（5 天，每天最多 5 首）
 *   weekStart：播放周期所在周一的日期字符串（YYYY-MM-DD）
 */

// ── 底层时间工具 ──────────────────────────────

/** 获取当前 UTC+8 时间（Date 对象） */
export function getUTC8Now() {
  return new Date(Date.now() + 8 * 3600 * 1000);
}

/** 将任意 Date 转换为 UTC+8 等效 Date */
export function toUTC8(date = new Date()) {
  return new Date(date.getTime() + 8 * 3600 * 1000);
}

/** 格式化日期为 YYYY-MM-DD（基于 UTC+8） */
export function formatDate(date) {
  const u = toUTC8(date);
  return u.toISOString().slice(0, 10);
}

// ── 周期计算 ──────────────────────────────────

/**
 * 获取 date 所在周的周一（UTC+8 日期）
 * getUTCDay(): 0=Sun … 6=Sat，JS 中周一 = 1
 */
export function getMonday(date) {
  const u = toUTC8(date);
  const day = u.getUTCDay();
  const diff = day === 0 ? -6 : 1 - day;   // 周日回退 6 天，其余回退到周一
  const mon = new Date(u);
  mon.setUTCDate(u.getUTCDate() + diff);
  mon.setUTCHours(0, 0, 0, 0);
  return mon;
}

/**
 * 判断当前是否处于点歌窗口（周五 19:00 — 周日 20:00 UTC+8）
 */
export function isInSubmissionWindow(date = new Date()) {
  const u = toUTC8(date);
  const day = u.getUTCDay();
  const h = u.getUTCHours();
  const m = u.getUTCMinutes();
  if (day === 6 /* 周六 */) return true;
  if (day === 5 && h >= 19) return true;
  if (day === 0 && (h < 20)) return true;  // 周日 20:00 整点视为窗口关闭
  return false;
}

/**
 * 获取当前周期信息
 *
 * @returns {{
 *   weekStart: string,          // 本周对应播放周期周一 YYYY-MM-DD
 *   submissionOpen: boolean,    // 当前窗口是否开放
 *   countdown: { total:number, hours:number, minutes:number, seconds:number, text:string }
 * }}
 */
export function getCurrentCycle() {
  const now = new Date();
  const open = isInSubmissionWindow(now);
  const weekStart = calcWeekStart(now);
  return { weekStart, submissionOpen: open, countdown: getOpenCountdown(now) };
}

/**
 * 根据当前时间计算 weekStart
 *  - 窗口内 / 窗口刚结束（周日 20:00 后 24 h 内）：返回下周一
 *  - 其他时间：返回本周一
 */
function calcWeekStart(date) {
  const u = toUTC8(date);
  const day = u.getUTCDay();
  const h = u.getUTCHours();

  let monday;

  if (day === 6 /* 周六 */ || day === 0 /* 周日 */) {
    // 窗口内 → 下一个播放周期
    monday = getMonday(date);
    monday.setUTCDate(monday.getUTCDate() + 7);
  } else if (day === 1 && h < 20) {
    // 周一 00:00-20:00：周日窗口刚结束，仍属上一周期
    monday = getMonday(date);
    monday.setUTCDate(monday.getUTCDate() + 7);
  } else {
    // 周二至周日（非窗口）或周一 20:00 后 → 当前播放周期
    monday = getMonday(date);
  }

  return formatDate(monday);
}

/**
 * 获取倒计时（窗口开放时 → 距关闭；窗口关闭时 → 距下次开放）
 */
export function getOpenCountdown(date = new Date()) {
  const u = toUTC8(date);
  const day = u.getUTCDay();
  const h = u.getUTCHours();
  const open = isInSubmissionWindow(date);

  let target;

  if (open) {
    // 窗口开放中 → 目标 = 周日 20:00（关闭时刻）
    target = new Date(u);
    const daysToSun = (7 - day) % 7;
    target.setUTCDate(u.getUTCDate() + daysToSun);
    target.setUTCHours(20, 0, 0, 0);
  } else if (day < 5 || (day === 5 && h < 19)) {
    // 窗口未开放 → 目标 = 本/下一个周五 19:00
    const daysUntilFri = (5 - day + 7) % 7;
    target = new Date(u);
    target.setUTCDate(u.getUTCDate() + daysUntilFri);
    target.setUTCHours(19, 0, 0, 0);
    // 如果目标时间已过（周五 19:00 之前调用了本分支），推到下周
    if (target.getTime() <= u.getTime()) {
      target.setUTCDate(target.getUTCDate() + 7);
    }
  } else {
    // 窗口刚关闭（周日 20:00+）→ 目标 = 下周五 19:00
    const daysUntilFri = (5 - day + 7) % 7 || 7;
    target = new Date(u);
    target.setUTCDate(u.getUTCDate() + daysUntilFri);
    target.setUTCHours(19, 0, 0, 0);
  }

  const total = Math.max(0, Math.floor((target.getTime() - u.getTime()) / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const text = `${hours}小时${minutes}分${seconds}秒`;
  return { total, hours, minutes, seconds, text };
}

// ── 网易云链接解析 ─────────────────────────────

/**
 * 从网易云音乐链接中提取歌曲 ID
 * @param {string} url
 * @returns {string|null}
 *
 * 支持格式：
 *   https://music.163.com/#/song?id=123456
 *   https://music.163.com/song?id=123456
 *   https://music.163.com/song/123456
 *   https://share.163.com/song/123456
 */
export function parseNeteaseUrl(url) {
  if (!url || typeof url !== 'string') return null;
  const patterns = [
    /song\?id=(\d+)/,
    /\/song\/(\d+)/,
    /\/(\d{5,})/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}
