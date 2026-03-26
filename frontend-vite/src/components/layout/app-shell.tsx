import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { ChatWidget } from "@/components/chat/chat-widget";

export function AppShell({ children, fullHeight = false }: { children: React.ReactNode; fullHeight?: boolean }) {
  return (
    <div className="flex min-h-screen bg-page">
      <Sidebar />
      <div className="flex flex-1 flex-col pl-[var(--sidebar-w)]">
        <Topbar />
        <main className={fullHeight ? "flex-1" : "flex-1 px-6 py-6"}>{children}</main>
      </div>
      <ChatWidget />
    </div>
  );
}
