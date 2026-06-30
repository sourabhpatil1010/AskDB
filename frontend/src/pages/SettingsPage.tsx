import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
  Cloud,
  HardDrive,
  RefreshCw,
  Zap,
  Wifi,
  WifiOff,
  Loader2,
  ChevronDown,
  Eye,
  EyeOff,
  Trash2,
  Key,
  Save,
  ShieldAlert,
  ExternalLink,
  X,
} from "lucide-react";
import { useThemeStore } from "@/store/themeStore";
import { useAppStore } from "@/store/appStore";
import type { CloudProvider, AnyProvider } from "@/store/appStore";
import { llmSettingsApi } from "@/services/llm-settings.service";
import {
  PROVIDER_INFO,
  PROVIDER_MODELS,
  PROVIDER_DEFAULT_MODEL,
  CLOUD_PROVIDER_LIST,
} from "@/config/providers";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Mask helper — never expose full key in UI
// ---------------------------------------------------------------------------

function maskApiKey(key: string): string {
  if (!key || key.length < 6) return "••••••••";
  const prefix = key.slice(0, 4);
  return `${prefix}${"•".repeat(Math.min(24, Math.max(8, key.length - 4)))}`;
}

// ---------------------------------------------------------------------------
// Security Warning Dialog
// ---------------------------------------------------------------------------

interface SecurityDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

function SecurityWarningDialog({ onConfirm, onCancel }: SecurityDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Dialog */}
      <motion.div
        initial={{ opacity: 0, scale: 0.92, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.92, y: 12 }}
        transition={{ type: "spring", damping: 22, stiffness: 320 }}
        className="relative bg-card border border-border rounded-2xl shadow-2xl max-w-md w-full p-6 z-10"
      >
        {/* Close button */}
        <button
          onClick={onCancel}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Icon */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">
              Security Warning
            </h2>
            <p className="text-xs text-muted-foreground">
              Before storing your API key
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 mb-5 space-y-2">
          <p className="text-sm text-foreground font-medium">
            Your API key will be stored on this device.
          </p>
          <ul className="space-y-1.5 text-xs text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">⚠</span>
              Anyone with access to this browser may be able to view it.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">⚠</span>
              Do not enable this option on shared or public computers.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5">⚠</span>
              The key is stored in <code className="font-mono bg-muted/50 px-1 rounded">localStorage</code> — browser DevTools can read it.
            </li>
          </ul>
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-muted-foreground bg-muted/50 border border-border rounded-xl hover:bg-muted transition-colors"
            id="security-warning-cancel"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium text-white bg-amber-500 rounded-xl hover:bg-amber-600 transition-colors shadow-md shadow-amber-500/20"
            id="security-warning-confirm"
          >
            Continue
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Provider info panel
// ---------------------------------------------------------------------------

interface ProviderInfoPanelProps {
  providerId: AnyProvider;
  connectionStatus?: { connected: boolean; message: string } | null;
  testing?: boolean;
}

function ProviderInfoPanel({ providerId, connectionStatus, testing }: ProviderInfoPanelProps) {
  const info = PROVIDER_INFO[providerId];
  if (!info) return null;

  return (
    <motion.div
      key={providerId}
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={`rounded-xl border p-4 bg-muted/20`}
      style={{ borderColor: "hsl(var(--border))" }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`w-7 h-7 rounded-lg bg-gradient-to-br ${info.gradient} flex items-center justify-center text-sm shadow-sm`}
            >
              {info.emoji}
            </span>
            <span className={`text-sm font-semibold ${info.color}`}>
              {info.label}
            </span>
          </div>
          <ul className="space-y-1">
            {info.features.map((f) => (
              <li key={f} className="text-xs text-muted-foreground">
                {f}
              </li>
            ))}
          </ul>
        </div>
        <div className="flex flex-col items-end gap-2">
          <a
            href={info.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors shrink-0 mt-0.5"
            aria-label={`Visit ${info.label} website`}
          >
            <ExternalLink className="w-3 h-3" />
            Website
          </a>

          <div className="mt-auto">
            {testing ? (
              <span className="text-[10px] font-medium text-muted-foreground animate-pulse flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" /> Testing...
              </span>
            ) : connectionStatus ? (
              connectionStatus.connected ? (
                <span className="text-[10px] font-medium text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded-md">🟢 Connected</span>
              ) : (
                <span className="text-[10px] font-medium text-red-500 bg-red-500/10 px-1.5 py-0.5 rounded-md">🔴 Failed</span>
              )
            ) : (
              <span className="text-[10px] font-medium text-muted-foreground">Status: Unknown</span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const { theme, setTheme } = useThemeStore();
  const { settings, updateSettings, llmSettings, updateLLMSettings } =
    useAppStore();

  // ---- local UI state ----
  const [models, setModels] = useState<string[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<{
    connected: boolean;
    message: string;
  } | null>(null);
  const [testing, setTesting] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  // Local staging area — only committed to store on Save
  const [apiKeyInput, setApiKeyInput] = useState(llmSettings.apiKey || "");
  const [saving, setSaving] = useState(false);
  // Security warning dialog
  const [showSecurityDialog, setShowSecurityDialog] = useState(false);
  // Pending rememberKey value waiting for confirmation
  const [pendingRememberKey, setPendingRememberKey] = useState(false);

  const isCloud = llmSettings.aiSource === "cloud";
  const activeInfo =
    PROVIDER_INFO[llmSettings.provider as AnyProvider] ?? PROVIDER_INFO.groq;

  // ---- keep local apiKey input in sync when store changes externally ----
  useEffect(() => {
    setApiKeyInput(llmSettings.apiKey || "");
  }, [llmSettings.apiKey]);

  // ---- Load models when provider/source changes ----
  useEffect(() => {
    loadModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llmSettings.aiSource, llmSettings.provider]);

  const loadModels = useCallback(async () => {
    if (!isCloud) {
      // Local Ollama — fetch from backend
      setLoadingModels(true);
      try {
        const result = await llmSettingsApi.listModels({
          source: "local",
          provider: "ollama",
          ollama_base_url: llmSettings.ollamaBaseUrl,
        });
        setModels(result.models);
      } catch {
        setModels([]);
      } finally {
        setLoadingModels(false);
      }
      return;
    }

    // Cloud — use curated static list (no API call needed)
    const providerModels =
      PROVIDER_MODELS[llmSettings.provider as AnyProvider] ?? [];
    setModels(providerModels);

    // For OpenRouter with a saved key, try to fetch live list from backend
    if (llmSettings.provider === "openrouter" && llmSettings.apiKey) {
      setLoadingModels(true);
      try {
        const result = await llmSettingsApi.listModels({
          source: "cloud",
          provider: "openrouter",
          api_key: llmSettings.apiKey,
          ollama_base_url: llmSettings.ollamaBaseUrl,
        });
        if (result.models.length > 0) {
          setModels(result.models);
        }
      } catch {
        // Fallback to static list already set above
      } finally {
        setLoadingModels(false);
      }
    }
  }, [isCloud, llmSettings.aiSource, llmSettings.provider, llmSettings.apiKey, llmSettings.ollamaBaseUrl]);

  // ---- Handlers ----

  const handleSourceChange = async (source: "cloud" | "local") => {
    const provider: AnyProvider = source === "cloud" ? "groq" : "ollama";
    const defaultModel =
      source === "cloud"
        ? PROVIDER_DEFAULT_MODEL.groq
        : "llama3:latest";

    updateLLMSettings({ aiSource: source, provider, model: defaultModel });
    setConnectionStatus(null);

    try {
      await llmSettingsApi.updateConfig({
        source,
        provider,
        model: defaultModel,
        api_key: source === "cloud" ? llmSettings.apiKey : "",
        ollama_base_url: llmSettings.ollamaBaseUrl,
      });
      toast.success(`Switched to ${source === "cloud" ? "Cloud API" : "Local LLM"}`);
    } catch {
      toast.error("Failed to update backend config");
    }
  };

  const handleProviderChange = async (providerId: CloudProvider) => {
    const defaultModel = PROVIDER_DEFAULT_MODEL[providerId];
    updateLLMSettings({ provider: providerId, model: defaultModel });
    setConnectionStatus(null);

    try {
      await llmSettingsApi.updateConfig({
        provider: providerId,
        model: defaultModel,
        api_key: llmSettings.apiKey,
        ollama_base_url: llmSettings.ollamaBaseUrl,
      });
    } catch {
      // Will re-sync on Save
    }
  };

  const handleModelChange = (model: string) => {
    updateLLMSettings({ model });
  };

  const handleBaseUrlChange = (url: string) => {
    updateLLMSettings({ ollamaBaseUrl: url });
  };

  /** "Remember key" checkbox — requires security confirmation when enabling */
  const handleRememberKeyChange = (checked: boolean) => {
    if (checked) {
      // Show security warning before enabling
      setPendingRememberKey(true);
      setShowSecurityDialog(true);
    } else {
      // Disabling: clear from localStorage immediately
      updateLLMSettings({ rememberKey: false });
      clearApiKeyFromLocalStorage();
    }
  };

  const confirmRememberKey = () => {
    setShowSecurityDialog(false);
    updateLLMSettings({ rememberKey: true });
    setPendingRememberKey(false);
    toast.success("API key will be remembered on this device");
  };

  const cancelRememberKey = () => {
    setShowSecurityDialog(false);
    setPendingRememberKey(false);
    // Leave rememberKey unchanged (stays false)
  };

  const clearApiKeyFromLocalStorage = () => {
    const stored = localStorage.getItem("askdb-app-store");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed?.state?.llmSettings) {
          parsed.state.llmSettings.apiKey = "";
          parsed.state.llmSettings.rememberKey = false;
          localStorage.setItem("askdb-app-store", JSON.stringify(parsed));
        }
      } catch {
        // ignore
      }
    }
  };

  const handleClearApiKey = () => {
    setApiKeyInput("");
    updateLLMSettings({ apiKey: "", rememberKey: false });
    clearApiKeyFromLocalStorage();
    toast.success("API key cleared");
  };

  const handleSave = async () => {
    setSaving(true);
    setConnectionStatus(null);
    try {
      // Commit staged key to store
      updateLLMSettings({ apiKey: apiKeyInput });

      // Sync to backend (key held in memory only on server)
      await llmSettingsApi.updateConfig({
        source: llmSettings.aiSource,
        provider: llmSettings.provider,
        model: llmSettings.model,
        api_key: apiKeyInput,
        ollama_base_url: llmSettings.ollamaBaseUrl,
      });

      // For OpenRouter, refresh live model list with new key
      if (llmSettings.provider === "openrouter" && apiKeyInput) {
        try {
          const result = await llmSettingsApi.listModels({
            source: "cloud",
            provider: "openrouter",
            api_key: apiKeyInput,
            ollama_base_url: llmSettings.ollamaBaseUrl,
          });
          if (result.models.length > 0) setModels(result.models);
        } catch {
          // Fallback to static list
        }
      }

      setSyncing(false);
      toast.success("Settings saved successfully");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setConnectionStatus(null);
    try {
      const result = await llmSettingsApi.testConnection({
        source: llmSettings.aiSource,
        provider: llmSettings.provider,
        model: llmSettings.model,
        api_key: apiKeyInput,
        ollama_base_url: llmSettings.ollamaBaseUrl,
      });
      setConnectionStatus(result);
      if (result.connected) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || err?.message || "Connection test failed";
      setConnectionStatus({ connected: false, message: msg });
      toast.error(msg);
    } finally {
      setTesting(false);
    }
  };

  const handleRefreshModels = async () => {
    setLoadingModels(true);
    try {
      const result = await llmSettingsApi.listModels({
        source: "local",
        provider: "ollama",
        ollama_base_url: llmSettings.ollamaBaseUrl,
      });
      setModels(result.models);
      toast.success(`${result.models.length} model(s) found`);
    } catch {
      toast.error("Could not reach Ollama");
    } finally {
      setLoadingModels(false);
    }
  };

  // ---- Derived values ----
  const keyIsStored = !!llmSettings.apiKey;
  const keyInputChanged = apiKeyInput !== llmSettings.apiKey;

  const connectionStatusBadge = connectionStatus && (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${
        connectionStatus.connected
          ? "bg-emerald-500/10 text-emerald-500"
          : "bg-red-500/10 text-red-400"
      }`}
    >
      <span className="text-base">
        {connectionStatus.connected ? "🟢" : "🔴"}
      </span>
      {connectionStatus.message}
    </div>
  );

  return (
    <>
      {/* Security Warning Portal */}
      <AnimatePresence>
        {showSecurityDialog && (
          <SecurityWarningDialog
            onConfirm={confirmRememberKey}
            onCancel={cancelRememberKey}
          />
        )}
      </AnimatePresence>

      <div className="p-6 lg:p-8 max-w-[900px] mx-auto">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-500 to-slate-700 flex items-center justify-center shadow-lg">
                <SettingsIcon className="w-5 h-5 text-white" />
              </div>
              Settings
            </h1>
            <p className="text-muted-foreground mt-2 text-sm">
              Configure your AskDB preferences and AI provider.
            </p>
          </div>

          <div className="space-y-6">
            {/* ========== AI Provider ========== */}
            <div className="bg-card border border-border rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-6">
                <Cpu className="w-4 h-4 text-violet-500" />
                <h3 className="font-semibold text-foreground">AI Provider</h3>
                {syncing && (
                  <Loader2 className="w-3.5 h-3.5 text-muted-foreground animate-spin ml-auto" />
                )}
              </div>

              {/* ── AI Source selector ── */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <button
                  id="source-cloud"
                  onClick={() => handleSourceChange("cloud")}
                  className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    isCloud
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/30"
                  }`}
                  aria-label="Select Cloud API"
                >
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-sm ${
                      isCloud
                        ? "bg-gradient-to-br from-violet-500 to-indigo-600"
                        : "bg-muted/50 border border-border"
                    }`}
                  >
                    <Cloud
                      className={`w-5 h-5 ${isCloud ? "text-white" : "text-muted-foreground"}`}
                    />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium text-foreground">Cloud API</p>
                    <p className="text-xs text-muted-foreground">Groq · OpenAI · Gemini · more</p>
                  </div>
                  {isCloud && (
                    <CheckCircle2 className="w-5 h-5 text-primary ml-auto" />
                  )}
                </button>

                <button
                  id="source-local"
                  onClick={() => handleSourceChange("local")}
                  className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    !isCloud
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/30"
                  }`}
                  aria-label="Select Local LLM"
                >
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-sm ${
                      !isCloud
                        ? "bg-gradient-to-br from-emerald-500 to-teal-600"
                        : "bg-muted/50 border border-border"
                    }`}
                  >
                    <HardDrive
                      className={`w-5 h-5 ${!isCloud ? "text-white" : "text-muted-foreground"}`}
                    />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium text-foreground">Local LLM</p>
                    <p className="text-xs text-muted-foreground">Ollama · No API key needed</p>
                  </div>
                  {!isCloud && (
                    <CheckCircle2 className="w-5 h-5 text-primary ml-auto" />
                  )}
                </button>
              </div>

              {/* ── CLOUD CONFIG ── */}
              {isCloud && (
                <div className="space-y-5">
                  {/* Provider grid selector */}
                  <div>
                    <label className="text-xs text-muted-foreground mb-3 block font-medium">
                      Provider
                    </label>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
                      {CLOUD_PROVIDER_LIST.map((p) => {
                        const isSelected = llmSettings.provider === p.id;
                        return (
                          <button
                            key={p.id}
                            id={`provider-${p.id}`}
                            onClick={() => handleProviderChange(p.id)}
                            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl border-2 transition-all text-left ${
                              isSelected
                                ? "border-primary bg-primary/5"
                                : "border-border hover:border-primary/20 hover:bg-muted/30"
                            }`}
                            aria-label={`Select ${p.label}`}
                            aria-pressed={isSelected}
                          >
                            <span
                              className={`w-7 h-7 rounded-lg bg-gradient-to-br ${p.gradient} flex items-center justify-center text-sm shrink-0 shadow-sm`}
                            >
                              {p.emoji}
                            </span>
                            <div className="min-w-0">
                              <p className={`text-xs font-semibold truncate ${isSelected ? p.color : "text-foreground"}`}>
                                {p.label}
                              </p>
                              <p className="text-[10px] text-muted-foreground truncate">
                                {p.tagline}
                              </p>
                            </div>
                            {isSelected && (
                              <CheckCircle2 className="w-3.5 h-3.5 text-primary ml-auto shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {/* Provider info panel */}
                    <AnimatePresence mode="wait">
                      <ProviderInfoPanel
                        key={llmSettings.provider}
                        providerId={llmSettings.provider as AnyProvider}
                        connectionStatus={connectionStatus}
                        testing={testing}
                      />
                    </AnimatePresence>
                  </div>

                  {/* API Key */}
                  <div>
                    <label className="text-xs text-muted-foreground mb-2 block font-medium flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5" />
                      API Key
                      {keyIsStored && (
                        <span className="ml-1 px-1.5 py-0.5 text-[10px] font-medium bg-emerald-500/10 text-emerald-500 rounded-md">
                          {llmSettings.rememberKey ? "saved to device" : "in memory"}
                        </span>
                      )}
                    </label>

                    <div className="flex items-center gap-2 w-full max-w-lg">
                      <div className="relative flex-1">
                        <input
                          id="api-key-input"
                          type={showApiKey ? "text" : "password"}
                          value={apiKeyInput}
                          onChange={(e) => setApiKeyInput(e.target.value)}
                          placeholder="Enter your API key..."
                          className="w-full px-4 py-2.5 pr-10 bg-muted/30 border border-border rounded-xl text-sm text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 placeholder:text-muted-foreground/50"
                          aria-label="API key"
                          autoComplete="off"
                          spellCheck={false}
                        />
                        <button
                          type="button"
                          onClick={() => setShowApiKey((v) => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                          aria-label={showApiKey ? "Hide API key" : "Show API key"}
                          id="toggle-api-key-visibility"
                        >
                          {showApiKey ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={handleClearApiKey}
                        id="clear-api-key-btn"
                        className="flex items-center gap-1.5 px-3 py-2.5 bg-red-500/10 text-red-500 text-sm rounded-xl hover:bg-red-500/20 transition-colors"
                        aria-label="Clear API key"
                        title="Clear API key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Masked display of stored key */}
                    {keyIsStored && !keyInputChanged && (
                      <p className="mt-1.5 text-xs text-muted-foreground font-mono flex items-center gap-1.5">
                        <span className="text-emerald-500">✓</span>
                        {maskApiKey(llmSettings.apiKey)}
                      </p>
                    )}

                    {/* Remember checkbox with security label */}
                    <label
                      className="flex items-center gap-2.5 mt-3 cursor-pointer w-fit group"
                      htmlFor="remember-api-key"
                    >
                      <input
                        id="remember-api-key"
                        type="checkbox"
                        checked={llmSettings.rememberKey && !pendingRememberKey}
                        onChange={(e) => handleRememberKeyChange(e.target.checked)}
                        className="w-4 h-4 rounded accent-primary"
                      />
                      <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                        Remember API key on this device
                      </span>
                      <ShieldAlert className="w-3 h-3 text-amber-500/70" />
                    </label>
                  </div>

                  {/* Model selector */}
                  <div>
                    <label className="text-xs text-muted-foreground mb-2 block font-medium">
                      Model
                    </label>
                    <div className="relative w-full max-w-xs">
                      <select
                        id="model-select"
                        value={llmSettings.model}
                        onChange={(e) => handleModelChange(e.target.value)}
                        className="w-full appearance-none px-4 py-2.5 pr-10 bg-muted/30 border border-border rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                        aria-label="Select LLM model"
                      >
                        {models.length === 0 ? (
                          <option value="" disabled>
                            {loadingModels ? "Loading models…" : "No models found"}
                          </option>
                        ) : (
                          models.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))
                        )}
                      </select>
                      <ChevronDown className="w-4 h-4 text-muted-foreground absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    </div>
                    {loadingModels && (
                      <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Fetching available models…
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* ── LOCAL / OLLAMA CONFIG ── */}
              {!isCloud && (
                <div className="space-y-5">
                  {/* Ollama info panel */}
                  <ProviderInfoPanel 
                    providerId="ollama" 
                    connectionStatus={connectionStatus}
                    testing={testing}
                  />

                  {/* Base URL */}
                  <div>
                    <label className="text-xs text-muted-foreground mb-2 block font-medium">
                      Base URL
                    </label>
                    <input
                      id="ollama-base-url"
                      type="text"
                      value={llmSettings.ollamaBaseUrl}
                      onChange={(e) => handleBaseUrlChange(e.target.value)}
                      className="w-full max-w-lg px-4 py-2.5 bg-muted/30 border border-border rounded-xl text-sm text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/20"
                      aria-label="Ollama base URL"
                    />
                  </div>

                  {/* Model selector */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs text-muted-foreground font-medium">
                        Model
                      </label>
                      <button
                        id="refresh-models-btn"
                        onClick={handleRefreshModels}
                        disabled={loadingModels}
                        className="flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                      >
                        <RefreshCw
                          className={`w-3 h-3 ${loadingModels ? "animate-spin" : ""}`}
                        />
                        Refresh Models
                      </button>
                    </div>
                    <div className="relative w-full max-w-xs">
                      <select
                        id="model-select"
                        value={llmSettings.model}
                        onChange={(e) => handleModelChange(e.target.value)}
                        className="w-full appearance-none px-4 py-2.5 pr-10 bg-muted/30 border border-border rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                        aria-label="Select LLM model"
                      >
                        {models.length === 0 ? (
                          <option value="" disabled>
                            {loadingModels
                              ? "Loading models…"
                              : "No models found — is Ollama running?"}
                          </option>
                        ) : (
                          models.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))
                        )}
                      </select>
                      <ChevronDown className="w-4 h-4 text-muted-foreground absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    </div>
                  </div>
                </div>
              )}

              {/* ── Status + Action buttons ── */}
              <div className="mt-6 pt-5 border-t border-border flex flex-wrap items-center gap-3">
                {connectionStatusBadge}

                <div className="flex items-center gap-2 ml-auto flex-wrap">
                  <button
                    id="test-connection-btn"
                    onClick={handleTestConnection}
                    disabled={testing}
                    className="flex items-center gap-2 px-4 py-2 bg-muted/50 text-foreground text-sm font-medium rounded-xl hover:bg-muted transition-colors disabled:opacity-50 border border-border"
                  >
                    {testing ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : connectionStatus?.connected ? (
                      <Wifi className="w-3.5 h-3.5 text-emerald-500" />
                    ) : connectionStatus && !connectionStatus.connected ? (
                      <WifiOff className="w-3.5 h-3.5 text-red-400" />
                    ) : (
                      <Zap className="w-3.5 h-3.5" />
                    )}
                    Test Connection
                  </button>

                  <button
                    id="save-settings-btn"
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-md shadow-primary/20"
                  >
                    {saving ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Save className="w-3.5 h-3.5" />
                    )}
                    Save
                  </button>
                </div>
              </div>
            </div>

            {/* ========== Appearance ========== */}
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
                    <p className="text-xs text-muted-foreground">Clean &amp; bright</p>
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

            {/* ========== Language ========== */}
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

            {/* ========== API URL ========== */}
            <div className="bg-card border border-border rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-6">
                <Server className="w-4 h-4 text-emerald-500" />
                <h3 className="font-semibold text-foreground">API Configuration</h3>
              </div>
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

            {/* ========== Database Status ========== */}
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

            {/* ========== About ========== */}
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
                  <p className="font-medium text-foreground">2.0.0</p>
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
    </>
  );
}
