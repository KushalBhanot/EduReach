import { StyleSheet } from 'react-native';

export const BG = '#F4F4FA';
export const INDIGO = '#6366F1';
export const INDIGO_DK = '#4338CA';
export const INDIGO_BG = '#EEF2FF';
export const SURFACE = '#EEEEF8';
export const TEXT_HI = '#0F0F1A';
export const TEXT_LO = '#9898B8';

export const quizStyles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: '#EEEEF0',
    shadowColor: INDIGO,
    shadowOpacity: 0.07,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  header: { fontSize: 14, fontWeight: '800', color: TEXT_HI, marginBottom: 12 },
  questionBlock: { marginBottom: 14 },
  questionText: {
    fontSize: 13,
    fontWeight: '700',
    color: TEXT_HI,
    marginBottom: 8,
    lineHeight: 19,
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderRadius: 10,
    padding: 10,
    marginBottom: 6,
    borderWidth: 1.5,
  },
  optionLabel: { fontSize: 12, fontWeight: '800', width: 18 },
  optionText: { fontSize: 12, flex: 1, lineHeight: 17 },
  tick: { fontSize: 14, color: '#10B981' },
  cross: { fontSize: 14, color: '#EF4444' },
  explanation: {
    fontSize: 11,
    color: TEXT_LO,
    marginTop: 6,
    lineHeight: 16,
    fontStyle: 'italic',
  },
  scoreRow: {
    borderTopWidth: 1,
    borderTopColor: '#EEEEF0',
    paddingTop: 10,
    marginTop: 4,
    alignItems: 'center',
  },
  scoreText: { fontSize: 14, fontWeight: '800', color: INDIGO },
});

export const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: BG },
  list: { padding: 16, paddingBottom: 8, gap: 4 },

  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginRight: 2,
  },
  headerBadge: { fontSize: 16 },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginLeft: 2 },
  clearBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: SURFACE,
    borderRadius: 8,
    marginLeft: 2,
  },
  clearBtnText: { fontSize: 12, color: TEXT_LO, fontWeight: '600' },

  deepThinkingBanner: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: INDIGO_BG,
  },
  deepThinkingText: { fontSize: 12, fontWeight: '600', color: INDIGO_DK },

  messageGroup: { marginBottom: 8 },
  messageGroupUser: { alignItems: 'flex-end' },
  messageGroupAssistant: { alignItems: 'flex-start' },
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  rowUser: { justifyContent: 'flex-end' },
  rowAssistant: { justifyContent: 'flex-start' },

  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: INDIGO,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { color: '#fff', fontSize: 11, fontWeight: '800' },

  bubble: {
    maxWidth: '78%',
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  bubbleUser: { backgroundColor: INDIGO, borderBottomRightRadius: 4 },
  bubbleAssistant: {
    backgroundColor: '#FFFFFF',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: '#EEEEF0',
    shadowColor: INDIGO,
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  bubblePending: { opacity: 0.6 },
  bubbleCopied: { opacity: 0.75 },
  bubbleTextUser: { fontSize: 15, color: '#FFFFFF', lineHeight: 22 },
  pendingLabel: { fontSize: 11, color: 'rgba(255,255,255,0.7)', marginTop: 4 },
  copiedLabel: {
    fontSize: 11,
    color: '#10B981',
    marginTop: 4,
    fontWeight: '600',
  },

  thinkingHeader: {
    paddingVertical: 6,
    marginBottom: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#EEEEF8',
  },
  thinkingHeaderText: {
    fontSize: 12,
    color: TEXT_LO,
    fontWeight: '600',
    fontStyle: 'italic',
  },
  thinkingBody: {
    backgroundColor: BG,
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
  },
  thinkingBodyText: {
    fontSize: 12,
    color: TEXT_LO,
    lineHeight: 18,
    fontStyle: 'italic',
  },

  modelBadge: {
    alignSelf: 'flex-start',
    backgroundColor: SURFACE,
    borderRadius: 6,
    paddingHorizontal: 7,
    paddingVertical: 3,
    marginBottom: 6,
  },
  modelBadgeFallback: { backgroundColor: '#FEF3C7' },
  modelBadgeText: { fontSize: 11, color: TEXT_LO, fontWeight: '600' },
  modelBadgeTextFallback: { color: '#92400E' },

  quizWrapper: {
    marginTop: 8,
    width: '90%',
    alignSelf: 'flex-start',
    marginLeft: 40,
  },

  belowBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 4,
    paddingHorizontal: 4,
  },
  belowBubbleUser: { justifyContent: 'flex-end' },
  belowBubbleAssistant: { marginLeft: 40 },
  timestamp: { fontSize: 11, color: TEXT_LO },

  actionRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  actionBtn: { paddingVertical: 3, paddingHorizontal: 2 },
  actionBtnQuiz: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  actionBtnText: { fontSize: 12, fontWeight: '600', color: INDIGO },

  typingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 8,
  },
  typingText: { fontSize: 13, fontWeight: '500', color: INDIGO },

  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 10,
    padding: 12,
    paddingBottom: 16,
    borderTopWidth: 1,
    borderTopColor: '#EEEEF0',
    backgroundColor: BG,
  },
  input: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    borderWidth: 1,
    borderColor: '#EEEEF0',
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    color: TEXT_HI,
    maxHeight: 120,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: INDIGO,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: { opacity: 0.35 },
  sendIcon: { color: '#fff', fontSize: 20, fontWeight: '700' },

  empty: { flex: 1, alignItems: 'center', paddingTop: 80, gap: 10 },
  emptyIconBox: {
    width: 72,
    height: 72,
    borderRadius: 22,
    backgroundColor: INDIGO_BG,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  emptyEmoji: { fontSize: 36 },
  emptyTitle: { fontSize: 18, fontWeight: '800', color: TEXT_HI },
  emptySubtitle: { fontSize: 13, color: TEXT_LO },
});
