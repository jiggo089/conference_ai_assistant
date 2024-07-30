import sys
from openai import OpenAI, AssistantEventHandler
import os
from dotenv import load_dotenv
import re


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

openai = OpenAI(api_key=api_key)
thread_id = None
assistant_id = None

class EventHandler(AssistantEventHandler):
    def __init__(self, log_func):
        super().__init__()
        self.log_func = log_func
        self.buffer = ""

    def on_text_created(self, text) -> None:
        self.log_func(f"\nassistant > {text}")

    def on_text_delta(self, delta, snapshot):
        if hasattr(delta, 'value'):
            self.buffer += delta.value
            sentences = re.split(r'(?<=[.!?]) +', self.buffer)
            for sentence in sentences[:-1]:
                self.log_func(sentence.strip())
            self.buffer = sentences[-1]

    def on_run_completed(self):
        if self.buffer:
            self.log_func(self.buffer.strip())
            self.buffer = ""

def process_audio(filename, log_func):
    global thread_id, assistant_id

    with open(filename, "rb") as audio_file:
        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    log_func(f"Transcription: {transcription.text}")
    transcription_text = transcription.text 

    
    if not isinstance(transcription_text, str):
        transcription_text = str(transcription_text)

    if thread_id is None or assistant_id is None:
       
        thread = openai.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": transcription_text  
                }
            ]
        )
        assistant = openai.beta.assistants.create(
            name="Interview Assistant",
            description="Assistant for answering interview questions.",
            model="gpt-4-turbo"
        )
        thread_id = thread.id
        assistant_id = assistant.id
      
        with open('session_ids.txt', 'w') as f:
            f.write(f"{thread_id}\n{assistant_id}\n")
    else:
        
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=transcription_text
        )

    
    with openai.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions="""
        create any instructions here
        """,
        event_handler=EventHandler(log_func),
    ) as stream:
        stream.until_done()

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python openai_processor.py <filename> [<thread_id> <assistant_id>]")
        sys.exit(1)

    filename = sys.argv[1]
    if len(sys.argv) == 4:
        thread_id = sys.argv[2]
        assistant_id = sys.argv[3]

    process_audio(filename, print)
