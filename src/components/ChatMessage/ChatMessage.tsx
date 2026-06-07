import React from 'react';
import {
  ActivityIndicator,
  Text,
  TouchableOpacity,
  TouchableWithoutFeedback,
  View,
} from 'react-native';
import { ChatMessageProps } from '../../types';
import { SimpleMarkdown } from '../SimpleMarkdown/SimpleMarkdown';
import { QuizCard } from '../QuizCard/QuizCard';
import { styles, INDIGO } from './ChatMessage.styles';

const MODEL_LABEL: Record<string, string> = {
  'gemini-2.5-flash': '⚡ Fast',
  'gemma-4-26b-a4b-it': '🧠 Smart',
  'gemma-4-31b-it': '🏆 Expert',
};

function formatTime(ts: number): string {
  const d = new Date(ts);
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  return `${h % 12 || 12}:${m} ${h >= 12 ? 'PM' : 'AM'}`;
}

export const ChatMessage = React.memo(function ChatMessage({
  item,
  isLastAssistant,
  copiedId,
  expandedThinking,
  quizAnswers,
  isQuizLoading,
  onCopy,
  onExplainDifferently,
  onQuizMe,
  onQuizAnswer,
  onToggleThinking,
}: ChatMessageProps) {
  const isUser = item.role === 'user';
  const isCopied = copiedId === item.id;
  const isThinkingExpanded = expandedThinking[item.id] ?? false;
  const msgQuizAnswers = quizAnswers[item.id] ?? {};

  return (
    <View
      style={[
        styles.messageGroup,
        isUser ? styles.messageGroupUser : styles.messageGroupAssistant,
      ]}
    >
      <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
        {!isUser && (
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>AI</Text>
          </View>
        )}
        <TouchableWithoutFeedback
          onLongPress={() => onCopy(item.content, item.id)}
        >
          <View
            style={[
              styles.bubble,
              isUser ? styles.bubbleUser : styles.bubbleAssistant,
              item.pending && styles.bubblePending,
              isCopied && styles.bubbleCopied,
            ]}
          >
            {item.thinking && (
              <TouchableOpacity
                onPress={() => onToggleThinking(item.id)}
                style={styles.thinkingHeader}
              >
                <Text style={styles.thinkingHeaderText}>
                  {isThinkingExpanded ? '▾' : '▸'} Thinking process...
                </Text>
              </TouchableOpacity>
            )}
            {item.actualModel && (
              <View
                style={[
                  styles.modelBadge,
                  item.usedFallback && styles.modelBadgeFallback,
                ]}
              >
                <Text
                  style={[
                    styles.modelBadgeText,
                    item.usedFallback && styles.modelBadgeTextFallback,
                  ]}
                >
                  {MODEL_LABEL[item.actualModel] ?? item.actualModel}
                  {item.usedFallback ? ' (Expert unavailable)' : ''}
                </Text>
              </View>
            )}
            {item.thinking && isThinkingExpanded && (
              <View style={styles.thinkingBody}>
                <Text style={styles.thinkingBodyText}>{item.thinking}</Text>
              </View>
            )}
            {isUser ? (
              <Text style={styles.bubbleTextUser}>{item.content}</Text>
            ) : (
              <SimpleMarkdown>{item.content}</SimpleMarkdown>
            )}
            {item.pending && (
              <Text style={styles.pendingLabel}>
                ⏳ Queued — will send when online
              </Text>
            )}
            {isCopied && <Text style={styles.copiedLabel}>✓ Copied</Text>}
          </View>
        </TouchableWithoutFeedback>
      </View>

      {item.quiz && (
        <View style={styles.quizWrapper}>
          <QuizCard
            quiz={item.quiz}
            answers={msgQuizAnswers}
            onAnswer={(qi, oi) => onQuizAnswer(item.id, qi, oi)}
          />
        </View>
      )}

      <View
        style={[
          styles.belowBubble,
          isUser ? styles.belowBubbleUser : styles.belowBubbleAssistant,
        ]}
      >
        <Text style={styles.timestamp}>{formatTime(item.timestamp)}</Text>
        {isLastAssistant && !item.pending && !item.quiz && (
          <View style={styles.actionRow}>
            <TouchableOpacity
              onPress={onExplainDifferently}
              style={styles.actionBtn}
            >
              <Text style={styles.actionBtnText}>↺ Explain differently</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => onQuizMe(item.id, item.content)}
              style={[styles.actionBtn, styles.actionBtnQuiz]}
              disabled={isQuizLoading}
            >
              {isQuizLoading ? (
                <ActivityIndicator size='small' color={INDIGO} />
              ) : (
                <Text style={[styles.actionBtnText, { color: INDIGO }]}>
                  🧩 Quiz me
                </Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>
    </View>
  );
});
