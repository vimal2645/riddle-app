import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = 'https://riddle-app-vimal26457915-0xllqh47.leapcell.dev';


function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [riddle, setRiddle] = useState(null);
  const [answer, setAnswer] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [category, setCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [activeTab, setActiveTab] = useState('riddle'); // riddle, leaderboard, daily, multiplayer, profile
  
  // Auth states
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Leaderboard
  const [leaderboard, setLeaderboard] = useState([]);
  
  // Daily Challenge
  const [dailyChallenge, setDailyChallenge] = useState(null);
  
  // Multiplayer
  const [rooms, setRooms] = useState([]);
  const [roomName, setRoomName] = useState('');

  useEffect(() => {
    if (token) {
      fetchProfile();
      fetchCategories();
    }
  }, [token]);

  const axiosConfig = {
    headers: { Authorization: `Bearer ${token}` }
  };

  // Auth Functions
  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const endpoint = isLogin ? '/login' : '/signup';
      const data = isLogin 
        ? { email, password }
        : { username, email, password, language };
      
      const response = await axios.post(`${API_URL}${endpoint}`, data);
      
      setToken(response.data.token);
      localStorage.setItem('token', response.data.token);
      setMessage(`Welcome ${isLogin ? '' : username}!`);
      fetchProfile();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error');
    }
    
    setLoading(false);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    setActiveTab('riddle');
  };

  // Profile
  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API_URL}/profile`, axiosConfig);
      setUser(response.data);
    } catch (error) {
      console.error('Profile error:', error);
    }
  };

  // Categories
  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/categories`);
      setCategories(response.data.categories);
    } catch (error) {
      console.error('Categories error:', error);
    }
  };

  // Riddle Functions
  const fetchRiddle = async () => {
    setLoading(true);
    setMessage('');
    setAnswer('');
    
    try {
      const params = { language };
      if (category) params.category = category;
      
      const response = await axios.get(`${API_URL}/riddle`, {
        ...axiosConfig,
        params
      });
      
      setRiddle(response.data);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error fetching riddle');
    }
    
    setLoading(false);
  };

  const checkAnswer = async () => {
    if (!answer.trim()) {
      setMessage('Please enter an answer');
      return;
    }
    
    setLoading(true);
    
    try {
      const response = await axios.post(
        `${API_URL}/check`,
        { riddle_id: riddle.id, answer },
        axiosConfig
      );
      
      setMessage(response.data.message);
      
      if (response.data.correct) {
        setTimeout(() => fetchRiddle(), 2000);
      }
      
      fetchProfile(); // Update stats
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error checking answer');
    }
    
    setLoading(false);
  };

  // Leaderboard
  const fetchLeaderboard = async () => {
    try {
      const response = await axios.get(`${API_URL}/leaderboard`);
      setLeaderboard(response.data.leaderboard);
    } catch (error) {
      console.error('Leaderboard error:', error);
    }
  };

  // Daily Challenge
  const fetchDailyChallenge = async () => {
    try {
      const response = await axios.get(`${API_URL}/daily-challenge`, axiosConfig);
      setDailyChallenge(response.data);
    } catch (error) {
      console.error('Daily challenge error:', error);
    }
  };

  const answerDailyChallenge = async () => {
    if (!answer.trim()) return;
    
    setLoading(true);
    
    try {
      const response = await axios.post(
        `${API_URL}/daily-challenge/answer`,
        { answer },
        axiosConfig
      );
      
      setMessage(response.data.message);
      fetchProfile();
      fetchDailyChallenge();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error');
    }
    
    setLoading(false);
  };

  // Multiplayer
  const fetchRooms = async () => {
    try {
      const response = await axios.get(`${API_URL}/multiplayer/rooms`);
      setRooms(response.data.rooms);
    } catch (error) {
      console.error('Rooms error:', error);
    }
  };

  const createRoom = async () => {
    if (!roomName.trim()) return;
    
    try {
      const response = await axios.post(
        `${API_URL}/multiplayer/create`,
        { room_name: roomName, max_players: 5 },
        axiosConfig
      );
      
      setMessage(response.data.message);
      setRoomName('');
      fetchRooms();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error creating room');
    }
  };

  const joinRoom = async (roomId) => {
    try {
      const response = await axios.post(
        `${API_URL}/multiplayer/join`,
        { room_id: roomId },
        axiosConfig
      );
      
      setMessage(response.data.message);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error joining room');
    }
  };

  const shareRiddle = async () => {
    if (!riddle) return;
    
    try {
      const response = await axios.post(
        `${API_URL}/share`,
        { riddle_id: riddle.id },
        axiosConfig
      );
      
      setMessage('Riddle shared! 📤');
    } catch (error) {
      setMessage('Error sharing riddle');
    }
  };

  // Switch tabs
  useEffect(() => {
    if (activeTab === 'leaderboard') fetchLeaderboard();
    if (activeTab === 'daily') fetchDailyChallenge();
    if (activeTab === 'multiplayer') fetchRooms();
  }, [activeTab]);

  // Login/Signup Screen
  if (!token) {
    return (
      <div className="app">
        <div className="auth-container">
          <h1>🧩 Riddle App</h1>
          
          <div className="auth-tabs">
            <button 
              className={isLogin ? 'active' : ''} 
              onClick={() => setIsLogin(true)}
            >
              Login
            </button>
            <button 
              className={!isLogin ? 'active' : ''} 
              onClick={() => setIsLogin(false)}
            >
              Signup
            </button>
          </div>
          
          <form onSubmit={handleAuth}>
            {!isLogin && (
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            )}
            
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            
            {!isLogin && (
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="en">English</option>
                <option value="hi">हिंदी</option>
              </select>
            )}
            
            <button type="submit" disabled={loading}>
              {loading ? 'Loading...' : (isLogin ? 'Login' : 'Signup')}
            </button>
          </form>
          
          {message && <p className="message">{message}</p>}
        </div>
      </div>
    );
  }

  // Main App Screen
  return (
    <div className="app">
      {/* Navigation */}
      <nav className="navbar">
        <h1>🧩 Riddle App</h1>
        <div className="nav-buttons">
          <button onClick={() => setActiveTab('riddle')} className={activeTab === 'riddle' ? 'active' : ''}>
            🎯 Riddles
          </button>
          <button onClick={() => setActiveTab('daily')} className={activeTab === 'daily' ? 'active' : ''}>
            📅 Daily
          </button>
          <button onClick={() => setActiveTab('leaderboard')} className={activeTab === 'leaderboard' ? 'active' : ''}>
            🏆 Leaderboard
          </button>
          <button onClick={() => setActiveTab('multiplayer')} className={activeTab === 'multiplayer' ? 'active' : ''}>
            👥 Multiplayer
          </button>
          <button onClick={() => setActiveTab('profile')} className={activeTab === 'profile' ? 'active' : ''}>
            👤 Profile
          </button>
          <button onClick={logout}>Logout</button>
        </div>
      </nav>

      {/* Riddles Tab */}
      {activeTab === 'riddle' && (
        <div className="container">
          <div className="controls">
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="en">English</option>
              <option value="hi">हिंदी</option>
            </select>
            
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat.name} value={cat.name}>
                  {cat.name} ({cat.count})
                </option>
              ))}
            </select>
            
            <button onClick={fetchRiddle} disabled={loading}>
              {riddle ? 'Next Riddle' : 'Start'}
            </button>
          </div>

          {riddle && (
            <div className="riddle-card">
              <div className="riddle-header">
                <span className="category">{riddle.category}</span>
                <span className="difficulty">{riddle.difficulty}</span>
              </div>
              
              <h2 className="riddle-question">{riddle.question}</h2>
              
              <div className="answer-section">
                <input
                  type="text"
                  placeholder="Your answer..."
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && checkAnswer()}
                />
                
                <button onClick={checkAnswer} disabled={loading}>
                  Submit
                </button>
                
                <button onClick={shareRiddle} className="share-btn">
                  📤 Share
                </button>
              </div>
              
              {message && <p className="message">{message}</p>}
            </div>
          )}
        </div>
      )}

      {/* Daily Challenge Tab */}
      {activeTab === 'daily' && (
        <div className="container">
          <h2>📅 Daily Challenge</h2>
          
          {!dailyChallenge && (
            <button onClick={fetchDailyChallenge}>Load Today's Challenge</button>
          )}
          
          {dailyChallenge && (
            <div className="riddle-card">
              <div className="daily-info">
                <p>🏆 Bonus: +50 points</p>
                <p>👥 Participants: {dailyChallenge.participants}</p>
                {dailyChallenge.completed && <p>✅ Completed!</p>}
              </div>
              
              <h3>{dailyChallenge.riddle.question}</h3>
              
              {!dailyChallenge.completed && (
                <div className="answer-section">
                  <input
                    type="text"
                    placeholder="Your answer..."
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && answerDailyChallenge()}
                  />
                  
                  <button onClick={answerDailyChallenge} disabled={loading}>
                    Submit
                  </button>
                </div>
              )}
              
              {message && <p className="message">{message}</p>}
            </div>
          )}
        </div>
      )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div className="container">
          <h2>🏆 Leaderboard</h2>
          
          <div className="leaderboard">
            {leaderboard.map((player, index) => (
              <div key={index} className="leaderboard-item">
                <span className="rank">#{player.rank}</span>
                <span className="username">{player.username}</span>
                <span className="points">{player.points} pts</span>
                <span className="streak">🔥 {player.streak}</span>
                <span className="accuracy">{player.accuracy}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Multiplayer Tab */}
      {activeTab === 'multiplayer' && (
        <div className="container">
          <h2>👥 Multiplayer Rooms</h2>
          
          <div className="create-room">
            <input
              type="text"
              placeholder="Room name..."
              value={roomName}
              onChange={(e) => setRoomName(e.target.value)}
            />
            <button onClick={createRoom}>Create Room</button>
          </div>
          
          <div className="rooms-list">
            {rooms.map(room => (
              <div key={room.room_id} className="room-card">
                <h3>{room.name}</h3>
                <p>Host: {room.host}</p>
                <p>Players: {room.players}/{room.max_players}</p>
                <button onClick={() => joinRoom(room.room_id)}>Join</button>
              </div>
            ))}
          </div>
          
          {message && <p className="message">{message}</p>}
        </div>
      )}

      {/* Profile Tab */}
      {activeTab === 'profile' && user && (
        <div className="container">
          <div className="profile-card">
            <h2>👤 {user.username}</h2>
            
            <div className="profile-stats">
              <div className="stat-item">
                <span className="stat-label">Email</span>
                <span className="stat-value">{user.email}</span>
              </div>
              
              <div className="stat-item">
                <span className="stat-label">Language</span>
                <span className="stat-value">{user.language === 'en' ? 'English' : 'हिंदी'}</span>
              </div>
              
              <div className="stat-item highlight">
                <span className="stat-label">🏆 Points</span>
                <span className="stat-value">{user.points}</span>
              </div>
              
              <div className="stat-item highlight">
                <span className="stat-label">📊 Rank</span>
                <span className="stat-value">#{user.rank}</span>
              </div>
              
              <div className="stat-item">
                <span className="stat-label">Total Solved</span>
                <span className="stat-value">{user.total_solved}</span>
              </div>
              
              <div className="stat-item">
                <span className="stat-label">Correct Answers</span>
                <span className="stat-value">{user.correct_answers}</span>
              </div>
              
              <div className="stat-item">
                <span className="stat-label">Accuracy</span>
                <span className="stat-value">{user.accuracy}%</span>
              </div>
              
              <div className="stat-item">
                <span className="stat-label">Current Streak</span>
                <span className="stat-value">🔥 {user.current_streak} days</span>
              </div>
              
              <div className="stat-item">
                <span className="stat-label">Unique Riddles Seen</span>
                <span className="stat-value">{user.unique_riddles_seen}</span>
              </div>
              
              <div className="stat-item highlight">
                <span className="stat-label">📅 Daily Challenges</span>
                <span className="stat-value">{user.daily_challenges_completed}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
