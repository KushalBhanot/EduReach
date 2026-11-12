import { AIRepository } from './AIRepository';
import { API_BASE_URL, backendRepository } from './BackendRepository';

if (!API_BASE_URL) {
  // v2 has no direct-to-Gemini path: the app never holds a provider key.
  // Local dev: EXPO_PUBLIC_API_BASE_URL=http://localhost:8080 (see backend/README.md).
  console.warn('EXPO_PUBLIC_API_BASE_URL is not set; AI requests will fail.');
}

/** The active AI repository: the EduReach backend (backend/, FastAPI on Cloud Run). */
export const aiRepository: AIRepository = backendRepository;
