import React, { useState } from 'react';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [generatedImage, setGeneratedImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generateNFT = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5000/api/generate-nft', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate NFT');
      }

      const data = await response.json();
      setGeneratedImage(data.data[0].url);
    } catch (err) {
      setError('Error generating NFT. Please try again.');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>NFT Generator</h1>
        <p>Create unique NFT artwork using AI</p>
      </header>
      
      <main className="App-main">
        <form onSubmit={generateNFT} className="generation-form">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your NFT (e.g., 'A cosmic astronaut cat floating in space with neon colors')"
            required
            className="prompt-input"
          />
          <button type="submit" disabled={loading} className="generate-button">
            {loading ? 'Generating...' : 'Generate NFT'}
          </button>
        </form>

        {error && <div className="error-message">{error}</div>}

        {generatedImage && (
          <div className="result-container">
            <h2>Your Generated NFT</h2>
            <img src={generatedImage} alt="Generated NFT" className="generated-image" />
            <button
              onClick={() => window.open(generatedImage, '_blank')}
              className="download-button"
            >
              Open Full Size
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
