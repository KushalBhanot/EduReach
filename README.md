# EduReach 🌍

**Offline-First AI Tutor for Underserved Students**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) · Kaggle × Google DeepMind

---

## v2: textbook-grounded answers on Google Cloud

Math and Science answers for grades 6 to 10 now come from a Python RAG service on GCP and cite the textbook section they used. When the books don't cover a question, the answer says so.

```
Expo app ──HTTPS──▶ Cloud Run (FastAPI, Python)
                     ├─ embed question ── Vertex AI gemini-embedding-001 (768-d)
                     ├─ top-5 passages ── Cloud SQL Postgres + pgvector (HNSW), filtered by subject and grade
                     ├─ answer ───────── Vertex AI Gemini, with numbered passages; citations parsed into `sources`
                     └─ one JSON log line per request: grounding, chunk IDs, per-stage latency, tokens, cost
```

- **Corpus:** 3 OpenStax books (Prealgebra 2e, Elementary Algebra 2e, Concepts of Biology), 2,250 chunks, ingested with an idempotent loader that checks each book's license.
- **No API key in the app.** Cloud Run calls Vertex AI with its service account; the database URL lives in Secret Manager.
- **Measured** on 62 questions ([docs/results.md](docs/results.md)): a correct section in the top 3 for 50 of 50 answerable questions (including Hindi, Spanish and French), and all 12 questions the books don't cover labelled as not from the textbook. Retrieval adds about 25 ms of vector search. In a human review, 19 of 19 graded answers were correct and every cited answer was supported by its passages. The prompt was revised (v2) based on that review.
- **Cost guard:** a $20 Cloud Billing budget wired to a function that disables billing when it is reached (tested).

Backend code, ingestion, evals and deployment: [backend/README.md](backend/README.md) and [backend/deploy/GCP_SETUP.md](backend/deploy/GCP_SETUP.md).

---

## App Preview

📹 **Demo Video:** https://www.youtube.com/watch?v=wgvaXzi2Awg

### Home Screen

<p float="left">
  <img src="assets/screenshots/home_1.png" width="30%" />
  <img src="assets/screenshots/home_2.png" width="30%" />
</p>

### Chat

<p float="left">
  <img src="assets/screenshots/chat_1.png" width="30%" />
  <img src="assets/screenshots/chat_2.png" width="30%" />
</p>

### Quiz Me

<p float="left">
  <img src="assets/screenshots/quiz_1.png" width="30%" />
  <img src="assets/screenshots/quiz_2.png" width="30%" />
</p>

---

## The Problem

Powerful AI tutors exist, but they require stable internet, a modern device, and often cost money. This makes them useless for the 260 million children worldwide who are out of school, or the hundreds of millions in rural communities with unreliable connectivity.

EduReach is built for the students that current AI tools leave behind.

---

## Features

- 🎓 **Grade-adaptive tutoring** — Grades 1 to 10, each with a distinct pedagogical approach calibrated to the student's level
- 🌐 **6 languages** — English, Hindi, Spanish, Swahili, French, Bengali with native-language prompting, not translation
- 📡 **Offline-first queue** — Questions saved locally with full conversation context, auto-answered when connectivity returns
- 🤖 **Multi-model routing** — Fast (Gemini 2.5 Flash), Smart (Gemma 4 26B MoE), Expert (Gemma 4 31B)
- 🧩 **Deep Thinking mode** — Toggle Gemma 4 reasoning with a collapsible thinking accordion per response
- 🧪 **Quiz Me** — One tap generates 3 multiple-choice questions from any explanation, with instant feedback and scoring
- ↺ **Explain differently** — Re-teaches the same concept with a new analogy on one tap
- 🔥 **Daily streak** — Tracks consecutive learning days to build study habits
- 📋 **Copy on long-press** — Copy any message to clipboard
- 🔄 **Graceful model fallback** — Auto-retries with Smart if Expert is unavailable, shown transparently to the student
- 🏷️ **Model badge** — Every AI response shows which model answered it

---

## Design goals

**Works with poor connectivity.** Questions are saved locally with their conversation context and answered automatically when the connection returns. Model calls go to the Gemini API today. The tier config is set up so on-device Gemma 4 E2B/E4B can replace the cloud call later.

**Inclusive by default.** Native-language prompting in 6 languages and answers calibrated for grades 1 to 10.

**Built for learning, not just answers.** Grade-adaptive depth, Quiz Me for active recall, Explain differently for re-teaching, and a daily streak for habit formation.

---

## Architecture

```
EduReach/
├── src/
│   ├── screens/
│   │   ├── SubjectPickerScreen.tsx
│   │   └── ChatScreen.tsx
│   ├── repositories/             # AIRepository interface + BackendRepository (calls the API)
│   ├── config/models.ts          # Tier labels (the backend picks the actual models)
│   ├── services/
│   │   ├── streakService.ts      # Daily streak tracking
│   │   ├── offlineQueue.ts       # Queue with history snapshot and dedup
│   │   └── progressService.ts
│   ├── components/
│   │   ├── SimpleMarkdown.tsx
│   │   └── OfflineBanner.tsx
│   ├── hooks/
│   │   ├── useChat.ts            # Chat state, offline queue flush, quiz requests
│   │   └── useNetworkStatus.ts
│   └── navigation/AppNavigator.tsx
backend/                          # v2: FastAPI + RAG on Cloud Run (see backend/README.md)
```

**Offline queue flow**

A student asks a question with no internet. The question is saved to AsyncStorage alongside a snapshot of the conversation history at that moment. When NetInfo detects connectivity, the queue flushes in order using those saved snapshots, and each item is removed only after a confirmed API response.

**Multi-model routing**

The student picks a tier (Fast, Smart, Expert). The backend maps it to a model chain and falls back to the next model on 404, 429 or 5xx, and the app shows which model answered. In v1 this ran on the device. Gemma 4 reasoning output is parsed from channel tags and shown in a collapsible accordion.

**Quiz generation**

The student taps Quiz Me on any AI response. That explanation is sent to the backend's `/v1/quiz`, which uses Gemini structured output and validates every item. Three multiple-choice questions come back, displayed inline with A/B/C/D options, instant color feedback on each answer, and a score at the end.

---

## Gemma 4 Integration

v1 (hackathon) models below. v2's current tier map is in `backend/app/models.py`.

| Model  | ID                 | Use Case                            |
| ------ | ------------------ | ----------------------------------- |
| Fast   | gemini-2.5-flash   | Quick answers, low data             |
| Smart  | gemma-4-26b-a4b-it | Deeper explanations, MoE efficiency |
| Expert | gemma-4-31b-it     | Most thorough, advanced grades      |

The system prompt is assembled dynamically from five components: a language prefix, persona, subject and grade, a grade-specific instruction string (10 distinct strings, one per grade), and a math formatting rule that prevents LaTeX from appearing as raw symbols.

---

## Setup

```bash
git clone https://github.com/KushalBhanot/EduReach.git
cd EduReach
yarn install
echo "EXPO_PUBLIC_API_BASE_URL=http://localhost:8080" > .env.local
npx expo start
```

The app needs the backend running (see [backend/README.md](backend/README.md) to run it locally), or a deployed URL in `EXPO_PUBLIC_API_BASE_URL`. The app holds no API key. Press `a` for Android or `i` for iOS simulator.

---

## Social Impact

Target users are students in rural India, Sub-Saharan Africa, and Southeast Asia on low-end Android phones with intermittent 2G/3G connectivity. Private tutoring in India costs ₹500 to ₹2,000 per month. EduReach is free.

The offline queue is the core differentiator. A student can ask questions on the walk to school with no signal and get every answer automatically when they reach WiFi. No question is ever lost.

---

## Built By

**Kushal Bhanot**, MS CS student at USC
[LinkedIn](https://linkedin.com/in/kushalbhanot) · [GitHub](https://github.com/KushalBhanot)

---

## License

[CC-BY 4.0](LICENSE)
