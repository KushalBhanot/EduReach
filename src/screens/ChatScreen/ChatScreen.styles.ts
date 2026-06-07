import { StyleSheet } from 'react-native';

export const BG = '#F4F4FA';
export const INDIGO = '#6366F1';
export const INDIGO_DK = '#4338CA';
export const INDIGO_BG = '#EEF2FF';
export const SURFACE = '#EEEEF8';
export const TEXT_HI = '#0F0F1A';
export const TEXT_LO = '#9898B8';

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

  typingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 8,
  },
  typingText: { fontSize: 13, fontWeight: '500', color: INDIGO },

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
