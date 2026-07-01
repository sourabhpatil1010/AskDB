import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Search,
  History,
  Bookmark,
  Database,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Moon,
  Sun,
  Menu,
  X,
  LogOut,
  User,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/appStore";
import { useThemeStore } from "@/store/themeStore";
import { useAuthStore } from "@/store/authStore";
import { useState } from "react";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/search", label: "AI Search", icon: Search },
  { path: "/history", label: "History", icon: History },
  { path: "/saved", label: "Saved Queries", icon: Bookmark },
  { path: "/schema", label: "Schema Explorer", icon: Database },
  { path: "/analytics", label: "Analytics", icon: BarChart3 },
];

const bottomItems = [
  { path: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();
  const { theme, toggleTheme } = useThemeStore();
  const { user, logout, isLoading: authLoading } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    setLoggingOut(true);
    await logout();
    setLoggingOut(false);
    navigate('/login', { replace: true });
  };

  const NavLink = ({ item }: { item: (typeof navItems)[0] }) => {
    const Icon = item.icon;
    const active = isActive(item.path);

    return (
      <Link
        to={item.path}
        onClick={() => setMobileOpen(false)}
        className={cn(
          "relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group",
          active
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
        )}
        aria-label={item.label}
        aria-current={active ? "page" : undefined}
      >
        {active && (
          <motion.div
            layoutId="sidebar-active"
            className="absolute inset-0 bg-primary/10 rounded-xl"
            transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
          />
        )}
        <Icon className={cn("w-5 h-5 shrink-0 relative z-10", active && "text-primary")} />
        <AnimatePresence mode="wait">
          {!sidebarCollapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              className="relative z-10 whitespace-nowrap overflow-hidden"
            >
              {item.label}
            </motion.span>
          )}
        </AnimatePresence>
        {active && !sidebarCollapsed && (
          <motion.div
            layoutId="sidebar-indicator"
            className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r-full"
            transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
          />
        )}
      </Link>
    );
  };

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 mb-2">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25 shrink-0">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <AnimatePresence mode="wait">
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="overflow-hidden"
            >
              <h1 className="text-lg font-bold text-foreground tracking-tight">AskDB</h1>
              <p className="text-[10px] text-muted-foreground font-medium -mt-0.5">AI-Powered SQL</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-1" aria-label="Main navigation">
        {navItems.map((item) => (
          <NavLink key={item.path} item={item} />
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-4 space-y-1 border-t border-border pt-4 mt-4">
        {bottomItems.map((item) => (
          <NavLink key={item.path} item={item} />
        ))}

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-200 w-full"
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === "dark" ? (
            <Sun className="w-5 h-5 shrink-0" />
          ) : (
            <Moon className="w-5 h-5 shrink-0" />
          )}
          <AnimatePresence mode="wait">
            {!sidebarCollapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="whitespace-nowrap"
              >
                {theme === "dark" ? "Light Mode" : "Dark Mode"}
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Collapse Toggle - Desktop only */}
        <button
          onClick={toggleSidebar}
          className="hidden lg:flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all duration-200 w-full"
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5 shrink-0" />
          ) : (
            <>
              <ChevronLeft className="w-5 h-5 shrink-0" />
              <span className="whitespace-nowrap">Collapse</span>
            </>
          )}
        </button>

        {/* User info + Logout */}
        <div className="border-t border-border pt-3 mt-2">
          {/* User avatar row */}
          <div className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-xl mb-1",
            sidebarCollapsed ? "justify-center" : ""
          )}>
            <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
              <User className="w-4 h-4 text-primary" />
            </div>
            <AnimatePresence mode="wait">
              {!sidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="overflow-hidden min-w-0"
                >
                  <p className="text-sm font-medium text-foreground truncate">
                    {user?.full_name || 'User'}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Logout button */}
          <button
            id="sidebar-logout"
            onClick={handleLogout}
            disabled={loggingOut || authLoading}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-200 w-full disabled:opacity-50"
            aria-label="Sign out"
          >
            {loggingOut ? (
              <Loader2 className="w-5 h-5 shrink-0 animate-spin" />
            ) : (
              <LogOut className="w-5 h-5 shrink-0" />
            )}
            <AnimatePresence mode="wait">
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="whitespace-nowrap"
                >
                  {loggingOut ? 'Signing out…' : 'Sign out'}
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-50 lg:hidden p-2 rounded-xl bg-card border border-border shadow-lg"
        aria-label="Open navigation menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: "spring", bounce: 0.1, duration: 0.4 }}
            className="fixed top-0 left-0 bottom-0 w-[260px] bg-card border-r border-border z-50 flex flex-col lg:hidden shadow-2xl"
          >
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-muted/50 text-muted-foreground"
              aria-label="Close navigation menu"
            >
              <X className="w-5 h-5" />
            </button>
            {sidebarContent}
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Desktop sidebar */}
      <motion.aside
        animate={{ width: sidebarCollapsed ? 68 : 260 }}
        transition={{ type: "spring", bounce: 0.1, duration: 0.4 }}
        className={cn(
          "fixed top-0 left-0 bottom-0 bg-card border-r border-border z-30 flex-col hidden lg:flex",
          "overflow-hidden"
        )}
      >
        {sidebarContent}
      </motion.aside>
    </>
  );
}
