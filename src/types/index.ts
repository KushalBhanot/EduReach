import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';

export type Subject = 'Math' | 'Science' | 'English';

export type Grade = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;

export type ModelQuality = 'fast' | 'smart' | 'expert';

export type Language =
  | 'English'
  | 'Hindi'
  | 'Spanish'
  | 'Swahili'
  | 'French'
  | 'Bengali';

export type MessageRole = 'user' | 'assistant';

export interface QuizQuestion {
  question: string;
  options: [string, string, string, string];
  correctIndex: number;
  explanation: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  pending?: boolean;
  thinking?: string;
  actualModel?: string;
  usedFallback?: boolean;
  quiz?: QuizQuestion[]; // populated when this message has a quiz attached
  quizAnswers?: Record<number, number>; // questionIndex -> chosen option index
}

export interface QueuedQuestion {
  id: string;
  subject: Subject;
  grade: Grade;
  question: string;
  timestamp: number;
  historySnapshot: import('../services/gemmaService').GemmaMessage[];
}

export interface ProgressEntry {
  subject: Subject;
  topicsAsked: string[];
  messageCount: number;
  lastActive: number;
}

export interface StreakData {
  currentStreak: number;
  longestStreak: number;
  lastActiveDate: string; // YYYY-MM-DD
  totalDays: number;
}

export type RootStackParamList = {
  SubjectPicker: undefined;
  Chat: {
    subject: Subject;
    grade: Grade;
    model: ModelQuality;
    language: Language;
  };
};

export type ChatScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Chat'>;
  route: RouteProp<RootStackParamList, 'Chat'>;
};

export type SubjectPickerScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'SubjectPicker'>;
};

export interface SimpleMarkdownProps {
  children: string;
  color?: string;
}

export interface OfflineBannerProps {
  queueLength: number;
}

export interface QuizCardProps {
  quiz: QuizQuestion[];
  answers: Record<number, number>;
  onAnswer: (qIdx: number, oIdx: number) => void;
}

export interface ChatMessageProps {
  item: Message;
  isLastAssistant: boolean;
  copiedId: string | null;
  expandedThinking: Record<string, boolean>;
  quizAnswers: Record<string, Record<number, number>>;
  isQuizLoading: boolean;
  onCopy: (text: string, id: string) => void;
  onExplainDifferently: () => void;
  onQuizMe: (messageId: string, explanation: string) => void;
  onQuizAnswer: (messageId: string, qIdx: number, oIdx: number) => void;
  onToggleThinking: (id: string) => void;
}

export interface ChatInputProps {
  input: string;
  onChangeText: (text: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  placeholder: string;
}
