import { Grade, Grounding, Language, ModelQuality, QuizQuestion, Source, Subject } from '../types';

/**
 * Provider-agnostic error thrown when the AI quota is exceeded.
 * Consumers catch this instead of any provider-specific error class.
 */
export class AIQuotaExceededError extends Error {
  constructor() {
    super('Daily AI quota exceeded');
    this.name = 'AIQuotaExceededError';
  }
}

/** A single message in a conversation, independent of any AI provider format. */
export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AskParams {
  subject: Subject;
  grade: Grade;
  language: Language;
  model: ModelQuality;
  history: ConversationMessage[];
  question: string;
  deepThinking?: boolean;
  /** Stable id for retries (the offline queue item id), so the backend can dedupe. */
  clientRequestId?: string;
}

export interface AIResponse {
  answer: string;
  thinking: string | null;
  actualModel: string;
  usedFallback?: boolean;
  /** Textbook passages the answer cites. Empty when nothing was cited. */
  sources?: Source[];
  grounding?: Grounding;
}

export interface QuizParams {
  subject: Subject;
  grade: Grade;
  language: Language;
  explanation: string;
}

/**
 * Contract that every AI provider implementation must satisfy.
 * The active implementation is chosen in repositories/index.ts
 * without touching any app logic.
 */
export interface AIRepository {
  ask(params: AskParams): Promise<AIResponse>;
  generateQuiz(params: QuizParams): Promise<QuizQuestion[]>;
}
