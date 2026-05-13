const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const app = express();
const server = http.createServer(app);

// Enable CORS
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'jyotish-video-signaling' });
});

const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Mock Database Storage
let users = [];
let astrologers = [
  { id: '101', name: 'Dr. Subramanian', phone_number: '9876543210', specialization: 'Vedic Astrology', rating: 4.8, price: 15, img: 'https://i.pravatar.cc/150?img=11', status: 'online' },
  { id: '102', name: 'Smt. Lakshmi', phone_number: '9876543211', specialization: 'Numerology & Tarot', rating: 4.9, price: 20, img: 'https://i.pravatar.cc/150?img=5', status: 'online' },
  { id: '103', name: 'Shri Ramachandran', phone_number: '9876543212', specialization: 'Prashna Jyotish', rating: 4.7, price: 10, img: 'https://i.pravatar.cc/150?img=60', status: 'offline' }
];

let socketToUserMap = {}; // socketId -> userId (or phone)
let userToSocketMap = {}; // phone -> socketId

// --- REST APIs ---

// 1. Send OTP (Mock)
app.post('/api/send-otp', (req, res) => {
  const { phone_number } = req.body;
  if (!phone_number) return res.status(400).json({ error: "Phone number required" });
  console.log(`Sending mock OTP 1234 to phone: ${phone_number}`);
  res.json({ success: true, message: "OTP 1234 sent successfully" });
});

// 2. Verify OTP (Mock)
app.post('/api/verify-otp', (req, res) => {
  const { phone_number, otp, role, name } = req.body;
  if (otp !== '1234') {
    return res.status(401).json({ error: "Invalid OTP" });
  }

  // Create or find user/astrologer
  let user;
  if (role === 'astrologer') {
    user = astrologers.find(a => a.phone_number === phone_number);
    if (!user) {
      user = { id: Date.now().toString(), name: name || 'New Astrologer', phone_number, role, status: 'online' };
      astrologers.push(user);
    }
  } else {
    user = users.find(u => u.phone_number === phone_number);
    if (!user) {
      user = { id: Date.now().toString(), name: name || 'User', phone_number, role: 'user' };
      users.push(user);
    }
  }

  res.json({ success: true, user });
});

// 3. Get Astrologers
app.get('/api/astrologers', (req, res) => {
  res.json({ astrologers });
});


// --- Socket.io Signaling ---
io.on('connection', (socket) => {
  console.log(`New socket connection: ${socket.id}`);

  // Register socket with a phone number (user or astrologer)
  socket.on('register', (data) => {
    const { phone_number, role } = data;
    socketToUserMap[socket.id] = phone_number;
    userToSocketMap[phone_number] = socket.id;
    console.log(`${role} registered: ${phone_number} on socket ${socket.id}`);
  });

  // User requests consultation to an astrologer
  socket.on('request-consultation', (data) => {
    // data: { astrologerPhone: string, userName: string, userPhone: string }
    const astroSocket = userToSocketMap[data.astrologerPhone];
    if (astroSocket) {
      io.to(astroSocket).emit('incoming-call', {
        callerSocketId: socket.id,
        callerPhone: data.userPhone,
        callerName: data.userName
      });
      console.log(`Call requested from ${data.userPhone} to ${data.astrologerPhone}`);
    } else {
      socket.emit('call-error', { message: 'Astrologer is currently offline.' });
    }
  });

  // User requests a public consultation (rings all available astrologers)
  socket.on('request-public-consultation', (data) => {
    // Find all astrologers who are currently connected
    const availableAstros = astrologers.filter(a => userToSocketMap[a.phone_number] && a.status === 'online');
    
    if (availableAstros.length > 0) {
      console.log(`Public call requested from ${data.userPhone}. Ringing ${availableAstros.length} astrologers...`);
      availableAstros.forEach(astro => {
        const astroSocket = userToSocketMap[astro.phone_number];
        if (astroSocket) {
          io.to(astroSocket).emit('incoming-call', {
            callerSocketId: socket.id,
            callerPhone: data.userPhone,
            callerName: data.userName,
            isPublic: true
          });
        }
      });
    } else {
      socket.emit('call-error', { message: 'No astrologers are available right now. Please try again later.' });
    }
  });

  // Astrologer accepts call
  socket.on('accept-call', (data) => {
    // data: { callerSocketId: string, isPublic: boolean }
    io.to(data.callerSocketId).emit('call-accepted', {
      astrologerSocketId: socket.id
    });
    
    // Tell other astrologers to stop ringing
    socket.broadcast.emit('cancel-ringing', { callerSocketId: data.callerSocketId });
    
    console.log(`Call accepted by ${socket.id}`);
  });

  // Astrologer rejects call
  socket.on('reject-call', (data) => {
    io.to(data.callerSocketId).emit('call-rejected', {
      message: 'Astrologer declined the call.'
    });
  });

  // WebRTC Signaling: Offer
  socket.on('webrtc-offer', (data) => {
    io.to(data.targetSocketId).emit('webrtc-offer', {
      offer: data.offer,
      senderSocketId: socket.id
    });
  });

  // WebRTC Signaling: Answer
  socket.on('webrtc-answer', (data) => {
    io.to(data.targetSocketId).emit('webrtc-answer', {
      answer: data.answer,
      senderSocketId: socket.id
    });
  });

  // WebRTC Signaling: ICE Candidate
  socket.on('webrtc-ice-candidate', (data) => {
    io.to(data.targetSocketId).emit('webrtc-ice-candidate', {
      candidate: data.candidate,
      senderSocketId: socket.id
    });
  });

  // End Call
  socket.on('end-call', (data) => {
    if (data.targetSocketId) {
      io.to(data.targetSocketId).emit('call-ended');
    }
  });

  // Disconnect
  socket.on('disconnect', () => {
    const phone = socketToUserMap[socket.id];
    delete socketToUserMap[socket.id];
    if (phone) {
      delete userToSocketMap[phone];
      console.log(`${phone} disconnected.`);
    }
  });
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`Video Consultation API & Signaling Server running on port ${PORT}`);
});
