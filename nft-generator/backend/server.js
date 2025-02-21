const express = require('express');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

const app = express();
const port = 5000;

app.use(cors());
app.use(express.json());

// Endpoint to generate NFT image using OpenRouter
app.post('/api/generate-nft', async (req, res) => {
    try {
        const { prompt } = req.body;
        
        if (!prompt) {
            return res.status(400).json({ error: 'Prompt is required' });
        }

        const response = await axios.post('https://openrouter.ai/api/v1/images/generate', {
            model: "stabilityai/stable-diffusion-xl",
            prompt: prompt,
            num_outputs: 1,
            width: 1024,
            height: 1024
        }, {
            headers: {
                'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
                'Content-Type': 'application/json',
                'HTTP-Referer': 'http://localhost:3000',
                'X-Title': 'NFT Generator'
            }
        });

        if (response.data && response.data.images && response.data.images[0]) {
            res.json({ data: [{ url: response.data.images[0] }] });
        } else {
            throw new Error('Invalid response format from OpenRouter');
        }
    } catch (error) {
        console.error('Error generating NFT:', error.response?.data || error.message);
        const errorMessage = error.response?.data?.error || error.message || 'Failed to generate NFT';
        res.status(500).json({ error: errorMessage });
    }
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
