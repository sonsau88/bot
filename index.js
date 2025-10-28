// index.js
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
app.use(bodyParser.json());

// Lấy biến môi trường
const PAGE_ACCESS_TOKEN  = process.env.PAGE_ACCESS_TOKEN;
const VERIFY_TOKEN       = process.env.VERIFY_TOKEN;
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID   = process.env.TELEGRAM_CHAT_ID; // bạn phải đặt

// Health‑check endpoint cho Render hoặc dịch vụ
app.get('/healthz', (req, res) => {
  res.send('ok');
});

// Facebook webhook xác minh
app.get('/webhook', (req, res) => {
  const mode      = req.query['hub.mode'];
  const token     = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];

  if (mode && token) {
    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
      console.log('✅ Webhook verified');
      return res.status(200).send(challenge);
    } else {
      return res.sendStatus(403);
    }
  }
  res.sendStatus(400);
});

// Nhận tin nhắn từ Facebook Messenger
app.post('/webhook', async (req, res) => {
  const body = req.body;

  if (body.object === 'page') {
    for (const entry of body.entry) {
      const webhook_event = entry.messaging[0];
      const senderId = webhook_event.sender.id;

      if (webhook_event.message && webhook_event.message.text) {
        const messageText = webhook_event.message.text;

        // Gửi thông báo tới Telegram (nếu đã cấu hình)
        if (TELEGRAM_BOT_TOKEN && TELEGRAM_CHAT_ID) {
          try {
            await axios.post(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
              chat_id: TELEGRAM_CHAT_ID,
              text: `📩 Tin nhắn từ Facebook: ${messageText}\nFB ID: ${senderId}`
            });
          } catch (err) {
            console.error('Telegram send error:', err.message);
          }
        }

        // Trả lời lại người dùng trên Facebook
        try {
          await axios.post(
            `https://graph.facebook.com/v18.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`,
            {
              recipient: { id: senderId },
              message:    { text: "Dạ anh/chị cần hỗ trợ gì ạ?" }
            }
          );
        } catch (err) {
          console.error('Facebook send error:', err.message);
        }
      }
    }
    res.status(200).send('EVENT_RECEIVED');
  } else {
    res.sendStatus(404);
  }
});

// Khởi chạy server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server is running on port ${PORT}`);
});

