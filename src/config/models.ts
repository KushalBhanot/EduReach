import { Language, ModelQuality } from '../types';

/**
 * UI labels for the three answer tiers. Which model serves each tier is decided
 * by the backend (backend/app/models.py), so a model change needs no app release.
 */
export const MODEL_CONFIG: Record<
  ModelQuality,
  { label: string; emoji: string; desc: string; supportsDeepThinking: boolean }
> = {
  fast: { emoji: '⚡', label: 'Fast', desc: 'Quick answers, less data', supportsDeepThinking: false },
  smart: { emoji: '🧠', label: 'Smart', desc: 'Deeper explanations', supportsDeepThinking: true },
  expert: { emoji: '🏆', label: 'Expert', desc: 'Most thorough answers', supportsDeepThinking: true },
};

export const LANGUAGE_CONFIG: Record<Language, { flag: string }> = {
  English: { flag: '🇬🇧' },
  Hindi: { flag: '🇮🇳' },
  Spanish: { flag: '🇪🇸' },
  Swahili: { flag: '🇰🇪' },
  French: { flag: '🇫🇷' },
  Bengali: { flag: '🇧🇩' },
};
