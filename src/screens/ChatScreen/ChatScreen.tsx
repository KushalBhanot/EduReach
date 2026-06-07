import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Clipboard,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChatInput } from '../../components/ChatInput/ChatInput';
import { ChatMessage } from '../../components/ChatMessage/ChatMessage';
import { OfflineBanner } from '../../components/OfflineBanner/OfflineBanner';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';
import {
  GemmaMessage,
  MODEL_CONFIG,
  LANGUAGE_CONFIG,
  QuotaExceededError,
  askGemma,
} from '../../services/gemmaService';
import { generateQuiz } from '../../services/quizService';
import { recordActivity } from '../../services/streakService';
import {
  enqueueQuestion,
  getQueue,
  removeFromQueue,
} from '../../services/offlineQueue';
import { recordQuestion } from '../../services/progressService';
import { ChatScreenProps, Message } from '../../types';
import {
  styles,
  BG,
  INDIGO,
  SURFACE,
  TEXT_HI,
  TEXT_LO,
} from './ChatScreen.styles';

const CHAT_HISTORY_KEY = (subject: string, grade: number) =>
  `edureach:chat:${subject}:grade${grade}`;

function buildGemmaHistory(messages: Message[]): GemmaMessage[] {
  return messages
    .filter((m) => !m.pending)
    .map((m) => ({
      role: m.role === 'user' ? 'user' : 'model',
      parts: [{ text: m.content }],
    }));
}

export function ChatScreen({ navigation, route }: ChatScreenProps) {
  const { subject, grade, model, language } = route.params;
  const { isOnline } = useNetworkStatus();
  const storageKey = CHAT_HISTORY_KEY(subject, grade);
  const isGemmaModel = MODEL_CONFIG[model].isGemma;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isQuizLoading, setIsQuizLoading] = useState(false);
  const [queueLength, setQueueLength] = useState(0);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deepThinking, setDeepThinking] = useState(false);
  const [expandedThinking, setExpandedThinking] = useState<
    Record<string, boolean>
  >({});
  const [quizAnswers, setQuizAnswers] = useState<
    Record<string, Record<number, number>>
  >({});
  const listRef = useRef<FlatList>(null);

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
          const parsed = await askGemma(
            subject,
            grade,
            language,
            model,
            item.historySnapshot,
            item.question,
          );
          setMessages((prev) => [
            ...prev,
            {
              id: item.id + '-reply',
              role: 'assistant',
              content: parsed.answer,
              thinking: parsed.thinking ?? undefined,
              actualModel: parsed.actualModel,
              usedFallback: parsed.usedFallback,
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

  const copyToClipboard = useCallback((text: string, id: string) => {
    Clipboard.setString(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const explainDifferently = useCallback(async () => {
    if (isLoading || !isOnline) return;
    setIsLoading(true);
    try {
      const parsed = await askGemma(
        subject,
        grade,
        language,
        model,
        buildGemmaHistory(messages),
        'Please explain that differently using a different example or analogy.',
        deepThinking,
      );
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + '-re',
          role: 'assistant',
          content: parsed.answer,
          thinking: parsed.thinking ?? undefined,
          actualModel: parsed.actualModel,
          usedFallback: parsed.usedFallback,
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
            e instanceof QuotaExceededError
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
        const quiz = await generateQuiz(subject, grade, language, explanation);
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

  const handleToggleThinking = useCallback((id: string) => {
    setExpandedThinking((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // Configure navigation header
  useEffect(() => {
    navigation.setOptions({
      title: `G${grade} · ${subject}`,
      headerStyle: { backgroundColor: BG },
      headerShadowVisible: false,
      headerTintColor: TEXT_HI,
      headerTitleStyle: { fontWeight: '800', color: TEXT_HI },
      headerRight: () => (
        <View style={styles.headerRight}>
          <Text style={styles.headerBadge}>
            {MODEL_CONFIG[model].emoji}
            {LANGUAGE_CONFIG[language].flag}
          </Text>
          {isGemmaModel && (
            <Switch
              value={deepThinking}
              onValueChange={setDeepThinking}
              trackColor={{ false: SURFACE, true: INDIGO + '80' }}
              thumbColor={deepThinking ? INDIGO : TEXT_LO}
              style={{ transform: [{ scaleX: 0.7 }, { scaleY: 0.7 }] }}
            />
          )}
          <View
            style={[
              styles.statusDot,
              { backgroundColor: isOnline ? '#10B981' : '#F59E0B' },
            ]}
          />
          <TouchableOpacity onPress={clearHistory} style={styles.clearBtn}>
            <Text style={styles.clearBtnText}>Clear</Text>
          </TouchableOpacity>
        </View>
      ),
    });
  }, [
    navigation,
    isOnline,
    clearHistory,
    grade,
    subject,
    model,
    language,
    deepThinking,
    isGemmaModel,
  ]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');

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
      await enqueueQuestion(subject, grade, text, buildGemmaHistory(messages));
      setQueueLength((n) => n + 1);
      return;
    }

    setIsLoading(true);
    try {
      const parsed = await askGemma(
        subject,
        grade,
        language,
        model,
        buildGemmaHistory(messages),
        text,
        deepThinking,
      );
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-reply`,
          role: 'assistant',
          content: parsed.answer,
          thinking: parsed.thinking ?? undefined,
          actualModel: parsed.actualModel,
          usedFallback: parsed.usedFallback,
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
            e instanceof QuotaExceededError
              ? "You've reached today's free AI limit. Come back tomorrow! 🌙"
              : "Sorry, I couldn't connect right now. Try again in a moment!",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, isOnline, messages, subject, grade, language, model, deepThinking]);

  const renderItem = useCallback(
    ({ item, index }: { item: Message; index: number }) => {
      const isLastAssistant =
        item.role !== 'user' &&
        messages.slice(index + 1).every((m) => m.role === 'user');
      return (
        <ChatMessage
          item={item}
          isLastAssistant={isLastAssistant}
          copiedId={copiedId}
          expandedThinking={expandedThinking}
          quizAnswers={quizAnswers}
          isQuizLoading={isQuizLoading}
          onCopy={copyToClipboard}
          onExplainDifferently={explainDifferently}
          onQuizMe={handleQuizMe}
          onQuizAnswer={handleQuizAnswer}
          onToggleThinking={handleToggleThinking}
        />
      );
    },
    [
      messages,
      copiedId,
      expandedThinking,
      quizAnswers,
      isQuizLoading,
      copyToClipboard,
      explainDifferently,
      handleQuizMe,
      handleQuizAnswer,
      handleToggleThinking,
    ],
  );

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      {!isOnline && <OfflineBanner queueLength={queueLength} />}

      {deepThinking && isGemmaModel && (
        <View style={styles.deepThinkingBanner}>
          <Text style={styles.deepThinkingText}>
            🧩 Deep Thinking ON — tap ▸ on any response to see reasoning
          </Text>
        </View>
      )}

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          keyboardShouldPersistTaps='handled'
          onContentSizeChange={() =>
            listRef.current?.scrollToEnd({ animated: true })
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <View style={styles.emptyIconBox}>
                <Text style={styles.emptyEmoji}>👋</Text>
              </View>
              <Text style={styles.emptyTitle}>
                Ask me anything about {subject}!
              </Text>
              <Text style={styles.emptySubtitle}>
                Grade {grade} · {MODEL_CONFIG[model].emoji}{' '}
                {MODEL_CONFIG[model].label} · {LANGUAGE_CONFIG[language].flag}{' '}
                {language}
              </Text>
            </View>
          }
        />

        {isLoading && (
          <View style={styles.typingRow}>
            <ActivityIndicator size='small' color={INDIGO} />
            <Text style={styles.typingText}>
              {deepThinking ? 'Thinking deeply...' : 'Thinking...'}
            </Text>
          </View>
        )}

        <ChatInput
          input={input}
          onChangeText={setInput}
          onSubmit={sendMessage}
          isLoading={isLoading}
          placeholder={`Ask a Grade ${grade} ${subject} question…`}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
