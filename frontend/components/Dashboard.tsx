'use client'; // This makes it a client component

import { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';

export default function Dashboard() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [message, setMessage] = useState('Connecting...');

  useEffect(() => {
    // Connect to backend WebSocket
    const newSocket = io('http://localhost:3000');
    setSocket(newSocket);

    newSocket.on('connect', () => {
      setMessage('Connected to server!');
      console.log('Socket connected:', newSocket.id);
    });

    newSocket.on('disconnect', () => {
      setMessage('Disconnected from server');
    });

    // Cleanup on unmount
    return () => {
      newSocket.disconnect();
    };
  }, []);

  const joinLeague = () => {
    if (socket) {
      socket.emit('join-league', 'test-league-123');
      setMessage('Joined test league!');
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-blue-800 mb-6">
        🏀 March Madness Fantasy
      </h1>
      
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-md">
        <h2 className="text-2xl font-semibold mb-4">Dashboard</h2>
        
        <div className="mb-6">
          <p className="text-gray-600 mb-2">Server Status:</p>
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
            message.includes('Connected') 
              ? 'bg-green-100 text-green-800' 
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            <span className="w-2 h-2 rounded-full bg-current mr-2"></span>
            {message}
          </div>
        </div>

        <button
          onClick={joinLeague}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200"
        >
          Join Test League
        </button>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <h3 className="text-lg font-medium mb-3">Coming Soon:</h3>
          <ul className="space-y-2 text-gray-600">
            <li className="flex items-center">
              <span className="mr-2">✅</span> User Authentication
            </li>
            <li className="flex items-center">
              <span className="mr-2">🔄</span> Live Draft System
            </li>
            <li className="flex items-center">
              <span className="mr-2">📊</span> Real-time Scoring
            </li>
            <li className="flex items-center">
              <span className="mr-2">🏆</span> League Management
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}