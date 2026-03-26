import { useState, KeyboardEvent } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
  maxTags?: number;
}

export function TagInput({ tags, onChange, placeholder = "Taper puis Entree...", className, maxTags = 50 }: TagInputProps) {
  const [input, setInput] = useState("");

  const addTag = (value: string) => {
    const trimmed = value.trim();
    if (trimmed && !tags.includes(trimmed) && tags.length < maxTags) {
      onChange([...tags, trimmed]);
    }
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(input);
    } else if (e.key === "Backspace" && !input && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const text = e.clipboardData.getData("text");
    const items = text.split(/[,;\n]/).map(s => s.trim()).filter(Boolean);
    const newTags = [...tags];
    items.forEach(item => {
      if (!newTags.includes(item) && newTags.length < maxTags) newTags.push(item);
    });
    onChange(newTags);
  };

  return (
    <div className={cn("flex flex-wrap gap-1.5 rounded-xl border border-gray-200 bg-white px-3 py-2 focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-500/10 transition-colors", className)}>
      {tags.map((tag) => (
        <span key={tag} className="inline-flex items-center gap-1 rounded-lg bg-brand-50 text-brand-700 px-2.5 py-1 text-xs font-medium">
          {tag}
          <button onClick={() => onChange(tags.filter(t => t !== tag))} className="rounded-full hover:bg-brand-100 p-0.5 transition-colors">
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onBlur={() => input && addTag(input)}
        placeholder={tags.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[100px] border-0 bg-transparent text-sm outline-none placeholder:text-gray-400"
      />
    </div>
  );
}
