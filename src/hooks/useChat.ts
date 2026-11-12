import AsyncStorage from '@react-native-async-storage/async-storage';
import { useCallback, useEffect, useState } from 'react';
import { Alert } from 'react-native';
import { aiRepository } from '../repositories';
import { AIQuotaExceededError, ConversationMessage } from '../repositories/AIRepository';
import { recordActivity } from '../services/streakService';
import {
  enqueueQuestion,
  getQueue,
  removeFromQueue,
} from '../services/offlineQueue';
import { recordQuestion } from '../services/progressService';
import { Grade, Language, Message, ModelQuality, Subject } from '../types';

const CHAT_HISTORY_KEY = (subject: string, grade: number) =>
  `edureach:chat:${subject}:grade${grade}`;

function buildHistory(messages: Message[]): ConversationMessage[] {
  return messages
    .filter((m) => !m.pending)
    .map((m) => ({ role: m.role, content: m.content }));
}

interface UseChatParams {
  subject: Subject;
  grade: Grade;
  model: ModelQuality;
  language: Language;
  isOnline: boolean;
  deepThinking: boolean;
}

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  isQuizLoading: boolean;
  queueLength: number;
  quizAnswers: Record<string, Record<number, number>>;
  sendMessage: (text: string) => Promise<void>;
  clearHistory: () => Promise<void>;
  explainDifferently: () => Promise<void>;
  handleQuizMe: (messageId: string, explanation: string) => Promise<void>;
  handleQuizAnswer: (messageId: string, qIdx: number, oIdx: number) => void;
}

export function useChat({
  subject,
  grade,
  model,
  language,
  isOnline,
  deepThinking,
}: UseChatParams): UseChatReturn {
  const storageKey = CHAT_HISTORY_KEY(subject, grade);

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isQuizLoading, setIsQuizLoading] = useState(false);
  const [queueLength, setQueueLength] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState<
    Record<string, Record<number, number>>
  >({});

  // Load persisted chat history and pending queue count on mount
  useEffect(() => {
    AsyncStorage.getItem(storageKey).then((raw) => {
      if (raw) setMessages(JSON.parse(raw));
    });
    getQueue().then((q) =>
      setQueueLength(q.filter((i) => i.subject === subject).length),
    );
  }, [storageKey, subject]);

  // Persist messages whenever they change
  useEffect(() => {
    if (messages.length > 0)
      AsyncStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages, storageKey]);

  // Flush queued messages when coming back online
  useEffect(() => {
    if (!isOnline) return;
    (async () => {
      const queue = await getQueue();
      const sq = queue.filter(
        (q) => q.subject === subject && q.grade === grade,
      );
      if (!sq.length) return;
      for (const item of sq) {
        setMessages((prev) =>
          prev.map((m) => (m.id === item.id ? { ...m, pending: false } : m)),
        );
        try {
          const parsed = await aiRepository.ask({
            subject,
            grade,
            language,
            model,
            history: item.historySnapshot.map((m) => ({
              role: m.role === 'model' ? 'assistant' : 'user',
              content: m.parts[0]?.text ?? '',
            })),
            question: item.question,
            clientRequestId: item.id,
          });
          setMessages((prev) => [
            ...prev,
            {
              id: item.id + '-reply',
              role: 'assistant',
              content: parsed.answer,
              thinking: parsed.thinking ?? undefined,
              actualModel: parsed.actualModel,
              usedFallback: parsed.usedFallback,
              sources: parsed.sources,
              grounding: parsed.grounding,
              timestamp: Date.now(),
            },
          ]);
          await removeFromQueue(item.id);
          setQueueLength((n) => Math.max(0, n - 1));
        } catch (e) {
          console.warn('Flush failed:', e);
        }
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOnline]);

  const clearHistory = useCallback(async () => {
    Alert.alert('Clear chat?', 'All messages in this chat will be deleted.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Clear',
        style: 'destructive',
        onPress: async () => {
          await AsyncStorage.removeItem(storageKey);
          setMessages([]);
          setQuizAnswers({});
        },
      },
    ]);
  }, [storageKey]);

  const explainDifferently = useCallback(async () => {
    if (isLoading || !isOnline) return;
    setIsLoading(true);
    try {
      const parsed = await aiRepository.ask({
        subject,
        grade,
        language,
        model,
        history: buildHistory(messages),
        question: 'Please explain that differently using a different example or analogy.',
        deepThinking,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + '-re',
          role: 'assistant',
          content: parsed.answer,
          thinking: parsed.thinking ?? undefined,
          actualModel: parsed.actualModel,
          usedFallback: parsed.usedFallback,
              sources: parsed.sources,
              grounding: parsed.grounding,
          timestamp: Date.now(),
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-err`,
          role: 'assistant',
          timestamp: Date.now(),
          content:
            e instanceof AIQuotaExceededError
              ? "You've reached today's free AI limit. Come back tomorrow! 🌙"
              : "Sorry, I couldn't connect right now. Try again in a moment!",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, isOnline, messages, subject, grade, language, model, deepThinking]);

  const handleQuizMe = useCallback(
    async (messageId: string, explanation: string) => {
      if (isQuizLoading || !isOnline) return;
      setIsQuizLoading(true);
      try {
        const quiz = await aiRepository.generateQuiz({ subject, grade, language, explanation });
        setMessages((prev) =>
          prev.map((m) => (m.id === messageId ? { ...m, quiz } : m)),
        );
      } catch (e) {
        Alert.alert('Could not generate quiz', 'Try again in a moment.');
      } finally {
        setIsQuizLoading(false);
      }
    },
    [isQuizLoading, isOnline, subject, grade, language],
  );

  const handleQuizAnswer = useCallback(
    (messageId: string, qIdx: number, oIdx: number) => {
      setQuizAnswers((prev) => ({
        ...prev,
        [messageId]: { ...(prev[messageId] ?? {}), [qIdx]: oIdx },
      }));
    },
    [],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text || isLoading) return;

      const userMsg: Message = {
        id: `${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: Date.now(),
        pending: !isOnline,
      };
      setMessages((prev) => [...prev, userMsg]);
      await recordQuestion(subject, text);
      await recordActivity();

      if (!isOnline) {
        await enqueueQuestion(subject, grade, text, buildHistory(messages).map((m) => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: m.content }],
        })));
        setQueueLength((n) => n + 1);
        return;
      }

      setIsLoading(true);
      try {
        const parsed = await aiRepository.ask({
          subject,
          grade,
          language,
          model,
          history: buildHistory(messages),
          question: text,
          deepThinking,
        });
        setMessages((prev) => [
          ...prev,
          {
            id: `${Date.now()}-reply`,
            role: 'assistant',
            content: parsed.answer,
            thinking: parsed.thinking ?? undefined,
            actualModel: parsed.actualModel,
            usedFallback: parsed.usedFallback,
              sources: parsed.sources,
              grounding: parsed.grounding,
            timestamp: Date.now(),
          },
        ]);
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          {
            id: `${Date.now()}-err`,
            role: 'assistant',
            timestamp: Date.now(),
            content:
              e instanceof AIQuotaExceededError
                ? "You've reached today's free AI limit. Come back tomorrow! 🌙"
                : "Sorry, I couldn't connect right now. Try again in a moment!",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, isOnline, messages, subject, grade, language, model, deepThinking],
  );

  return {
    messages,
    isLoading,
    isQuizLoading,
    queueLength,
    quizAnswers,
    sendMessage,
    clearHistory,
    explainDifferently,
    handleQuizMe,
    handleQuizAnswer,
  };
}
