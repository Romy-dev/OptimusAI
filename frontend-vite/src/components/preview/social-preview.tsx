
import { useState } from "react";
import { PhoneMockup } from "./phone-mockup";
import { cn } from "@/lib/utils";
import {
  ThumbsUp,
  MessageCircle,
  Share2,
  Heart,
  Send,
  Bookmark,
  MoreHorizontal,
  Phone,
  ChevronLeft,
  Check,
  CheckCheck,
} from "lucide-react";

interface SocialPreviewProps {
  content: string;
  hashtags?: string[];
  channel: string;
  brandName: string;
  brandInitials?: string;
  imageUrl?: string;
  className?: string;
}

/**
 * Renders the post inside an iPhone mockup, simulating the look of each platform.
 */
export function SocialPreview({
  content,
  hashtags = [],
  channel,
  brandName,
  brandInitials = "WE",
  imageUrl,
  className,
}: SocialPreviewProps) {
  return (
    <PhoneMockup className={className}>
      {channel === "facebook" && (
        <FacebookPreview
          content={content}
          hashtags={hashtags}
          brandName={brandName}
          brandInitials={brandInitials}
          imageUrl={imageUrl}
        />
      )}
      {channel === "instagram" && (
        <InstagramPreview
          content={content}
          hashtags={hashtags}
          brandName={brandName}
          brandInitials={brandInitials}
          imageUrl={imageUrl}
        />
      )}
      {channel === "whatsapp" && (
        <WhatsAppPreview
          content={content}
          hashtags={hashtags}
          brandName={brandName}
        />
      )}
    </PhoneMockup>
  );
}

/**
 * Channel selector tabs to switch between previews.
 */
export function ChannelTabs({
  active,
  onChange,
  channels = ["facebook", "instagram", "whatsapp"],
}: {
  active: string;
  onChange: (ch: string) => void;
  channels?: string[];
}) {
  const labels: Record<string, { name: string; color: string }> = {
    facebook: { name: "Facebook", color: "bg-blue-500" },
    instagram: { name: "Instagram", color: "bg-gradient-to-tr from-purple-500 via-pink-500 to-orange-400" },
    whatsapp: { name: "WhatsApp", color: "bg-emerald-500" },
  };

  return (
    <div className="flex gap-1.5">
      {channels.map((ch) => {
        const l = labels[ch];
        return (
          <button
            key={ch}
            onClick={() => onChange(ch)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all",
              active === ch
                ? "bg-gray-900 text-white shadow-sm"
                : "bg-gray-100 text-gray-500 hover:bg-gray-200",
            )}
          >
            <span className={cn("h-2 w-2 rounded-full", l?.color)} />
            {l?.name || ch}
          </button>
        );
      })}
    </div>
  );
}

// ─── Facebook ────────────────────────────────────────────

function FacebookPreview({
  content,
  hashtags,
  brandName,
  brandInitials,
  imageUrl,
}: {
  content: string;
  hashtags: string[];
  brandName: string;
  brandInitials: string;
  imageUrl?: string;
}) {
  const fullText = hashtags.length > 0
    ? content + "\n\n" + hashtags.map((h) => `#${h}`).join(" ")
    : content;

  return (
    <div className="bg-white">
      {/* FB Header bar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
        <span className="text-[13px] font-bold text-blue-600">facebook</span>
        <div className="flex gap-2">
          <div className="h-6 w-6 rounded-full bg-gray-100" />
          <div className="h-6 w-6 rounded-full bg-gray-100" />
        </div>
      </div>

      {/* Post */}
      <div className="px-3 pt-3">
        {/* Author */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500 text-white text-[10px] font-bold">
            {brandInitials}
          </div>
          <div>
            <p className="text-[12px] font-semibold text-gray-900">{brandName}</p>
            <p className="text-[10px] text-gray-500">Maintenant · 🌍</p>
          </div>
          <MoreHorizontal className="ml-auto h-4 w-4 text-gray-400" />
        </div>

        {/* Content */}
        <p className="mt-2.5 text-[12px] text-gray-800 leading-relaxed whitespace-pre-wrap">
          {fullText}
        </p>
      </div>

      {/* Image placeholder */}
      {imageUrl ? (
        <img src={imageUrl} className="mt-2 w-full aspect-video object-cover" alt="" />
      ) : (
        <div className="mt-2 w-full aspect-video bg-gradient-to-br from-brand-100 to-sky-100 flex items-center justify-center">
          <span className="text-3xl">🎨</span>
        </div>
      )}

      {/* Reactions bar */}
      <div className="px-3 py-1.5">
        <div className="flex items-center justify-between text-[10px] text-gray-500 pb-1.5 border-b border-gray-100">
          <div className="flex items-center gap-1">
            <span className="flex -space-x-1">
              <span className="h-4 w-4 rounded-full bg-blue-500 flex items-center justify-center text-white text-[7px]">👍</span>
              <span className="h-4 w-4 rounded-full bg-red-500 flex items-center justify-center text-white text-[7px]">❤️</span>
            </span>
            <span>24</span>
          </div>
          <span>3 commentaires · 2 partages</span>
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-around pt-1.5">
          {[
            { icon: ThumbsUp, label: "J'aime" },
            { icon: MessageCircle, label: "Commenter" },
            { icon: Share2, label: "Partager" },
          ].map((a) => (
            <button key={a.label} className="flex items-center gap-1 text-[11px] text-gray-500 font-medium py-1">
              <a.icon className="h-3.5 w-3.5" />
              {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Instagram ───────────────────────────────────────────

function InstagramPreview({
  content,
  hashtags,
  brandName,
  brandInitials,
  imageUrl,
}: {
  content: string;
  hashtags: string[];
  brandName: string;
  brandInitials: string;
  imageUrl?: string;
}) {
  return (
    <div className="bg-white">
      {/* IG Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
        <span className="text-[14px] font-bold text-gray-900" style={{ fontFamily: "serif" }}>Instagram</span>
        <div className="flex gap-3">
          <Heart className="h-5 w-5 text-gray-900" />
          <Send className="h-5 w-5 text-gray-900 -rotate-45" />
        </div>
      </div>

      {/* Post header */}
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-purple-500 via-pink-500 to-orange-400 p-[2px]">
          <div className="flex h-full w-full items-center justify-center rounded-full bg-white text-[8px] font-bold text-gray-700">
            {brandInitials}
          </div>
        </div>
        <span className="text-[12px] font-semibold text-gray-900">{brandName.toLowerCase().replace(/\s/g, "")}</span>
        <MoreHorizontal className="ml-auto h-4 w-4 text-gray-900" />
      </div>

      {/* Image */}
      {imageUrl ? (
        <img src={imageUrl} className="w-full aspect-square object-cover" alt="" />
      ) : (
        <div className="w-full aspect-square bg-gradient-to-br from-brand-100 via-sky-50 to-brand-200 flex items-center justify-center">
          <span className="text-5xl">🌍</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between px-3 pt-2">
        <div className="flex gap-3">
          <Heart className="h-5 w-5 text-gray-900" />
          <MessageCircle className="h-5 w-5 text-gray-900" />
          <Send className="h-5 w-5 text-gray-900 -rotate-45" />
        </div>
        <Bookmark className="h-5 w-5 text-gray-900" />
      </div>

      {/* Likes */}
      <p className="px-3 pt-1.5 text-[11px] font-semibold text-gray-900">142 J&apos;aime</p>

      {/* Caption */}
      <div className="px-3 pt-1 pb-2">
        <p className="text-[11px] text-gray-800 leading-relaxed">
          <span className="font-semibold">{brandName.toLowerCase().replace(/\s/g, "")} </span>
          {content.slice(0, 120)}{content.length > 120 ? "..." : ""}
        </p>
        {hashtags.length > 0 && (
          <p className="mt-1 text-[11px] text-blue-800">
            {hashtags.map((h) => `#${h}`).join(" ")}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── WhatsApp ────────────────────────────────────────────

function WhatsAppPreview({
  content,
  hashtags,
  brandName,
}: {
  content: string;
  hashtags: string[];
  brandName: string;
}) {
  const fullText = hashtags.length > 0
    ? content + "\n\n" + hashtags.map((h) => `#${h}`).join(" ")
    : content;

  return (
    <div className="bg-[#ECE5DD] min-h-[420px] flex flex-col">
      {/* WA Header */}
      <div className="flex items-center gap-2 bg-[#075E54] px-3 py-2 text-white">
        <ChevronLeft className="h-5 w-5" />
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-300 text-gray-600 text-[10px] font-bold">
          {brandName[0]}
        </div>
        <div className="flex-1">
          <p className="text-[12px] font-semibold">{brandName}</p>
          <p className="text-[9px] text-green-200">en ligne</p>
        </div>
        <Phone className="h-4 w-4" />
      </div>

      {/* Chat area */}
      <div className="flex-1 px-3 py-4 space-y-2">
        {/* Business message bubble */}
        <div className="max-w-[85%]">
          <div className="rounded-xl rounded-tl-sm bg-white px-3 py-2 shadow-sm">
            <p className="text-[11px] text-gray-800 leading-relaxed whitespace-pre-wrap">
              {fullText}
            </p>
            <div className="mt-1 flex items-center justify-end gap-1">
              <span className="text-[9px] text-gray-400">09:41</span>
              <CheckCheck className="h-3 w-3 text-blue-500" />
            </div>
          </div>
        </div>

        {/* Simulated customer response */}
        <div className="flex justify-end">
          <div className="max-w-[75%] rounded-xl rounded-tr-sm bg-[#DCF8C6] px-3 py-2 shadow-sm">
            <p className="text-[11px] text-gray-800">Intéressant ! Quel est le prix ? 🤔</p>
            <div className="mt-1 flex items-center justify-end gap-1">
              <span className="text-[9px] text-gray-400">09:42</span>
              <CheckCheck className="h-3 w-3 text-blue-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Input bar */}
      <div className="flex items-center gap-2 bg-[#F0F0F0] px-3 py-2">
        <div className="flex-1 rounded-full bg-white px-3 py-1.5 text-[11px] text-gray-400">
          Écrire un message...
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#075E54]">
          <Send className="h-3.5 w-3.5 text-white" />
        </div>
      </div>
    </div>
  );
}
