import { useState, useEffect, useRef, useCallback } from "react";
import { MessageCircle, Send, X, Volume2, VolumeX, Bot, User } from "lucide-react";
import { toast } from "sonner";
import { chat } from "@/lib/api";
import { AudioRecorder } from "./audio-recorder";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  buttons?: { label: string; action: string }[];
  created_at: string;
}

const LS_KEY = "optimus-chat-open";

export function ChatWidget() {
  const [open, setOpen] = useState(() => localStorage.getItem(LS_KEY) === "true");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [playingTts, setPlayingTts] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Persist open/closed state
  useEffect(() => {
    localStorage.setItem(LS_KEY, String(open));
  }, [open]);

  // Load history on first open
  useEffect(() => {
    if (!open || historyLoaded) return;
    chat
      .history(50)
      .then((history) => {
        setMessages(
          history.map((m: any) => ({
            id: m.id || crypto.randomUUID(),
            role: m.role || (m.direction === "outbound" ? "assistant" : "user"),
            content: m.content || m.message || "",
            buttons: m.buttons,
            created_at: m.created_at || new Date().toISOString(),
          })),
        );
        setHistoryLoaded(true);
      })
      .catch(() => {
        setHistoryLoaded(true);
      });
  }, [open, historyLoaded]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // Focus input when opened
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };
      addMessage(userMsg);
      setInput("");
      setSending(true);

      try {
        const res = await chat.send(trimmed);
        const assistantMsg: ChatMessage = {
          id: res.id || crypto.randomUUID(),
          role: "assistant",
          content: res.response || res.content || res.message || "",
          buttons: res.buttons,
          created_at: res.created_at || new Date().toISOString(),
        };
        addMessage(assistantMsg);
      } catch (err: any) {
        toast.error(err.message || "Erreur lors de l'envoi du message");
      } finally {
        setSending(false);
      }
    },
    [sending, addMessage],
  );

  const handleVoice = useCallback(
    async (blob: Blob) => {
      if (sending) return;
      setSending(true);

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: "🎤 Message vocal",
        created_at: new Date().toISOString(),
      };
      addMessage(userMsg);

      try {
        const res = await chat.sendVoice(blob);
        const assistantMsg: ChatMessage = {
          id: res.id || crypto.randomUUID(),
          role: "assistant",
          content: res.response || res.content || res.message || "",
          buttons: res.buttons,
          created_at: res.created_at || new Date().toISOString(),
        };
        addMessage(assistantMsg);
      } catch (err: any) {
        toast.error(err.message || "Erreur lors de l'envoi vocal");
      } finally {
        setSending(false);
      }
    },
    [sending, addMessage],
  );

  const handleTts = useCallback(
    async (messageId: string, text: string) => {
      if (playingTts === messageId) {
        setPlayingTts(null);
        return;
      }
      try {
        setPlayingTts(messageId);
        const blob = await chat.tts(text);
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => {
          setPlayingTts(null);
          URL.revokeObjectURL(url);
        };
        audio.play();
      } catch {
        setPlayingTts(null);
        toast.error("Synthese vocale indisponible");
      }
    },
    [playingTts],
  );

  const handleButtonAction = useCallback(
    (action: string) => {
      sendMessage(action);
    },
    [sendMessage],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  // ── Collapsed bubble ──
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-teal-600 text-white shadow-lg transition-transform hover:scale-110 hover:bg-teal-700"
        title="Ouvrir le chat Optimus AI"
      >
        <MessageCircle className="h-6 w-6" />
      </button>
    );
  }

  // ── Expanded panel ──
  return (
    <div className="fixed bottom-6 right-6 z-50 flex h-[600px] w-[400px] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between bg-teal-600 px-4 py-3 text-white">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          <span className="font-semibold">Optimus AI</span>
        </div>
        <button
          onClick={() => setOpen(false)}
          className="rounded-full p-1 transition-colors hover:bg-teal-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && !sending && (
          <div className="flex h-full flex-col items-center justify-center text-center text-gray-400">
            <Bot className="mb-2 h-10 w-10 text-teal-300" />
            <p className="text-sm">Bonjour ! Comment puis-je vous aider ?</p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className={`flex max-w-[85%] gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              {/* Avatar */}
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                  msg.role === "user" ? "bg-teal-100 text-teal-700" : "bg-gray-100 text-gray-600"
                }`}
              >
                {msg.role === "user" ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
              </div>

              {/* Bubble */}
              <div>
                <div
                  className={`rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-teal-600 text-white"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {/* Action buttons */}
                {msg.buttons && msg.buttons.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {msg.buttons.map((btn, i) => (
                      <button
                        key={i}
                        onClick={() => handleButtonAction(btn.action)}
                        className="rounded-full border border-teal-200 bg-white px-3 py-1 text-xs font-medium text-teal-700 transition-colors hover:bg-teal-50"
                      >
                        {btn.label}
                      </button>
                    ))}
                  </div>
                )}

                {/* TTS button for assistant messages */}
                {msg.role === "assistant" && (
                  <button
                    onClick={() => handleTts(msg.id, msg.content)}
                    className="mt-1 text-gray-400 transition-colors hover:text-teal-600"
                    title="Ecouter"
                  >
                    {playingTts === msg.id ? (
                      <VolumeX className="h-3.5 w-3.5" />
                    ) : (
                      <Volume2 className="h-3.5 w-3.5" />
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {sending && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-gray-600">
                <Bot className="h-3.5 w-3.5" />
              </div>
              <div className="flex gap-1 rounded-2xl bg-gray-100 px-4 py-3">
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "0ms" }} />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "150ms" }} />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 px-3 py-2">
        <div className="flex items-center gap-1.5">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Tapez votre message..."
            disabled={sending}
            className="flex-1 rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-sm outline-none transition-colors focus:border-teal-400 focus:bg-white disabled:opacity-50"
          />
          <AudioRecorder onRecordingComplete={handleVoice} disabled={sending} />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || sending}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-600 text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
