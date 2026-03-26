
import { cn } from "@/lib/utils";

/**
 * iPhone mockup shell. Wraps any content in a realistic phone frame.
 */
export function PhoneMockup({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("relative mx-auto", className)} style={{ width: 280 }}>
      {/* Phone frame */}
      <div className="relative rounded-[2.5rem] border-[6px] border-gray-900 bg-gray-900 shadow-xl">
        {/* Notch / dynamic island */}
        <div className="absolute left-1/2 top-0 z-20 -translate-x-1/2 translate-y-2">
          <div className="h-6 w-24 rounded-full bg-gray-900" />
        </div>

        {/* Screen */}
        <div className="relative overflow-hidden rounded-[2rem] bg-white">
          {/* Status bar */}
          <div className="flex items-center justify-between bg-white px-6 pb-1 pt-8 text-[10px] font-semibold text-gray-900">
            <span>9:41</span>
            <div className="flex items-center gap-1">
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3a4.237 4.237 0 00-6 0zm-4-4l2 2a7.074 7.074 0 0110 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M17 4h-3V2h-4v2H7v18h10V4z"/></svg>
            </div>
          </div>

          {/* Content area */}
          <div className="min-h-[420px] max-h-[480px] overflow-y-auto">
            {children}
          </div>

          {/* Home indicator */}
          <div className="flex justify-center py-2 bg-white">
            <div className="h-1 w-28 rounded-full bg-gray-300" />
          </div>
        </div>
      </div>
    </div>
  );
}
