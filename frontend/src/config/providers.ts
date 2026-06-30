/**
 * providers.ts — Single source of truth for all AI provider configuration.
 *
 * Import this wherever provider metadata, model lists, icons, or website
 * links are needed. Never duplicate this data elsewhere.
 */

import type { AnyProvider, CloudProvider } from "@/store/appStore";

// ---------------------------------------------------------------------------
// Curated model lists — production-ready, hand-picked
// ---------------------------------------------------------------------------

export const PROVIDER_MODELS: Record<AnyProvider, string[]> = {
  groq: [
    "qwen/qwen3-32b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b",
    "gemma2-9b-it",
  ],
  openai: [
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
  ],
  gemini: [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
  ],
  anthropic: [
    "claude-opus-4",
    "claude-sonnet-4",
    "claude-haiku-4",
  ],
  openrouter: [
    "deepseek/deepseek-r1",
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "google/gemini-flash-1.5",
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
  ],
  // Ollama models are discovered dynamically via GET /api/tags
  ollama: [],
};

// Default model per provider — first entry in the curated list
export const PROVIDER_DEFAULT_MODEL: Record<AnyProvider, string> = {
  groq: PROVIDER_MODELS.groq[0],
  openai: PROVIDER_MODELS.openai[0],
  gemini: PROVIDER_MODELS.gemini[0],
  anthropic: PROVIDER_MODELS.anthropic[0],
  openrouter: PROVIDER_MODELS.openrouter[0],
  ollama: "llama3:latest",
};

// ---------------------------------------------------------------------------
// Provider metadata
// ---------------------------------------------------------------------------

export interface ProviderInfo {
  /** Canonical identifier matching backend keys */
  id: AnyProvider;
  /** Human-readable short name */
  label: string;
  /** One-line tagline shown in the dropdown */
  tagline: string;
  /** Emoji icon (used as fallback when SVG unavailable) */
  emoji: string;
  /** Tailwind text colour for the provider */
  color: string;
  /** Tailwind gradient for icon backgrounds */
  gradient: string;
  /** Feature bullet points shown in the info panel */
  features: string[];
  /** Official website URL */
  website: string;
  /** Whether this provider requires an API key */
  requiresApiKey: boolean;
  /** Whether models for this provider are fetched from the backend */
  dynamicModels: boolean;
}

export const PROVIDER_INFO: Record<AnyProvider, ProviderInfo> = {
  groq: {
    id: "groq",
    label: "Groq",
    tagline: "Ultra-fast inference",
    emoji: "⚡",
    color: "text-orange-500",
    gradient: "from-orange-500 to-amber-600",
    features: [
      "⚡ Very fast inference",
      "✓ Free tier available",
      "✓ Excellent for SQL generation",
    ],
    website: "https://console.groq.com",
    requiresApiKey: true,
    dynamicModels: false,
  },
  openai: {
    id: "openai",
    label: "OpenAI",
    tagline: "Industry-leading reasoning",
    emoji: "🤖",
    color: "text-emerald-500",
    gradient: "from-emerald-500 to-teal-600",
    features: [
      "🤖 Industry-leading reasoning",
      "✓ GPT-5 models",
      "✓ Broad tool & function calling support",
    ],
    website: "https://platform.openai.com",
    requiresApiKey: true,
    dynamicModels: false,
  },
  gemini: {
    id: "gemini",
    label: "Google Gemini",
    tagline: "Large context window",
    emoji: "💎",
    color: "text-blue-500",
    gradient: "from-blue-500 to-indigo-600",
    features: [
      "💎 Large context window",
      "✓ Strong multimodal capabilities",
      "✓ Gemini 2.5 Pro & Flash",
    ],
    website: "https://aistudio.google.com",
    requiresApiKey: true,
    dynamicModels: false,
  },
  anthropic: {
    id: "anthropic",
    label: "Anthropic",
    tagline: "Excellent coding & reasoning",
    emoji: "🧠",
    color: "text-violet-500",
    gradient: "from-violet-500 to-purple-600",
    features: [
      "🧠 Excellent coding and reasoning",
      "✓ Claude models",
      "✓ Strong instruction following",
    ],
    website: "https://console.anthropic.com",
    requiresApiKey: true,
    dynamicModels: false,
  },
  openrouter: {
    id: "openrouter",
    label: "OpenRouter",
    tagline: "Access hundreds of models",
    emoji: "🌐",
    color: "text-rose-500",
    gradient: "from-rose-500 to-pink-600",
    features: [
      "🌐 Access hundreds of models",
      "✓ Multiple providers via one API",
      "✓ Pay-per-use pricing",
    ],
    website: "https://openrouter.ai",
    requiresApiKey: true,
    dynamicModels: true,
  },
  ollama: {
    id: "ollama",
    label: "Ollama",
    tagline: "Fully local execution",
    emoji: "💻",
    color: "text-teal-500",
    gradient: "from-teal-500 to-emerald-600",
    features: [
      "💻 Fully local execution",
      "✓ Privacy focused",
      "✓ No API key required",
    ],
    website: "https://ollama.com",
    requiresApiKey: false,
    dynamicModels: true,
  },
};

/** Cloud-only providers for the Settings dropdown */
export const CLOUD_PROVIDER_IDS: CloudProvider[] = [
  "groq",
  "openai",
  "gemini",
  "anthropic",
  "openrouter",
];

export const CLOUD_PROVIDER_LIST = CLOUD_PROVIDER_IDS.map(
  (id) => PROVIDER_INFO[id] as ProviderInfo & { id: CloudProvider }
);
