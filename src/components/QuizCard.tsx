import React from 'react';
import { Text, TouchableOpacity, View } from 'react-native';
import { QuizQuestion } from '../types';
import {
  styles,
  SURFACE,
  INDIGO,
  INDIGO_DK,
  INDIGO_BG,
  TEXT_HI,
} from './QuizCard.styles';

interface QuizCardProps {
  quiz: QuizQuestion[];
  answers: Record<number, number>;
  onAnswer: (qIdx: number, oIdx: number) => void;
}

export const QuizCard = React.memo(function QuizCard({
  quiz,
  answers,
  onAnswer,
}: QuizCardProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.header}>🧩 Quick Quiz</Text>
      {quiz.map((q, qi) => {
        const chosen = answers[qi];
        const answered = chosen !== undefined;
        return (
          <View key={qi} style={styles.questionBlock}>
            <Text style={styles.questionText}>
              {qi + 1}. {q.question}
            </Text>
            {q.options.map((opt, oi) => {
              const isChosen = chosen === oi;
              const isCorrect = oi === q.correctIndex;
              let bg = SURFACE;
              let border = 'transparent';
              let textColor = TEXT_HI;
              if (answered) {
                if (isCorrect) {
                  bg = '#ECFDF5';
                  border = '#10B981';
                  textColor = '#065F46';
                } else if (isChosen) {
                  bg = '#FEF2F2';
                  border = '#EF4444';
                  textColor = '#991B1B';
                }
              } else if (isChosen) {
                bg = INDIGO_BG;
                border = INDIGO;
                textColor = INDIGO_DK;
              }
              return (
                <TouchableOpacity
                  key={oi}
                  style={[
                    styles.option,
                    { backgroundColor: bg, borderColor: border },
                  ]}
                  onPress={() => !answered && onAnswer(qi, oi)}
                  disabled={answered}
                  activeOpacity={0.75}
                >
                  <Text style={[styles.optionLabel, { color: textColor }]}>
                    {String.fromCharCode(65 + oi)}
                  </Text>
                  <Text style={[styles.optionText, { color: textColor }]}>
                    {opt}
                  </Text>
                  {answered && isCorrect && (
                    <Text style={styles.tick}>✓</Text>
                  )}
                  {answered && isChosen && !isCorrect && (
                    <Text style={styles.cross}>✗</Text>
                  )}
                </TouchableOpacity>
              );
            })}
            {answered && (
              <Text style={styles.explanation}>💡 {q.explanation}</Text>
            )}
          </View>
        );
      })}
      {Object.keys(answers).length === quiz.length && (
        <View style={styles.scoreRow}>
          <Text style={styles.scoreText}>
            {
              Object.entries(answers).filter(
                ([qi, oi]) => oi === quiz[Number(qi)].correctIndex,
              ).length
            }
            /{quiz.length} correct 🎉
          </Text>
        </View>
      )}
    </View>
  );
});
