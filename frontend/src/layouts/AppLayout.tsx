import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/lib/utils";

export function AppLayout() {
  const sidebarCollapsed = useAppStore((s) => s.sidebarCollapsed);

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <main
        className={cn(
          "flex-1 min-h-screen transition-all duration-300 ease-in-out",
          sidebarCollapsed ? "ml-[68px]" : "ml-[260px]",
          "max-lg:ml-0"
        )}
      >
        <div className="min-h-screen">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
