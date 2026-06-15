import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

import songRoutes from './routes/songRoutes.js';
import commentRoutes from './routes/commentRoutes.js';
import downloadRoutes from './routes/downloadRoutes.js';
import { startCronJobs } from './tasks/cronJobs.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 4000;

// --------------- 中间件 ---------------
app.use(cors());
app.use(express.json());

// --------------- API 路由 ---------------
app.use('/api/song', songRoutes);
app.use('/api/comment', commentRoutes);
app.use('/api/song', downloadRoutes);

// --------------- 健康检查 ---------------
app.get('/api/health', (_req, res) => {
  res.json({ success: true, message: 'ok' });
});

// --------------- 生产环境：托管前端 ---------------
if (process.env.NODE_ENV === 'production') {
  const webDist = path.join(__dirname, '..', 'web', 'dist');
  app.use(express.static(webDist));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(webDist, 'index.html'));
  });
}

// --------------- 404 处理（非生产环境下的 API 路由） ---------------
app.use('/api/*', (_req, res) => {
  res.status(404).json({ success: false, code: 404, message: '接口不存在' });
});

// --------------- 错误处理 ---------------
app.use((err, _req, res, _next) => {
  console.error('[Error]', err);
  res.status(err.status || 500).json({
    success: false,
    code: err.status || 500,
    message: err.message || '服务器内部错误',
  });
});

// --------------- 启动 ---------------
app.listen(PORT, () => {
  console.log(`[MusicSelect] 服务已启动: http://localhost:${PORT}`);
  startCronJobs();
});
