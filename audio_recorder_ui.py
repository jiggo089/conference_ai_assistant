import sys
import pyaudio
import wave
import threading
import numpy as np
import datetime
import os
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont

# Параметры записи
FORMAT = pyaudio.paInt16
CHANNELS = 3  #  3 канала для записи
RATE = 44100
CHUNK = 1024

class SignalHandler(QObject):
    log_signal = pyqtSignal(str)
    finished = pyqtSignal(str)

class AudioRecorder(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.audio = None
        self.stream = None
        self.recording_thread = None
        self.stop_event = threading.Event()
        self.frames = deque(maxlen=int(RATE / CHUNK * 60))  
        self.is_recording = False
        self.record_seconds = 10  
        self.signal_handler = SignalHandler()
        self.signal_handler.finished.connect(self.on_finished)
        self.signal_handler.log_signal.connect(self.update_log)
        self.thread_id = None
        self.assistant_id = None

    def init_ui(self):
        self.setWindowTitle('Audio Recorder')
        layout = QVBoxLayout()

        self.start_button = QPushButton('Слушать звук', self)
        self.start_button.clicked.connect(self.start_recording)
        layout.addWidget(self.start_button)

        self.stop_10_button = QPushButton('Записать последние 10 sec', self)
        self.stop_10_button.clicked.connect(lambda: self.stop_recording(10))
        layout.addWidget(self.stop_10_button)

        self.stop_20_button = QPushButton('Записать последние 20 sec', self)
        self.stop_20_button.clicked.connect(lambda: self.stop_recording(20))
        layout.addWidget(self.stop_20_button)

        self.stop_30_button = QPushButton('Записать последние 30 sec', self)
        self.stop_30_button.clicked.connect(lambda: self.stop_recording(30))
        layout.addWidget(self.stop_30_button)

        self.stop_60_button = QPushButton('Записать последние 60 sec', self)
        self.stop_60_button.clicked.connect(lambda: self.stop_recording(60))
        layout.addWidget(self.stop_60_button)

        self.reset_button = QPushButton('Обновить ветку', self)
        self.reset_button.clicked.connect(self.reset_thread_id)
        layout.addWidget(self.reset_button)

        self.text_edit = QTextEdit(self)
        font = QFont()
        font.setPointSize(10)  
        self.text_edit.setFont(font)
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        self.setLayout(layout)
        self.show()

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.log("Recording...")
            self.stop_event.clear()
            self.frames.clear()  
            self.recording_thread = threading.Thread(target=self.record)
            self.recording_thread.start()

    def stop_recording(self, seconds):
        if self.is_recording:
            self.record_seconds = seconds
            self.log(f"Stopping recording and saving last {seconds} seconds...")
            self.stop_event.set()
            self.recording_thread.join()
            filename = self.save_to_file()
            self.is_recording = False
            self.signal_handler.finished.emit(filename)
            self.cleanup_audio()

    def reset_thread_id(self):
        self.thread_id = None
        self.assistant_id = None
        if os.path.exists('session_ids.txt'):
            os.remove('session_ids.txt')
        self.log("Thread ID and Assistant ID have been reset.")

    def record(self):
        self.audio = pyaudio.PyAudio()
        aggregate_device_index = None
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info['name'] == 'Aggregate Device':
                aggregate_device_index = i
                break
        if aggregate_device_index is None:
            self.log("Aggregate Device не найден")
            return
        self.stream = self.audio.open(format=FORMAT,
                                      channels=CHANNELS,
                                      rate=RATE,
                                      input=True,
                                      input_device_index=aggregate_device_index,
                                      frames_per_buffer=CHUNK)

        while not self.stop_event.is_set():
            data = self.stream.read(CHUNK)
            self.frames.append(data)

    def save_to_file(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
        filename = f"output_{timestamp}.wav"
        self.log(f"Saving to file {filename}...")
        self.stream.stop_stream()
        self.stream.close()

        
        maxlen = int(RATE / CHUNK * self.record_seconds)
        recent_frames = list(self.frames)[-maxlen:]

        
        mono_frames = []
        for frame in recent_frames:
           
            data = np.frombuffer(frame, dtype=np.int16)
            
            third_channel_data = data[2::CHANNELS]
           
            mono_frames.extend(third_channel_data)

       
        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)  #  1 канал для моно
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(np.array(mono_frames, dtype=np.int16).tobytes())
        wf.close()

        self.log(f"Файл сохранен как {filename}")
        return filename

    def cleanup_audio(self):
        self.audio.terminate()
        self.audio = None
        self.stream = None

    @pyqtSlot(str)
    def on_finished(self, filename):
      
        if os.path.exists('session_ids.txt'):
            with open('session_ids.txt', 'r') as f:
                ids = f.readlines()
                self.thread_id = ids[0].strip()
                self.assistant_id = ids[1].strip()

       
        import subprocess
        def log_output(pipe):
            for line in pipe:
                self.signal_handler.log_signal.emit(line.decode('utf-8'))

        if self.thread_id and self.assistant_id:
            process = subprocess.Popen(['python3', 'openai_processor.py', filename, self.thread_id, self.assistant_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(['python3', 'openai_processor.py', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        threading.Thread(target=log_output, args=(process.stdout,)).start()
        threading.Thread(target=log_output, args=(process.stderr,)).start()

    @pyqtSlot(str)
    def update_log(self, message):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(message + "\n")
        self.text_edit.setTextCursor(cursor)

    def log(self, message):
        self.signal_handler.log_signal.emit(message)

def main():
    app = QApplication(sys.argv)
    ex = AudioRecorder()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
