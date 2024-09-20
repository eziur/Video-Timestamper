import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module='whisper')

import subprocess
import sys
import os
from whisper import load_model
import re
from datetime import timedelta

# Force UTF-8 encoding for print statements
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
my_env = os.environ.copy()
my_env["PYTHONIOENCODING"] = "utf-8"

# 1. Transcription with Whisper
def transcribe_video(video_path):
    print(f"Loading Whisper model for transcription of: {video_path}")
    model = load_model("base")
    print(f"Starting transcription for: {video_path}")
    
    # Transcribe and get detailed segment information
    result = model.transcribe(video_path, verbose=True)
    
    # Create a list to store the transcript with timestamps
    transcript_with_timestamps = []
    
    # Iterate over each segment in the transcription result
    for segment in result['segments']:
        # Get start and end time of the segment
        start_time = segment['start']
        end_time = segment['end']
        # Get the text of the segment
        text = segment['text'].strip()
        # Format the timestamp as HH:MM:SS
        formatted_start_time = str(timedelta(seconds=int(start_time)))
        formatted_end_time = str(timedelta(seconds=int(end_time)))
        # Append the line with timestamps to the transcript list
        transcript_with_timestamps.append(f"[{formatted_start_time} --> {formatted_end_time}] {text}")
    
    # Join the transcript list into a single string
    final_transcript = "\n".join(transcript_with_timestamps)
    
    print("Transcription completed successfully.")
    return final_transcript


def label_segments_llama(transcript):
    print("Generating labeled segments with LLaMA...")
    
    prompt = f"""
You are an AI assistant analyzing a transcript from a gaming VOD. Your goal is to label sections with a brief summary of what happens in each segment and provide the exact timestamps. 

**Important Instructions:**
- **Output Format:** Your output must be strictly in the following format and nothing else:
  
  [START_HR:MM:SS] [END_HR:MM:SS] Label/Description

- **Do Not Include:** Any additional text, explanations, or introductions.
- **Examples:**
  [00:02:30] [00:03:30] Player gets first kill
  [01:05:30] [01:10:25] Region of players advances in redstone technology

Now, analyze the transcript below and output the labels in the exact format specified:

{transcript}

You are an AI assistant analyzing a transcript from a gaming VOD. Your goal is to label every section of the footage with a brief summary of what happens in each segment and provide the exact timestamps. 

**Important Instructions:**
- **Output Format:** Your output must be strictly in the following format and nothing else:
  
  [START_HR:MM:SS] [END_HR:MM:SS] Label/Description

- **Do Not Include:** Any additional text, explanations, or introductions.
- **Examples:**
  [00:02:30] [00:03:30] Player gets first kill
  [01:05:30] [01:10:25] Region of players advances in redstone technology
"""
    
    # Prepare the command as a list without shell=True
    llama_command = ["ollama", "run", "llama3.1"]
    
    # Run the command and pass the prompt via stdin
    process = subprocess.Popen(
        llama_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,  # Ensures that the I/O is in text mode
        encoding='utf-8',
        errors='replace',
        env=my_env
    )
    
    # Communicate the prompt to the subprocess
    output, error = process.communicate(input=prompt)

    # Print the raw output from LLaMA to check what's being returned
    if output:
        print(f"LLaMA raw output:\n{output}")
    
    # Check for errors
    if process.returncode != 0:
        print(f"Error running LLaMA: {error}")
        return []
    
    # Ignore console mode errors if any
    if "failed to get console mode" in output or "failed to get console mode" in error:
        print("Ignoring console mode errors...")
    
    print("LLaMA labeling completed successfully.")
    
    # Parse the output from LLaMA
    return parse_llama_output(output)

def parse_llama_output(output):
    chapters = []
    # Patterns to match different formats
    pattern_arrow = re.compile(r'\[(\d+:\d{2}:\d{2})\s*-->\s*(\d+:\d{2}:\d{2})\]\s*(.*)')
    pattern_brackets = re.compile(r'\[(\d+:\d{2}:\d{2})\]\s*\[(\d+:\d{2}:\d{2})\]\s*(.*)')
    pattern_single = re.compile(r'\[(\d+:\d{2}:\d{2})\]\s*(.*)')

    # Split the output into lines
    for line in output.strip().split('\n'):
        line = line.strip()
        match = pattern_arrow.match(line)
        if match:
            start_str, end_str, label = match.groups()
        else:
            match = pattern_brackets.match(line)
            if match:
                start_str, end_str, label = match.groups()
            else:
                match = pattern_single.match(line)
                if match:
                    start_str = match.group(1)
                    end_str = start_str  # No end time provided
                    label = match.group(2).strip()
                else:
                    # Line didn't match any pattern; skip it
                    continue

        # Convert "H:MM:SS" to seconds
        def hms_to_seconds(hms_str):
            parts = hms_str.strip().split(':')
            parts = [int(p) for p in parts]
            while len(parts) < 3:
                parts.insert(0, 0)  # Pad with zeros if necessary
            hours, minutes, seconds = parts
            return hours * 3600 + minutes * 60 + seconds

        start_sec = hms_to_seconds(start_str)
        end_sec = hms_to_seconds(end_str)

        # Store each chapter
        chapters.append({
            "start": start_sec,
            "end": end_sec,
            "label": label.strip()
        })

    return chapters



# 4. Skip silent periods (optional for speeding up transcription)
def skip_silence_in_transcription(transcript):
    print("Skipping silent periods if applicable...")
    return transcript

# 5. Add chapters to video metadata using FFmpeg without re-encoding

def add_chapters_to_video(video_path, chapters):
    import os

    print(f"Extracting metadata from: {video_path}")

    # Extract metadata to 'metadata.txt'
    extract_metadata_cmd = ['ffmpeg', '-y', '-i', video_path, '-f', 'ffmetadata', 'metadata.txt']

    # Run FFmpeg command and capture output
    extract_process = subprocess.Popen(extract_metadata_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=my_env)
    stdout, stderr = extract_process.communicate()

    if extract_process.returncode != 0:
        print(f"Error extracting metadata:\n{stderr}")
        return

    print("Building chapter metadata...")
    with open("metadata.txt", "a", encoding='utf-8') as f:
        for chapter in chapters:
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(chapter['start'] * 1000)}\nEND={int(chapter['end'] * 1000)}\ntitle={chapter['label']}\n")

    print("Adding metadata back into the video...")

    # Generate output file path
    base, ext = os.path.splitext(video_path)
    output_video_path = f"{base}_with_chapters{ext}"

    add_metadata_cmd = ['ffmpeg', '-y', '-i', video_path, '-i', 'metadata.txt', '-map_metadata', '1', '-codec', 'copy', output_video_path]

    # Run FFmpeg command to add metadata
    add_process = subprocess.Popen(add_metadata_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=my_env)
    stdout, stderr = add_process.communicate()

    if add_process.returncode != 0:
        print(f"Error adding metadata:\n{stderr}")
        return

    print(f"Chapters successfully added to: {output_video_path}")



def process_video(video_path):
    print(f"Processing video: {video_path}")

    # 1. Transcribe the video
    transcript = transcribe_video(video_path)

    # 2. Use LLaMA to generate labels with timestamps
    chapters = label_segments_llama(transcript)

    if chapters:
        print("Labeled segments generated. Proceeding to add chapters to video.")
        add_chapters_to_video(video_path, chapters)
        print("Video processing complete.")
    else:
        print("No chapters generated. Video processing terminated.")



# Keeping the original main block
if __name__ == "__main__":
    import sys
    video_file_path = sys.argv[1]
   
    print(f"Video file path received: {video_file_path}")

    process_video(video_file_path)
