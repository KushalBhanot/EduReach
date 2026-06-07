import React from 'react';
import { Text, TextInput, TouchableOpacity, View } from 'react-native';
import { ChatInputProps } from '../../types';
import { styles, TEXT_LO } from './ChatInput.styles';

export function ChatInput({
  input,
  onChangeText,
  onSubmit,
  isLoading,
  placeholder,
}: ChatInputProps) {
  return (
    <View style={styles.inputRow}>
      <TextInput
        style={styles.input}
        value={input}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={TEXT_LO}
        multiline
        maxLength={400}
        returnKeyType='send'
        onSubmitEditing={onSubmit}
      />
      <TouchableOpacity
        style={[
          styles.sendBtn,
          (!input.trim() || isLoading) && styles.sendBtnDisabled,
        ]}
        onPress={onSubmit}
        disabled={!input.trim() || isLoading}
      >
        <Text style={styles.sendIcon}>↑</Text>
      </TouchableOpacity>
    </View>
  );
}
