import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { Server } from 'socket.io';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: ["http://localhost:3000", "http://localhost:3001"],
    credentials: true
  }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'March Madness Fantasy API',
    timestamp: new Date().toISOString(),
    message: 'Backend server is running correctly!'
  });
});

// Test endpoint
app.get('/api/test', (req, res) => {
  res.json({ 
    message: 'API is working!',
    data: {
      features: ['User Auth', 'League Management', 'Live Draft', 'Real-time Scoring'],
      status: 'active'
    }
  });
});

// WebSocket connection
io.on('connection', (socket) => {
  console.log('🏀 Client connected:', socket.id);
  
  socket.emit('welcome', {
    message: 'Welcome to March Madness Fantasy!',
    connectionId: socket.id,
    timestamp: new Date().toISOString()
  });
  
  socket.on('draft-test', (data) => {
    console.log('Draft test received:', data);
    socket.emit('draft-update', {
      type: 'pick',
      player: data.playerName,
      team: 'Test Team',
      timestamp: new Date().toISOString()
    });
  });
  
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Use port 3001 for backend (3000 is for frontend)
const PORT = process.env.PORT || 3001;
httpServer.listen(PORT, () => {
  console.log(`🚀 Backend server running on http://localhost:${PORT}`);
  console.log(`📡 WebSocket server ready on ws://localhost:${PORT}`);
  console.log(`✅ Health check: http://localhost:${PORT}/api/health`);
});