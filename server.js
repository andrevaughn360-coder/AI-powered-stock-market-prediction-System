// StockMind AI — backend proxy
// Keeps the Anthropic API key on the server, never exposed to the browser.

require('dotenv').config();
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const API_KEY = process.env.ANTHROPIC_API_KEY;

if (!API_KEY) {
  console.error('Missing ANTHROPIC_API_KEY. Set it in your .env file (see .env.example).');
  process.exit(1);
}

app.use(express.json({ limit: '1mb' }));

// Serve the frontend (public/index.html) as static files
app.use(express.static(path.join(__dirname, 'public')));

// Simple in-memory rate limiter: max N requests per IP per minute.
// Prevents someone from hammering your key if the page is public.
const RATE_LIMIT = 20; // requests
const RATE_WINDOW_MS = 60 * 1000;
const hits = new Map();

function rateLimit(req, res, next) {
  const ip = req.ip;
  const now = Date.now();
  const windowStart = now - RATE_WINDOW_MS;
  const timestamps = (hits.get(ip) || []).filter(t => t > windowStart);
  if (timestamps.length >= RATE_LIMIT) {
    return res.status(429).json({ error: 'Too many requests. Please slow down.' });
  }
  timestamps.push(now);
  hits.set(ip, timestamps);
  next();
}

// Single proxy endpoint. Frontend sends the same body shape it would have
// sent directly to Anthropic (model, max_tokens, messages, system?), and
// this just forwards it with the real API key attached server-side.
app.post('/api/claude', rateLimit, async (req, res) => {
  try {
    const { model, max_tokens, messages, system } = req.body || {};

    if (!Array.isArray(messages) || messages.length === 0) {
      return res.status(400).json({ error: 'Request must include a non-empty "messages" array.' });
    }

    const payload = {
      model: model || 'claude-sonnet-4-6',
      max_tokens: Math.min(max_tokens || 1000, 2000), // cap to control cost
      messages
    };
    if (system) payload.system = system;

    const anthropicRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify(payload)
    });

    const data = await anthropicRes.json();

    if (!anthropicRes.ok) {
      console.error('Anthropic API error:', data);
      return res.status(anthropicRes.status).json({ error: data.error?.message || 'Upstream API error' });
    }

    res.json(data);
  } catch (err) {
    console.error('Proxy error:', err);
    res.status(500).json({ error: 'Server error while contacting the AI.' });
  }
});

app.listen(PORT, () => {
  console.log(`StockMind AI backend running at http://localhost:${PORT}`);
});
