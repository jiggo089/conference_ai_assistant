# Audio Recorder and OpenAI Integration

This project consists of two main components:

1. **Audio Recorder**: A PyQt5-based GUI application that records audio from a specified input device, processes the audio to save only the last few seconds, and then triggers an OpenAI processor to transcribe and interact with the recorded audio.

2. **OpenAI Processor**: A script that processes the audio file, transcribes it using OpenAI's Whisper model, and interacts with OpenAI's GPT-4 model to generate responses based on the transcription.

## Prerequisites

- **Python 3.6+**
- **PyQt5**
- **pyaudio**
- **numpy**
- **openai**
- **dotenv**
- **BlackHole** (for macOS to create an Aggregate Device)

## Setup

### Install Dependencies

```sh
pip install pyaudio numpy PyQt5 openai python-dotenv
```
## Create an Aggregate Device
- Go to Audio MIDI Setup on your Mac.
- Create an Aggregate Device that includes your desired input devices (e.g., MacBook Microphone and BlackHole).
## Setup OpenAI API Key
- Create a .env file in the root directory of the project.
## Add your OpenAI API key to the .env file:
```sh
OPENAI_API_KEY=your_openai_api_key_here
```
# Usage
Running the Audio Recorder
Start the Audio Recorder:

```sh
python audio_recorder.py
```
