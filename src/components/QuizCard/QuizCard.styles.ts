import { StyleSheet } from 'react-native';

export const SURFACE = '#EEEEF8';
export const INDIGO = '#6366F1';
export const INDIGO_DK = '#4338CA';
export const INDIGO_BG = '#EEF2FF';
export const TEXT_HI = '#0F0F1A';
export const TEXT_LO = '#9898B8';

export const styles = StyleSheet.create({
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
