import { useState, useRef, useCallback } from "react";
import { Mic, MicOff } from "lucide-react";

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  disabled?: boolean;
}

export function AudioRecorder({ onRecordingComplete, disabled }: AudioRecorderProps) {
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        if (blob.size > 0) onRecordingComplete(blob);
      };

      mediaRecorder.start();
      setRecording(true);
    } catch {
      // Microphone permission denied — silently ignore
    }
  }, [onRecordingComplete]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }, []);

  return (
    <button
      type="button"
      disabled={disabled}
      onMouseDown={startRecording}
      onMouseUp={stopRecording}
      onMouseLeave={stopRecording}
      onTouchStart={startRecording}
      onTouchEnd={stopRecording}
      className={`relative flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
        recording
          ? "bg-red-500 text-white"
          : "text-gray-500 hover:bg-gray-100 hover:text-teal-600"
      } ${disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
      title="Maintenir pour enregistrer"
    >
      {recording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
      {recording && (
        <span className="absolute inset-0 animate-ping rounded-full bg-red-400 opacity-40" />
      )}
      {recording && (
        <div className="absolute -top-8 left-1/2 flex -translate-x-1/2 items-center gap-0.5">
          {[1, 2, 3, 4, 5].map((i) => (
            <span
              key={i}
              className="inline-block w-0.5 rounded-full bg-red-500"
              style={{
                height: `${8 + Math.random() * 10}px`,
                animation: `waveBar 0.4s ease-in-out ${i * 0.05}s infinite alternate`,
              }}
            />
          ))}
        </div>
      )}
      <style>{`
        @keyframes waveBar {
          0% { height: 6px; }
          100% { height: 18px; }
        }
      `}</style>
    </button>
  );
}
