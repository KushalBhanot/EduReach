import { StyleSheet } from 'react-native';

export const TEXT_LO = '#9898B8';
const BG = '#F4F4FA';
const INDIGO = '#6366F1';
const TEXT_HI = '#0F0F1A';

export const styles = StyleSheet.create({
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
});
