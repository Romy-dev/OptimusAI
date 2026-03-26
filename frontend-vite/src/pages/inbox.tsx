
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import {
  Search, Send, User, Clock, AlertTriangle, CheckCircle2,
  Bot, Phone, MessageCircle, Sparkles, ArrowUpRight, Loader2, Inbox,
  XCircle, UserCheck, X, Zap, Copy, ChevronRight, MessageSquare,
  BookOpen, Lightbulb, ArrowRight, CornerDownLeft,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import {
  conversations as convApi,
  knowledge as knowledgeApi,
  brands as brandsApi,
  Conversation,
  Message,
} from "@/lib/api";
import { ChatBubbleSkeleton, ListItemSkeleton } from "@/components/ui/skeleton";

// ── Constants ──

const QUICK_REPLIES = [
  { label: "Merci", text: "Merci pour votre message ! Nous sommes ravis de vous aider." },
  { label: "En cours", text: "Votre demande est en cours de traitement. Nous reviendrons vers vous rapidement." },
  { label: "Transfert", text: "Je vais transf\u00e9rer votre conversation \u00e0 un agent sp\u00e9cialis\u00e9 qui pourra mieux vous assister." },
  { label: "D\u00e9sol\u00e9", text: "Nous sommes d\u00e9sol\u00e9s pour ce d\u00e9sagr\u00e9ment. Laissez-nous corriger cela pour vous." },
  { label: "Horaires", text: "Nos horaires d'ouverture sont du lundi au vendredi, de 8h \u00e0 18h (GMT)." },
];

const STATUS_FILTERS = [
  { key: "all", label: "Tous" },
  { key: "escalated", label: "Urgents" },
  { key: "ai_handling", label: "IA" },
  { key: "open", label: "Ouverts" },
  { key: "human_handling", label: "Humain" },
  { key: "resolved", label: "R\u00e9solus" },
];

const statusCfg: Record<string, { label: string; color: string; dotColor: string; icon: React.ElementType }> = {
  open:              { label: "Ouvert",         color: "bg-emerald-50 text-emerald-700 ring-emerald-200",   dotColor: "bg-emerald-500", icon: Clock },
  ai_handling:       { label: "IA",             color: "bg-amber-50 text-amber-700 ring-amber-200",        dotColor: "bg-amber-500",   icon: Bot },
  escalated:         { label: "Escalad\u00e9",  color: "bg-red-50 text-red-600 ring-red-200",              dotColor: "bg-red-500",     icon: AlertTriangle },
  resolved:          { label: "R\u00e9solu",    color: "bg-emerald-50 text-emerald-600 ring-emerald-200",  dotColor: "bg-emerald-500", icon: CheckCircle2 },
  closed:            { label: "Ferm\u00e9",     color: "bg-gray-100 text-gray-500 ring-gray-200",          dotColor: "bg-gray-400",    icon: CheckCircle2 },
  human_handling:    { label: "Humain",         color: "bg-blue-50 text-blue-600 ring-blue-200",           dotColor: "bg-blue-500",    icon: UserCheck },
  waiting_customer:  { label: "Attente client", color: "bg-gray-100 text-gray-500 ring-gray-200",          dotColor: "bg-gray-400",    icon: Clock },
};

// ── Helpers ──

const platformIcon = (p: string) =>
  p === "whatsapp"
    ? <Phone className="h-3.5 w-3.5 text-emerald-500" />
    : <MessageCircle className="h-3.5 w-3.5 text-sky-500" />;

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function formatMessageTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }
  if (diffDays === 1) {
    return `Hier ${date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`;
  }
  if (diffDays < 7) {
    return date.toLocaleDateString("fr-FR", { weekday: "short", hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function formatConversationTime(dateStr?: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  if (diffDays === 1) return "Hier";
  if (diffDays < 7) return date.toLocaleDateString("fr-FR", { weekday: "short" });
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

// ── Typing Indicator Component ──

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-white border border-gray-100 px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-brand-400 animate-bounce [animation-delay:0ms]" />
          <span className="h-2 w-2 rounded-full bg-brand-400 animate-bounce [animation-delay:150ms]" />
          <span className="h-2 w-2 rounded-full bg-brand-400 animate-bounce [animation-delay:300ms]" />
        </div>
        <span className="ml-1.5 text-xs text-gray-400">IA en r\u00e9flexion...</span>
      </div>
    </div>
  );
}

// ── Confidence Bar ──

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const barColor = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-gray-100 overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", barColor)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-medium text-gray-500 tabular-nums">{pct}%</span>
    </div>
  );
}

// ── Status Dot ──

function StatusDot({ status }: { status: string }) {
  const cfg = statusCfg[status] || statusCfg.open;
  const isPulsing = status === "open" || status === "ai_handling" || status === "escalated";
  return (
    <span className="relative flex h-2.5 w-2.5">
      {isPulsing && (
        <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-50", cfg.dotColor)} />
      )}
      <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", cfg.dotColor)} />
    </span>
  );
}

// ── Main Component ──

export default function InboxPage() {
  const { data: convList, loading, refetch } = useApi(() => convApi.list(), []);
  const { data: brandList } = useApi(() => brandsApi.list(), []);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [msgsLoading, setMsgsLoading] = useState(false);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [filter, setFilter] = useState("all");
  const [searchText, setSearchText] = useState("");
  const [closing, setClosing] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [showMobileChat, setShowMobileChat] = useState(false);

  // AI suggestion state
  type SuggestionResult = { content: string; score: number; document_title: string; section_title?: string };
  const [suggestions, setSuggestions] = useState<SuggestionResult[]>([]);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [aiProcessing, setAiProcessing] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const brandId = brandList?.[0]?.id;
  const debouncedSearch = useDebounce(searchText, 300);

  // Auto-select first conversation
  useEffect(() => {
    if (convList && convList.length > 0 && !selectedId) setSelectedId(convList[0].id);
  }, [convList]);

  // Fetch messages when conversation changes
  useEffect(() => {
    if (!selectedId) return;
    setMsgsLoading(true);
    setSuggestions([]);
    convApi
      .messages(selectedId)
      .then(setMessages)
      .catch(() => {
        setMessages([]);
        toast.error("Impossible de charger les messages");
      })
      .finally(() => setMsgsLoading(false));
  }, [selectedId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, aiProcessing]);

  // Fetch AI suggestions when messages load
  useEffect(() => {
    if (!messages.length || !brandId) return;
    const lastInbound = [...messages].reverse().find((m) => m.direction === "inbound");
    if (!lastInbound) return;
    setSuggestionLoading(true);
    knowledgeApi
      .search({ query: lastInbound.content, brand_id: brandId, min_score: 0.01 })
      .then((res) => {
        if (res.results.length > 0) {
          setSuggestions(
            res.results.slice(0, 3).map((r) => ({
              content: r.content,
              score: r.score,
              document_title: r.document_title,
              section_title: r.section_title,
            }))
          );
        } else {
          setSuggestions([]);
        }
      })
      .catch(() => setSuggestions([]))
      .finally(() => setSuggestionLoading(false));
  }, [messages, brandId]);

  const handleSend = useCallback(async () => {
    if (!reply.trim() || !selectedId) return;
    setSending(true);
    setAiProcessing(true);
    try {
      await convApi.sendMessage(selectedId, reply);
      setReply("");
      toast.success("Message envoy\u00e9");
      const msgs = await convApi.messages(selectedId);
      setMessages(msgs);
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de l'envoi du message");
    } finally {
      setSending(false);
      setAiProcessing(false);
    }
  }, [reply, selectedId]);

  const handleUseSuggestion = useCallback((text: string) => {
    setReply(text);
    inputRef.current?.focus();
    toast.info("Suggestion ajout\u00e9e au champ de r\u00e9ponse");
  }, []);

  const handleCopySuggestion = useCallback((text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success("Copi\u00e9 dans le presse-papiers");
    });
  }, []);

  const handleQuickReply = useCallback((text: string) => {
    setReply(text);
    inputRef.current?.focus();
  }, []);

  const handleClose = useCallback(async () => {
    if (!selectedId) return;
    setClosing(true);
    try {
      await convApi.close(selectedId);
      toast.success("Conversation ferm\u00e9e");
      refetch();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de la fermeture");
    } finally {
      setClosing(false);
    }
  }, [selectedId, refetch]);

  const handleEscalate = useCallback(async () => {
    if (!selectedId) return;
    setEscalating(true);
    try {
      await convApi.escalate(selectedId);
      toast.success("Conversation escalad\u00e9e vers un agent humain");
      refetch();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de l'escalade");
    } finally {
      setEscalating(false);
    }
  }, [selectedId, refetch]);

  const handleSelectConversation = useCallback((id: string) => {
    setSelectedId(id);
    setShowMobileChat(true);
  }, []);

  const conversations = convList ?? [];

  const filtered = useMemo(() => {
    let list = filter === "all" ? conversations : conversations.filter((c) => c.status === filter);
    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase();
      list = list.filter((c) => (c.customer_name || "").toLowerCase().includes(q));
    }
    return list;
  }, [conversations, filter, debouncedSearch]);

  const selected = conversations.find((c) => c.id === selectedId);

  // ── Render ──

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-white">
      {/* ================================================================ */}
      {/* LEFT: Conversation List                                          */}
      {/* ================================================================ */}
      <div
        className={cn(
          "flex w-full flex-col border-r border-gray-100 bg-gray-50/50 md:w-80 lg:w-96",
          showMobileChat && "hidden md:flex",
        )}
      >
        {/* Search & Filters */}
        <div className="border-b border-gray-100 p-3 space-y-2.5">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Rechercher un client..."
              className="input-base pl-9 bg-white"
            />
            {searchText && (
              <button
                onClick={() => setSearchText("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500 transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <div className="flex gap-1 flex-wrap">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={cn(
                  "rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all duration-150",
                  filter === f.key
                    ? "bg-brand-500 text-white shadow-sm shadow-brand-200"
                    : "text-gray-500 hover:bg-gray-200/60",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="space-y-0">
              {Array.from({ length: 6 }).map((_, i) => (
                <ListItemSkeleton key={i} />
              ))}
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="flex flex-col items-center py-16 text-center px-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-100">
                <Inbox className="h-6 w-6 text-gray-300" />
              </div>
              <p className="mt-3 text-sm font-medium text-gray-500">
                {debouncedSearch ? "Aucun r\u00e9sultat" : "Aucune conversation"}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                {debouncedSearch
                  ? `Aucun client ne correspond \u00e0 "${debouncedSearch}"`
                  : "Les nouvelles conversations appara\u00eetront ici"
                }
              </p>
            </div>
          )}

          {filtered.map((conv) => {
            const st = statusCfg[conv.status] || statusCfg.open;
            const active = selectedId === conv.id;
            return (
              <button
                key={conv.id}
                onClick={() => handleSelectConversation(conv.id)}
                className={cn(
                  "flex w-full items-start gap-3 px-4 py-3.5 text-left transition-all duration-150 border-b border-gray-100/80",
                  active
                    ? "bg-brand-50/70 border-l-2 border-l-brand-500"
                    : "hover:bg-gray-100/50 border-l-2 border-l-transparent",
                )}
              >
                {/* Avatar */}
                <div className="relative shrink-0">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200 text-gray-500">
                    <User className="h-4 w-4" />
                  </div>
                  <div className="absolute -bottom-0.5 -right-0.5 rounded-full bg-white p-0.5">
                    {platformIcon(conv.platform)}
                  </div>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className={cn("text-sm truncate", active ? "font-semibold text-gray-900" : "font-medium text-gray-700")}>
                      {conv.customer_name || "Client"}
                    </span>
                    <span className="text-[11px] text-gray-400 shrink-0 tabular-nums">
                      {formatConversationTime(conv.last_message_at)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-400 truncate">
                    {conv.message_count} msg · {conv.platform}
                  </p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <StatusDot status={conv.status} />
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset",
                        st.color,
                      )}
                    >
                      <st.icon className="h-3 w-3" />
                      {st.label}
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ================================================================ */}
      {/* CENTER: Chat Area                                                */}
      {/* ================================================================ */}
      <div
        className={cn(
          "flex flex-1 flex-col min-w-0",
          !showMobileChat && "hidden md:flex",
        )}
      >
        {!selected ? (
          /* ── Empty State ── */
          <div className="flex flex-1 items-center justify-center text-center px-8">
            <div className="max-w-sm">
              {/* Illustration */}
              <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-brand-50 to-brand-100/50">
                <MessageSquare className="h-10 w-10 text-brand-500" />
              </div>

              <h3 className="text-lg font-semibold text-gray-800">
                Bienvenue dans votre bo\u00eete de r\u00e9ception
              </h3>
              <p className="mt-2 text-sm text-gray-500 leading-relaxed">
                S\u00e9lectionnez une conversation pour commencer \u00e0 r\u00e9pondre \u00e0 vos clients.
              </p>

              {/* Tips */}
              <div className="mt-8 space-y-3 text-left">
                {[
                  { icon: Zap, text: "L'IA r\u00e9pond automatiquement aux questions fr\u00e9quentes" },
                  { icon: BookOpen, text: "Enrichissez la base de connaissances pour de meilleures r\u00e9ponses" },
                  { icon: Lightbulb, text: "Utilisez les r\u00e9ponses rapides pour gagner du temps" },
                ].map((tip, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-xl bg-gray-50 p-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white shadow-sm">
                      <tip.icon className="h-4 w-4 text-brand-500" />
                    </div>
                    <p className="text-sm text-gray-600 leading-snug pt-1">{tip.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* ── Chat Header ── */}
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 bg-white/80 backdrop-blur-sm">
              <div className="flex items-center gap-3">
                {/* Mobile back button */}
                <button
                  onClick={() => setShowMobileChat(false)}
                  className="mr-1 rounded-lg p-1.5 hover:bg-gray-100 md:hidden"
                >
                  <ChevronRight className="h-5 w-5 text-gray-400 rotate-180" />
                </button>

                <div className="relative">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-200">
                    <User className="h-4 w-4 text-gray-500" />
                  </div>
                  <div className="absolute -bottom-0.5 -right-0.5">
                    <StatusDot status={selected.status} />
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">
                    {selected.customer_name || "Client"}
                  </h3>
                  <div className="flex items-center gap-1.5 text-xs text-gray-400">
                    {platformIcon(selected.platform)}
                    <span>{selected.platform}</span>
                    <span className="text-gray-200">|</span>
                    <span>{selected.message_count} messages</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "hidden sm:inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset",
                    (statusCfg[selected.status] || statusCfg.open).color,
                  )}
                >
                  {(statusCfg[selected.status] || statusCfg.open).label}
                </span>
                {selected.status !== "closed" && selected.status !== "resolved" && (
                  <>
                    <button
                      onClick={handleEscalate}
                      disabled={escalating}
                      className="btn-ghost text-xs py-1.5 text-amber-600 hover:bg-amber-50"
                      title="Escalader vers un agent humain"
                    >
                      {escalating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                      <span className="hidden sm:inline ml-1">Escalader</span>
                    </button>
                    <button
                      onClick={handleClose}
                      disabled={closing}
                      className="btn-ghost text-xs py-1.5 text-emerald-600 hover:bg-emerald-50"
                      title="Fermer la conversation"
                    >
                      {closing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                      <span className="hidden sm:inline ml-1">Fermer</span>
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* ── Message Area ── */}
            <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4 bg-gradient-to-b from-gray-50/50 to-white/30">
              {msgsLoading && (
                <div className="space-y-4">
                  <ChatBubbleSkeleton direction="inbound" />
                  <ChatBubbleSkeleton direction="outbound" />
                  <ChatBubbleSkeleton direction="inbound" />
                  <ChatBubbleSkeleton direction="outbound" />
                </div>
              )}

              {!msgsLoading && messages.length === 0 && (
                <div className="flex flex-col items-center py-12 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-100">
                    <MessageCircle className="h-6 w-6 text-gray-300" />
                  </div>
                  <p className="mt-3 text-sm text-gray-500 font-medium">Aucun message</p>
                  <p className="mt-1 text-xs text-gray-400">Cette conversation ne contient pas encore de messages</p>
                </div>
              )}

              {messages.map((msg) => {
                const isOutbound = msg.direction === "outbound";
                const isAI = msg.is_ai_generated;
                return (
                  <div key={msg.id} className={cn("flex gap-2", isOutbound ? "justify-end" : "justify-start")}>
                    {/* AI badge on inbound side */}
                    {!isOutbound && isAI && (
                      <div className="flex shrink-0 items-end pb-6">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-600 shadow-sm shadow-brand-200">
                          <Zap className="h-3.5 w-3.5 text-white" />
                        </div>
                      </div>
                    )}

                    <div className="max-w-[75%] space-y-1.5">
                      {/* Bubble */}
                      <div
                        className={cn(
                          "rounded-2xl px-4 py-3 shadow-sm",
                          isOutbound
                            ? "bg-brand-500 text-white rounded-br-md"
                            : "bg-white text-gray-800 border border-gray-100 rounded-bl-md",
                          isOutbound && isAI && "bg-gradient-to-br from-brand-500 to-brand-600",
                        )}
                      >
                        <p className="text-[13px] leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      </div>

                      {/* Meta row */}
                      <div
                        className={cn(
                          "flex items-center gap-2 px-1 text-[11px]",
                          isOutbound ? "justify-end" : "justify-start",
                        )}
                      >
                        <span className="text-gray-400">{formatMessageTime(msg.created_at)}</span>
                        {isAI && (
                          <span className="flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-brand-600 font-medium">
                            <Zap className="h-3 w-3" />
                            IA
                            {msg.ai_confidence_score != null && (
                              <span className="text-brand-400 ml-0.5">
                                {Math.round(msg.ai_confidence_score * 100)}%
                              </span>
                            )}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* AI badge on outbound side */}
                    {isOutbound && isAI && (
                      <div className="flex shrink-0 items-end pb-6">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-600 shadow-sm shadow-brand-200">
                          <Zap className="h-3.5 w-3.5 text-white" />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Typing indicator */}
              {aiProcessing && <TypingIndicator />}

              <div ref={messagesEndRef} />
            </div>

            {/* ── Quick Replies ── */}
            <div className="border-t border-gray-100 bg-white px-4 pt-2 pb-0">
              <div className="flex gap-1.5 overflow-x-auto pb-2 scrollbar-hide">
                {QUICK_REPLIES.map((qr) => (
                  <button
                    key={qr.label}
                    onClick={() => handleQuickReply(qr.text)}
                    className={cn(
                      "shrink-0 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium",
                      "text-gray-600 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700",
                      "transition-all duration-150 active:scale-95",
                    )}
                  >
                    {qr.label}
                  </button>
                ))}
              </div>
            </div>

            {/* ── Input Area ── */}
            <div className="border-t border-gray-100 px-4 py-3 bg-white">
              <div className="flex gap-2 items-end">
                <div className="relative flex-1">
                  <input
                    ref={inputRef}
                    type="text"
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="\u00c9crivez votre r\u00e9ponse..."
                    className="input-base pr-20"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey && reply.trim()) handleSend();
                    }}
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[11px] text-gray-300">
                    <CornerDownLeft className="h-3 w-3" />
                    Entr\u00e9e
                  </div>
                </div>
                <button
                  onClick={handleSend}
                  disabled={!reply.trim() || sending}
                  className={cn(
                    "btn-primary px-4 py-2.5 shrink-0",
                    "disabled:opacity-40 disabled:cursor-not-allowed",
                  )}
                >
                  {sending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ================================================================ */}
      {/* RIGHT: Client Info + AI Suggestions                              */}
      {/* ================================================================ */}
      {selected && (
        <div className="hidden w-80 flex-col border-l border-gray-100 bg-gray-50/50 xl:flex">
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            {/* Client Info */}
            <div>
              <p className="section-label mb-3">Client</p>
              <div className="rounded-xl bg-white border border-gray-100 p-4 space-y-3 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gray-100">
                    <User className="h-5 w-5 text-gray-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{selected.customer_name || "Inconnu"}</p>
                    <div className="flex items-center gap-1.5 text-xs text-gray-400">
                      {platformIcon(selected.platform)}
                      <span>{selected.platform}</span>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  {[
                    { label: "Messages", value: `${selected.message_count}` },
                    { label: "Statut", value: (statusCfg[selected.status] || statusCfg.open).label },
                    { label: "Ouvert le", value: new Date(selected.created_at).toLocaleDateString("fr-FR") },
                    { label: "Dernier msg", value: formatConversationTime(selected.last_message_at) || "N/A" },
                  ].map((item) => (
                    <div key={item.label}>
                      <p className="text-[11px] text-gray-400 uppercase tracking-wide">{item.label}</p>
                      <p className="text-sm font-medium text-gray-800 mt-0.5">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Tags */}
            {selected.tags.length > 0 && (
              <div>
                <p className="section-label mb-2">Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {selected.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-lg bg-gray-100 px-2.5 py-1 text-[11px] font-medium text-gray-600"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* AI Suggestions */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="section-label">Suggestions IA</p>
                {suggestions.length > 0 && (
                  <span className="text-[11px] font-medium text-brand-500">
                    {suggestions.length} r\u00e9sultat{suggestions.length > 1 ? "s" : ""}
                  </span>
                )}
              </div>

              {suggestionLoading ? (
                <div className="rounded-xl bg-white border border-gray-100 p-4">
                  <div className="flex items-center gap-2.5 text-xs text-gray-400">
                    <Loader2 className="h-4 w-4 animate-spin text-brand-500" />
                    <span>Recherche dans la base de connaissances...</span>
                  </div>
                </div>
              ) : suggestions.length > 0 ? (
                <div className="space-y-3">
                  {suggestions.map((s, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl bg-white border border-gray-100 p-4 space-y-3 shadow-sm hover:border-brand-200 transition-colors"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <Sparkles className="h-4 w-4 text-brand-500 shrink-0" />
                          <p className="text-xs font-semibold text-gray-700 truncate">
                            {s.document_title}
                          </p>
                        </div>
                      </div>

                      {/* Section title if available */}
                      {s.section_title && (
                        <p className="text-[11px] text-gray-400 -mt-1">
                          {s.section_title}
                        </p>
                      )}

                      {/* Relevance bar */}
                      <div>
                        <p className="text-[11px] text-gray-400 mb-1">Pertinence</p>
                        <ConfidenceBar score={s.score} />
                      </div>

                      {/* Content */}
                      <p className="text-xs text-gray-600 leading-relaxed line-clamp-4">
                        {s.content}
                      </p>

                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleCopySuggestion(s.content)}
                          className={cn(
                            "flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2",
                            "text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors",
                          )}
                        >
                          <Copy className="h-3 w-3" />
                          Copier
                        </button>
                        <button
                          onClick={() => handleUseSuggestion(s.content)}
                          className={cn(
                            "flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-brand-500 px-3 py-2",
                            "text-xs font-semibold text-white hover:bg-brand-600 transition-colors",
                          )}
                        >
                          <ArrowUpRight className="h-3 w-3" />
                          Utiliser
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl bg-gray-50 border border-dashed border-gray-200 p-5 text-center">
                  <BookOpen className="h-6 w-6 text-gray-300 mx-auto" />
                  <p className="mt-2 text-xs text-gray-500 font-medium">Aucune suggestion</p>
                  <p className="mt-1 text-[11px] text-gray-400 leading-relaxed">
                    Ajoutez des documents \u00e0 la base de connaissances pour am\u00e9liorer les suggestions IA.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
