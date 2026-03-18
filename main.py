"""Howl - Voice-to-text desktop tool powered by Groq Whisper."""

import sys
import signal
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal, pyqtSlot

from ui.pill_widget import PillWidget
from ui.refine_widget import RefineWidget
from ui.preview_widget import PreviewWidget
from ui.refine_config_widget import RefineConfigWidget

# Delay heavy module loading to speed up UI startup
# They will be imported inside _deferred_setup


class HowlApp(QObject):
    """Main application controller. Wires hotkey -> recorder -> transcriber -> clipboard."""

    # Signal to handle transcription result on the main thread
    transcription_done = pyqtSignal(str, float)
    transcription_error = pyqtSignal(str)
    
    # Signals for refinement
    refinement_done = pyqtSignal(str, str)
    refinement_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Fast UI initialization
        self.pill = PillWidget()
        self.refine_widget = RefineWidget()
        self.refine_widget.refine_requested.connect(self._on_configure_requested, Qt.ConnectionType.QueuedConnection)
        self.config_widget = RefineConfigWidget()
        self.config_widget.generate_requested.connect(self._on_generate_requested, Qt.ConnectionType.QueuedConnection)
        self.preview_widget = PreviewWidget()
        self.preview_widget.choice_made.connect(self._on_preview_choice, Qt.ConnectionType.QueuedConnection)

        # Placeholders for deferred components
        self.recorder = None
        self.transcriber = None
        self.db = None
        self.hotkey = None

    def start(self):
        self.pill.show()
        self.pill.set_state(PillWidget.STATE_PROCESSING) # Show loading
        
        # Schedule heavy setup immediately after event loop starts
        QTimer.singleShot(100, self._deferred_setup)

    @pyqtSlot()
    def _deferred_setup(self):
        # Lazy load heavy modules
        from core.recorder import AudioRecorder
        from core.transcriber import Transcriber
        from core.hotkey import HotkeyListener
        from db.database import TranscriptionDB
        from web.server import start_web_server

        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.db = TranscriptionDB()
        self.hotkey = HotkeyListener()

        # Connect visualizer to recorder's audio queue
        self.pill.visualizer.set_audio_queue(self.recorder.audio_queue)

        # Connect hotkey signals
        self.hotkey.pressed.connect(self._on_hotkey_pressed, Qt.ConnectionType.QueuedConnection)
        self.hotkey.released.connect(self._on_hotkey_released, Qt.ConnectionType.QueuedConnection)

        # Connect transcription signals
        self.transcription_done.connect(self._on_transcription_done, Qt.ConnectionType.QueuedConnection)
        self.transcription_error.connect(self._on_transcription_error, Qt.ConnectionType.QueuedConnection)
        self.refinement_done.connect(self._on_refinement_done, Qt.ConnectionType.QueuedConnection)
        self.refinement_error.connect(self._on_refinement_error, Qt.ConnectionType.QueuedConnection)

        # Start listening
        self.hotkey.start()
        
        # Start web dashboard
        port = start_web_server(5000)
        print(f"Dashboard: http://localhost:{port}")

        self.pill.set_state(PillWidget.STATE_IDLE)
        print("Howl running. Ctrl+Shift (hold) o Ctrl-Ctrl (hands-free). Ctrl+C to quit.")

    @pyqtSlot()
    def _on_hotkey_pressed(self):
        from core.clipboard import save_frontmost_app
        save_frontmost_app()
        self.recorder.start()
        self.pill.set_state(PillWidget.STATE_RECORDING)

    @pyqtSlot()
    def _on_hotkey_released(self):
        duration = self.recorder.stop()
        self.pill.set_state(PillWidget.STATE_PROCESSING)

        # Don't transcribe very short recordings (accidental taps)
        if duration < 0.3:
            self.pill.set_state(PillWidget.STATE_IDLE)
            return

        # Transcribe in background thread to avoid blocking UI
        wav_buffer = self.recorder.get_wav_buffer()
        recording_duration = self.recorder.get_duration()
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(wav_buffer, recording_duration),
            daemon=True,
        )
        thread.start()

    def _transcribe_worker(self, wav_buffer, duration):
        try:
            text = self.transcriber.transcribe(wav_buffer)
            if text:
                self.transcription_done.emit(text, duration)
            else:
                self.transcription_error.emit("No speech detected")
        except Exception as e:
            self.transcription_error.emit(str(e))

    @pyqtSlot(str, float)
    def _on_transcription_done(self, text: str, duration: float):
        from core.clipboard import paste_text
        self.hotkey.suspend()
        # Paste text where cursor is
        paste_text(text)
        self.hotkey.resume()
        # Save to database
        self.db.insert(text=text, duration_seconds=duration)
        # Update UI
        self.pill.set_state(PillWidget.STATE_DONE)
        print(f"Transcribed ({duration:.1f}s): {text[:80]}{'...' if len(text) > 80 else ''}")
        
        # Show Refine button
        self.refine_widget.show_for_text(text)

    @pyqtSlot(str)
    def _on_transcription_error(self, error: str):
        self.pill.set_state(PillWidget.STATE_ERROR)
        print(f"Transcription error: {error}")

    @pyqtSlot(str)
    def _on_configure_requested(self, text: str):
        self.config_widget.show_for_text(text)

    @pyqtSlot(str, str, str)
    def _on_generate_requested(self, text: str, output_type: str, context: str):
        self.pill.set_state(PillWidget.STATE_PROCESSING)
        thread = threading.Thread(
            target=self._refine_worker,
            args=(text, output_type, context),
            daemon=True,
        )
        thread.start()

    def _refine_worker(self, text: str, output_type: str, context: str):
        from core.refiner import refine_prompt
        try:
            refined_text = refine_prompt(text, output_type, context)
            self.refinement_done.emit(text, refined_text)
        except Exception as e:
            self.refinement_error.emit(str(e))

    @pyqtSlot(str, str)
    def _on_refinement_done(self, original: str, refined: str):
        self.refine_widget.hide()
        self.pill.set_state(PillWidget.STATE_DONE)
        self.preview_widget.show_preview(original, refined)

    @pyqtSlot(str)
    def _on_preview_choice(self, chosen_text: str):
        if chosen_text:
            from core.clipboard import undo_and_paste_text
            self.hotkey.suspend()
            undo_and_paste_text(chosen_text)
            self.hotkey.resume()
            print("Refined text manually accepted and applied.")
        else:
            print("Original text kept. No changes applied.")

    @pyqtSlot(str)
    def _on_refinement_error(self, error: str):
        self.refine_widget.hide()
        self.pill.set_state(PillWidget.STATE_ERROR)
        print(f"Refinement error: {error}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Howl")
    app.setQuitOnLastWindowClosed(False)

    # Allow Ctrl+C to kill the app
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    howl = HowlApp()
    howl.start()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
