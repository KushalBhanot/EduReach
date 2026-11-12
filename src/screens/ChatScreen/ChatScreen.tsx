import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
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
import { useChat } from '../../hooks/useChat';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';
import { LANGUAGE_CONFIG, MODEL_CONFIG } from '../../config/models';
import { ChatScreenProps, Message } from '../../types';
import {
  BG,
  INDIGO,
  SURFACE,
  TEXT_HI,
  TEXT_LO,
  styles,
} from './ChatScreen.styles';

export function ChatScreen({ navigation, route }: ChatScreenProps) {
  const { subject, grade, model, language } = route.params;
  const { isOnline } = useNetworkStatus();
  const showDeepThinking = MODEL_CONFIG[model].supportsDeepThinking;
  const listRef = useRef<FlatList>(null);

  // UI-only state
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deepThinking, setDeepThinking] = useState(false);
  const [expandedThinking, setExpandedThinking] = useState<
    Record<string, boolean>
  >({});

  // All chat domain logic
  const {
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
  } = useChat({ subject, grade, model, language, isOnline, deepThinking });

  const copyToClipboard = useCallback((text: string, id: string) => {
    Clipboard.setString(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const handleToggleThinking = useCallback((id: string) => {
    setExpandedThinking((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const handleSendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text) return;
    setInput('');
    await sendMessage(text);
  }, [input, sendMessage]);

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
          {showDeepThinking && (
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
    showDeepThinking,
  ]);

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

      {deepThinking && showDeepThinking && (
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
          onSubmit={handleSendMessage}
          isLoading={isLoading}
          placeholder={`Ask a Grade ${grade} ${subject} question…`}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
