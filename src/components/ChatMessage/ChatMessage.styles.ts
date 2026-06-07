import { StyleSheet } from 'react-native';

export const INDIGO = '#6366F1';
const BG = '#F4F4FA';
const SURFACE = '#EEEEF8';
const TEXT_HI = '#0F0F1A';
const TEXT_LO = '#9898B8';

export const styles = StyleSheet.create({
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
  copiedLabel: { fontSize: 11, color: '#10B981', marginTop: 4, fontWeight: '600' },

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
});
