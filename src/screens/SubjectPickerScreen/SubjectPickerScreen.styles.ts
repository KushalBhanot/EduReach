import { StyleSheet } from 'react-native';

export const BG = '#F4F4FA';
export const SURFACE = '#EEEEF8';
export const CARD = '#FFFFFF';
export const INDIGO = '#6366F1';
export const INDIGO_DK = '#4338CA';
export const INDIGO_BG = '#EEF2FF';
export const TEXT_HI = '#0F0F1A';
export const TEXT_LO = '#9898B8';
export const BORDER = '#EEEEF0';

export const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: BG },
  scroll: { paddingHorizontal: 22, paddingBottom: 40 },

  hero: { paddingTop: 10, paddingBottom: 24 },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    marginBottom: 16,
  },
  brandDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: INDIGO },
  brandName: {
    fontSize: 11,
    fontWeight: '800',
    color: INDIGO,
    letterSpacing: 2.5,
    textTransform: 'uppercase',
  },
  heading: {
    fontSize: 32,
    fontWeight: '900',
    color: TEXT_HI,
    letterSpacing: -1,
    lineHeight: 38,
    marginBottom: 8,
  },
  headingAccent: { color: INDIGO },
  sub: { fontSize: 13, color: TEXT_LO, lineHeight: 20 },

  sectionLabel: {
    fontSize: 11,
    fontWeight: '800',
    color: TEXT_LO,
    letterSpacing: 1.3,
    textTransform: 'uppercase',
    marginBottom: 10,
  },

  pillRow: { gap: 8, paddingRight: 4 },

  gradePill: {
    width: 46,
    height: 46,
    borderRadius: 14,
    backgroundColor: SURFACE,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: 'transparent',
  },
  gradePillOn: { backgroundColor: INDIGO_BG, borderColor: INDIGO },
  gradePillText: { fontSize: 15, fontWeight: '700', color: TEXT_LO },
  gradePillTextOn: { color: INDIGO_DK },

  langPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 24,
    backgroundColor: SURFACE,
    borderWidth: 1.5,
    borderColor: 'transparent',
  },
  langPillOn: { backgroundColor: INDIGO_BG, borderColor: INDIGO },
  langFlag: { fontSize: 18 },
  langText: { fontSize: 13, fontWeight: '600', color: TEXT_LO },
  langTextOn: { color: INDIGO_DK },

  modelRow: { flexDirection: 'row', gap: 10 },
  modelCard: {
    flex: 1,
    borderRadius: 16,
    padding: 12,
    alignItems: 'center',
    backgroundColor: SURFACE,
    borderWidth: 1.5,
    borderColor: 'transparent',
  },
  modelCardOn: { backgroundColor: INDIGO_BG, borderColor: INDIGO },
  modelEmoji: { fontSize: 22, marginBottom: 4 },
  modelLabel: {
    fontSize: 12,
    fontWeight: '800',
    color: TEXT_HI,
    marginBottom: 2,
  },
  modelLabelOn: { color: INDIGO_DK },
  modelDesc: {
    fontSize: 10,
    color: TEXT_LO,
    textAlign: 'center',
    lineHeight: 14,
  },

  subjectHeadRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 28,
    marginBottom: 14,
  },
  subjectHeadTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: TEXT_HI,
    letterSpacing: -0.3,
  },
  subjectHeadHint: { fontSize: 13, color: TEXT_LO, fontWeight: '500' },

  subjectCard: {
    backgroundColor: CARD,
    borderRadius: 20,
    padding: 16,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    borderWidth: 1,
    borderColor: BORDER,
    shadowColor: INDIGO,
    shadowOpacity: 0.07,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  subjectIcon: {
    width: 52,
    height: 52,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  subjectEmoji: { fontSize: 26 },
  subjectBody: { flex: 1 },
  subjectName: {
    fontSize: 17,
    fontWeight: '800',
    color: TEXT_HI,
    marginBottom: 3,
    letterSpacing: -0.2,
  },
  subjectDesc: {
    fontSize: 12,
    color: TEXT_LO,
    lineHeight: 17,
    marginBottom: 5,
  },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  badgeText: { fontSize: 11, fontWeight: '700' },
  subjectArrow: { fontSize: 26, color: '#D4D0F0', marginRight: 2 },

  streakBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: '#FFF7ED',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 5,
    alignSelf: 'flex-start',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#FED7AA',
  },
  streakFire: { fontSize: 14 },
  streakText: { fontSize: 12, fontWeight: '700', color: '#C2410C' },

  footer: {
    backgroundColor: CARD,
    borderRadius: 16,
    padding: 14,
    marginTop: 6,
    borderWidth: 1,
    borderColor: BORDER,
  },
  footerText: {
    fontSize: 13,
    color: TEXT_LO,
    lineHeight: 20,
    textAlign: 'center',
  },
});
