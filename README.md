# YouTube Video Mixer Pro 🎬 - TikTok/Reels Edition

Create professional vertical videos for TikTok and Instagram Reels from YouTube videos!

## 🚀 Features

- **Native vertical format**: Optimized 9:16 videos (1080x1920) for TikTok and Reels
- **Face recognition**: Automatically detect and prioritize a specific person
- **HD download**: Support up to 1080p+ with multiple quality modes
- **Text management**: Automatically avoid or remove logos and subtitles
- **Professional audio**: Add voiceovers, music with fade effects
- **Customization**: Logo overlay, tagline video, adaptive duration
- **Smart shuffle**: Automatic alternation between different sources

## 📱 How to Use

1. **Configuration**: Set the duration and clip parameters
2. **Face recognition** (optional): Upload a reference photo
3. **Audio** (optional): Add your voiceover or music
4. **Customization**: Add logo and/or tagline video
5. **YouTube URLs**: Paste the source video links
6. **Create**: Click "Create video" and download the result!

## 🎯 Use Cases

- TikTok/Reels content creators
- Highlight compilations
- Reaction videos with face recognition
- Synchronized music montages
- Vertical educational content

## 🛠️ Technologies

- Streamlit for the interface
- Face Recognition for facial detection
- MoviePy for video editing
- OpenCV for image processing
- yt-dlp for YouTube downloading

## 🚨 Important Notes

### Streamlit Cloud Limitations
When deployed on Streamlit Cloud (free tier), the app has these limitations:
- Memory limit: 1GB
- Timeout: 15 minutes
- Limited temporary storage

### Recommendations for Best Results
- Use short videos (< 5 min) to avoid timeouts
- Download in "standard" or "fast" quality rather than "ultra"
- Limit the number of source videos (2-3 max)
- Use short clips (3-5 seconds)

### Alternative Hosting
For better performance, consider:
- Hosting on a VPS with more resources
- Using Google Colab with a Streamlit notebook
- Running locally and sharing via ngrok

## 📋 Installation (Local)

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/youtube-video-mixer.git
cd youtube-video-mixer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the app:
```bash
streamlit run youtube_mixer.py
```

## 📄 License

This project is for educational and personal use. Please respect YouTube's Terms of Service and copyright laws when using this tool.

---
Created with ❤️ for content creators
