'use client';

import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export default function Home() {
  const [backendStatus, setBackendStatus] = useState<string>('Checking backend...');
  const [socket, setSocket] = useState<Socket | null>(null);
  const [messages, setMessages] = useState<string[]>([]);
  const [apiTest, setApiTest] = useState<any>(null);

  useEffect(() => {
    // Test backend API connection
    const checkBackend = async () => {
      try {
        const response = await fetch('http://localhost:3001/api/health');
        const data = await response.json();
        setBackendStatus(`✅ ${data.message}`);
        
        // Test API endpoint
        const testResponse = await fetch('http://localhost:3001/api/test');
        const testData = await testResponse.json();
        setApiTest(testData);
      } catch (error) {
        setBackendStatus('❌ Backend connection failed');
      }
    };

    checkBackend();

    // Connect to WebSocket
    const newSocket = io('http://localhost:3001');
    setSocket(newSocket);

    newSocket.on('connect', () => {
      addMessage('Connected to WebSocket server');
    });

    newSocket.on('welcome', (data) => {
      addMessage(`Server: ${data.message}`);
    });

    newSocket.on('draft-update', (data) => {
      addMessage(`Draft: ${data.player} picked by ${data.team}`);
    });

    return () => {
      newSocket.disconnect();
    };
  }, []);

  const addMessage = (msg: string) => {
    setMessages(prev => [...prev, `${new Date().toLocaleTimeString()}: ${msg}`]);
  };

  const sendTestDraft = () => {
    if (socket) {
      socket.emit('draft-test', {
        playerName: 'Test Player',
        leagueId: 'test-123'
      });
      addMessage('Sent draft test message');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="text-center mb-10">
          <h1 className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-green-600 mb-4">
            🏀 March Madness Fantasy
          </h1>
          <p className="text-lg text-gray-600">
            Build your ultimate NCAA tournament fantasy team
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Backend Status Card */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-3 h-3 rounded-full bg-green-500 mr-3"></div>
              <h2 className="text-2xl font-bold text-gray-800">System Status</h2>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="font-semibold text-blue-800">Frontend</p>
                <p className="text-green-600 mt-1">✅ Running on http://localhost:3000</p>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="font-semibold text-blue-800">Backend API</p>
                <p className={backendStatus.includes('✅') ? 'text-green-600' : 'text-red-600'}>
                  {backendStatus}
                </p>
              </div>
              {apiTest && (
                <div className="p-4 bg-green-50 rounded-lg">
                  <p className="font-semibold text-green-800">API Test Response</p>
                  <p className="text-gray-700 mt-1">{apiTest.message}</p>
                  <div className="mt-2 text-sm text-gray-600">
                    Features: {apiTest.data?.features?.join(', ')}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* WebSocket Console */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-3 h-3 rounded-full bg-blue-500 mr-3"></div>
              <h2 className="text-2xl font-bold text-gray-800">Real-time Console</h2>
            </div>
            
            <div className="mb-4">
              <button
                onClick={sendTestDraft}
                disabled={!socket}
                className="w-full bg-gradient-to-r from-blue-600 to-green-600 hover:from-blue-700 hover:to-green-700 text-white font-semibold py-3 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Test Draft System
              </button>
            </div>

            <div className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm h-64 overflow-y-auto">
              {messages.length === 0 ? (
                <p className="text-gray-400 italic">Waiting for messages...</p>
              ) : (
                messages.map((msg, i) => (
                  <div key={i} className="mb-2 border-l-2 border-green-500 pl-3">
                    <span className="text-green-400">▶</span> {msg}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Features Preview */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">🚀 Next Steps</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition">
                <div className="text-2xl mb-3">👤</div>
                <h3 className="font-bold text-lg mb-2">User Authentication</h3>
                <p className="text-gray-600 text-sm">Login, registration, and user profiles</p>
              </div>
              <div className="border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition">
                <div className="text-2xl mb-3">🏆</div>
                <h3 className="font-bold text-lg mb-2">League Creation</h3>
                <p className="text-gray-600 text-sm">Create and manage fantasy leagues</p>
              </div>
              <div className="border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition">
                <div className="text-2xl mb-3">📊</div>
                <h3 className="font-bold text-lg mb-2">Live Draft</h3>
                <p className="text-gray-600 text-sm">Real-time player draft with timer</p>
              </div>
              <div className="border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition">
                <div className="text-2xl mb-3">⚡</div>
                <h3 className="font-bold text-lg mb-2">Live Scoring</h3>
                <p className="text-gray-600 text-sm">Real-time updates during games</p>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Status Bar */}
        <div className="mt-8 p-4 bg-gray-800 text-white rounded-lg">
          <div className="flex flex-wrap items-center justify-between">
            <div className="flex items-center">
              <div className="w-2 h-2 rounded-full bg-green-500 mr-3 animate-pulse"></div>
              <span>System: Operational</span>
            </div>
            <div className="text-sm text-gray-300">
              Backend: <code className="ml-2 bg-gray-700 px-2 py-1 rounded">localhost:3001</code>
              <span className="mx-3">|</span>
              Frontend: <code className="ml-2 bg-gray-700 px-2 py-1 rounded">localhost:3000</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}