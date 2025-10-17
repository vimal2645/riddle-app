import React, { useState, useEffect } from 'react';
import api from '../api/axios';

function Riddle({ language, setLanguage }) {
  const [riddle, setRiddle] = useState(null);
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ solved: 0, correct: 0, streak: 0 });

  const fetchRiddle = async () => {
    setLoading(true);
    setFeedback(null);
    setAnswer('');

    try {
      const response = await api.get(`/riddle?language=${language}`);
      setRiddle(response.data);
    } catch (err) {
      console.error('Failed to fetch riddle:', err);
    } finally {
      setLoading(false);
    }
  };

  const checkAnswer = async () => {
    if (!answer.trim()) return;

    try {
      const response = await api.post('/check', {
        riddle_id: riddle.id,
        answer: answer,
      });

      setFeedback(response.data);
      setStats(response.data.stats);

      if (response.data.correct) {
        setTimeout(() => fetchRiddle(), 2000);
      }
    } catch (err) {
      console.error('Failed to check answer:', err);
    }
  };

  useEffect(() => {
    fetchRiddle();
  }, [language]);

  return (
    <div className="riddle-container">
      <div className="header">
        <h1>🧩 Riddle App</h1>
        <div className="stats-bar">
          <span>✅ Solved: {stats.solved}</span>
          <span>🎯 Correct: {stats.correct}</span>
          <span>🔥 Streak: {stats.streak}</span>
        </div>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="language-select"
        >
          <option value="en">English</option>
          <option value="hi">हिंदी</option>
        </select>
      </div>

      {loading ? (
        <div className="loading">Loading riddle...</div>
      ) : riddle ? (
        <div className="riddle-card">
          <div className="riddle-badge">{riddle.difficulty}</div>
          <h2>{riddle.question}</h2>

          {riddle.hints && riddle.hints.length > 0 && (
            <div className="hints">
              <h4>💡 Hints:</h4>
              {riddle.hints.map((hint, i) => (
                <p key={i}>• {hint}</p>
              ))}
            </div>
          )}

          <div className="answer-section">
            <input
              type="text"
              placeholder="Type your answer..."
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && checkAnswer()}
              disabled={feedback?.correct}
            />
            <button onClick={checkAnswer} disabled={feedback?.correct}>
              Submit
            </button>
          </div>

          {feedback && (
            <div className={`feedback ${feedback.correct ? 'correct' : 'wrong'}`}>
              <p>{feedback.message}</p>
              {!feedback.correct && feedback.answer && (
                <p>
                  <strong>Correct answer:</strong> {feedback.answer}
                </p>
              )}
            </div>
          )}

          <button className="next-btn" onClick={fetchRiddle}>
            Next Riddle →
          </button>
        </div>
      ) : (
        <p>No riddles available</p>
      )}
    </div>
  );
}

export default Riddle;
