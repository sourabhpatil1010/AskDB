import { motion } from "framer-motion";
import {
  Settings as SettingsIcon,
  Palette,
  Globe,
  Database,
  Cpu,
  Sun,
  Moon,
  CheckCircle2,
  Server,
  Info,
} from "lucide-react";
import { useThemeStore } from "@/store/themeStore";
import { useAppStore } from "@/store/appStore";
import { toast } from "sonner";

export default function SettingsPage() {
  const { theme, setTheme } = useThemeStore();
  const { settings, updateSettings } = useAppStore();

  return (
    <div className="p-6 lg:p-8 max-w-[900px] mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-500 to-slate-700 flex items-center justify-center shadow-lg">
              <SettingsIcon className="w-5 h-5 text-white" />
            </div>
            Settings
          </h1>
          <p className="text-muted-foreground mt-2 text-sm">
            Configure your AskDB preferences and connections.
          </p>
        </div>

        <div className="space-y-6">
          {/* Theme */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Palette className="w-4 h-4 text-primary" />
              <h3 className="font-semibold text-foreground">Appearance</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setTheme("light")}
                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                  theme === "light"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/30"
                }`}
                aria-label="Select light theme"
              >
                <div className="w-10 h-10 rounded-xl bg-white border border-gray-200 flex items-center justify-center shadow-sm">
                  <Sun className="w-5 h-5 text-amber-500" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground">Light</p>
                  <p className="text-xs text-muted-foreground">Clean & bright</p>
                </div>
                {theme === "light" && (
                  <CheckCircle2 className="w-5 h-5 text-primary ml-auto" />
                )}
              </button>
              <button
                onClick={() => setTheme("dark")}
                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                  theme === "dark"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/30"
                }`}
                aria-label="Select dark theme"
              >
                <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center shadow-sm">
                  <Moon className="w-5 h-5 text-violet-400" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground">Dark</p>
                  <p className="text-xs text-muted-foreground">Easy on eyes</p>
                </div>
                {theme === "dark" && (
                  <CheckCircle2 className="w-5 h-5 text-primary ml-auto" />
                )}
              </button>
            </div>
          </div>

          {/* Language */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Globe className="w-4 h-4 text-blue-500" />
              <h3 className="font-semibold text-foreground">Language</h3>
            </div>
            <select
              value={settings.language}
              onChange={(e) => {
                updateSettings({ language: e.target.value });
                toast.success("Language updated");
              }}
              className="w-full max-w-xs px-4 py-2.5 bg-muted/30 border border-border rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
              aria-label="Select language"
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
              <option value="ja">日本語</option>
            </select>
          </div>

          {/* LLM Model */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Cpu className="w-4 h-4 text-violet-500" />
              <h3 className="font-semibold text-foreground">LLM Model</h3>
            </div>
            <select
              value={settings.llmModel}
              onChange={(e) => {
                updateSettings({ llmModel: e.target.value });
                toast.success("Model updated");
              }}
              className="w-full max-w-xs px-4 py-2.5 bg-muted/30 border border-border rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
              aria-label="Select LLM model"
            >
              <option value="llama-3.3-70b-versatile">LLaMA 3.3 70B (Versatile)</option>
              <option value="llama-3.1-8b-instant">LLaMA 3.1 8B (Instant)</option>
              <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
              <option value="gemma2-9b-it">Gemma 2 9B</option>
            </select>
            <p className="text-xs text-muted-foreground mt-2">
              Powered by Groq for ultra-fast inference
            </p>
          </div>

          {/* API URL */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Server className="w-4 h-4 text-emerald-500" />
              <h3 className="font-semibold text-foreground">API Configuration</h3>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">
                  API Base URL
                </label>
                <input
                  type="text"
                  value={settings.apiUrl}
                  onChange={(e) => updateSettings({ apiUrl: e.target.value })}
                  className="w-full max-w-lg px-4 py-2.5 bg-muted/30 border border-border rounded-xl text-sm text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/20"
                  aria-label="API base URL"
                />
              </div>
            </div>
          </div>

          {/* Database Status */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Database className="w-4 h-4 text-primary" />
              <h3 className="font-semibold text-foreground">Database Status</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-muted/30 rounded-xl p-4">
                <p className="text-xs text-muted-foreground mb-1">Status</p>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <p className="text-sm font-semibold text-emerald-500">Connected</p>
                </div>
              </div>
              <div className="bg-muted/30 rounded-xl p-4">
                <p className="text-xs text-muted-foreground mb-1">Engine</p>
                <p className="text-sm font-semibold text-foreground">PostgreSQL</p>
              </div>
              <div className="bg-muted/30 rounded-xl p-4">
                <p className="text-xs text-muted-foreground mb-1">Database</p>
                <p className="text-sm font-semibold text-foreground">askdb</p>
              </div>
              <div className="bg-muted/30 rounded-xl p-4">
                <p className="text-xs text-muted-foreground mb-1">ORM</p>
                <p className="text-sm font-semibold text-foreground">SQLAlchemy</p>
              </div>
            </div>
          </div>

          {/* App Info */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <Info className="w-4 h-4 text-muted-foreground" />
              <h3 className="font-semibold text-foreground">About</h3>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Application</p>
                <p className="font-medium text-foreground">AskDB</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Version</p>
                <p className="font-medium text-foreground">1.0.0</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Frontend</p>
                <p className="font-medium text-foreground">React + TypeScript + Vite</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Backend</p>
                <p className="font-medium text-foreground">FastAPI + LangChain</p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
