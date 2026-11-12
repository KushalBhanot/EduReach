import AsyncStorage from '@react-native-async-storage/async-storage';
import { QuizQuestion } from '../types';
import {
  AIQuotaExceededError,
  AIRepository,
  AIResponse,
  AskParams,
  QuizParams,
} from './AIRepository';

/**
 * Talks to the EduReach API (backend/, FastAPI on Cloud Run).
 * The backend holds the Google credentials, so the app ships no API key;
 * the base URL is public by design.
 */
export const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');

const DEVICE_ID_KEY = 'edureach:device_id';
const TIMEOUT_MS = 30_000;

let deviceIdPromise: Promise<string> | null = null;

/** Random per-install id, used by the backend for rate limiting only. */
function getDeviceId(): Promise<string> {
  if (!deviceIdPromise) {
    deviceIdPromise = (async () => {
      const existing = await AsyncStorage.getItem(DEVICE_ID_KEY);
      if (existing) return existing;
      const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      await AsyncStorage.setItem(DEVICE_ID_KEY, id);
      return id;
    })();
  }
  return deviceIdPromise;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(API_BASE_URL + path, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Device-Id': await getDeviceId(),
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 429 && err.error === 'quota_exhausted') {
        throw new AIQuotaExceededError();
      }
      throw new Error(`EduReach API ${res.status}: ${err.error ?? 'unknown'} (${err.requestId ?? '-'})`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export const backendRepository: AIRepository = {
  async ask(params: AskParams): Promise<AIResponse> {
    const data = await post<AIResponse>('/v1/ask', {
      subject: params.subject,
      grade: params.grade,
      language: params.language,
      tier: params.model,
      history: params.history,
      question: params.question,
      deepThinking: params.deepThinking ?? false,
      clientRequestId: params.clientRequestId,
    });
    return {
      answer: data.answer,
      thinking: data.thinking,
      actualModel: data.actualModel,
      usedFallback: data.usedFallback,
      sources: data.sources ?? [],
      grounding: data.grounding ?? 'none',
    };
  },

  async generateQuiz(params: QuizParams): Promise<QuizQuestion[]> {
    const data = await post<{ questions: QuizQuestion[] }>('/v1/quiz', params);
    return data.questions;
  },
};
