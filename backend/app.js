import 'dotenv/config';
import express from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import axios from 'axios';
import authRoutes from './routes/authRoutes.js';
import auth from './middleware/auth.js';

const app = express();

// ── Middleware ────────────────────────────────────────────────────────────────
app.use(cors());
app.use(express.json());

// ── Database Connection ───────────────────────────────────────────────────────
// useNewUrlParser & useUnifiedTopology are deprecated no-ops in Mongoose 6+
mongoose
  .connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/shopsense')
  .then(() => console.log('✅ MongoDB Connected'))
  .catch((err) => console.error('❌ MongoDB Connection Error:', err));

// ── Auth Routes (public) ─────────────────────────────────────────────────────
// POST /api/v1/login  |  POST /api/v1/register  |  POST /api/v1/refresh
app.use('/api/v1', authRoutes);

// ── Python FastAPI base URL ───────────────────────────────────────────────────
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000';

// ── Protected proxy routes ────────────────────────────────────────────────────
// All protected endpoints are under /api/v1 — auth middleware guards each one.

app.get('/api/v1/products', auth, async (req, res) => {
  try {
    const response = await axios.get(`${PYTHON_API_URL}/products`);
    res.json(response.data);
  } catch (error) {
    console.error('Python API Error (products):', error.message);
    res
      .status(error.response?.status || 500)
      .json(error.response?.data || { message: 'Error fetching products' });
  }
});

app.get('/api/v1/search', auth, async (req, res) => {
  try {
    const response = await axios.get(`${PYTHON_API_URL}/search`, {
      params: req.query,
    });
    res.json(response.data);
  } catch (error) {
    console.error('Python API Error (search):', error.message);
    res
      .status(error.response?.status || 500)
      .json(error.response?.data || { message: 'Error searching products' });
  }
});

app.post('/api/v1/recommend', auth, async (req, res) => {
  try {
    console.log('[recommend] forwarding to Python:', JSON.stringify(req.body));
    const response = await axios.post(`${PYTHON_API_URL}/recommend`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Python API Error (recommend):', error.message);
    res
      .status(error.response?.status || 500)
      .json(error.response?.data || { message: 'Error getting recommendations' });
  }
});

// ── Health check ──────────────────────────────────────────────────────────────
app.get('/api/v1/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// ── Start Server ──────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 Express server running on http://localhost:${PORT}`);
  console.log(`   Auth  → /api/v1/login | /api/v1/register | /api/v1/refresh`);
  console.log(`   Proxy → /api/v1/products | /api/v1/search | /api/v1/recommend`);
});
