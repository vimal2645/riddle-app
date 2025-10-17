import React, { useState, useEffect } from 'react';
import api from '../api/axios';

function Profile({ onLogout }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.get('/profile');
      setProfile(response.data);
    } catch (err) {
      console.error('Failed to fetch profile:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading profile...</div>;

  return (
    <div className="profile-container">
      <div className="profile-card">
        <h2>👤 Profile</h2>
        {profile && (
          <>
            <div className="profile-stat">
              <strong>Username:</strong> {profile.username}
            </div>
            <div className="profile-stat">
              <strong>Email:</strong> {profile.email}
            </div>
            <div className="profile-stat">
              <strong>Language:</strong> {profile.language === 'en' ? 'English' : 'हिंदी'}
            </div>
            <hr />
            <h3>📊 Stats</h3>
            <div className="profile-stat">
              <strong>Total Solved:</strong> {profile.total_solved}
            </div>
            <div className="profile-stat">
              <strong>Correct Answers:</strong> {profile.correct_answers}
            </div>
            <div className="profile-stat">
              <strong>Accuracy:</strong> {profile.accuracy}%
            </div>
            <div className="profile-stat">
              <strong>Current Streak:</strong> 🔥 {profile.current_streak} days
            </div>
          </>
        )}
        <button className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>
    </div>
  );
}

export default Profile;
