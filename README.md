# VOD Labeler
Tool to help creators label sections and timestamp important moments on their VODs instead of having to spend hours reviewing footage and then going back to find clips while editing

View video chapters with VLC Player.

**To run:**
- Run the gui.py file

**Requires**
- Whisper (Audio to Text transcription)
- Llama3.1 
- FFmpeg (adding video chapters to metadata)

**Known bugs:**
- for longer VODs, the large context window (prompt) causes some hallucinations and errors with LLM output response. need to hone in prompt
- only generates timestamps for end of video for larger videos
- formatting bugs that will sometimes happen "An error occurred: 'charmap' codec can't decode byte 0x81 in position 27: character maps to <undefined>"
- gets stuck on "transcribing" for awhile sometimes

**Potential future features:**
- Ability to analyze multiple VODs at once
- more accurate labeling of sections and highlights
- Optimization of process / code for faster processing speeds
- Nicer UI / user experience
- Ability to analyze more filetypes like .mov, .mkv, .mp3
