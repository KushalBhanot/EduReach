import React, { useEffect, useState } from 'react';
import {
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MODEL_CONFIG, LANGUAGE_CONFIG } from '../services/gemmaService';
import { getProgress } from '../services/progressService';
import { getStreak } from '../services/streakService';
import {
  Grade,
  Language,
  ModelQuality,
  ProgressEntry,
  StreakData,
  Subject,
  SubjectPickerScreenProps,
} from '../types';
import { styles, INDIGO_DK } from './SubjectPickerScreen.styles';

const SUBJECTS: {
  key: Subject;
  emoji: string;
  iconBg: string;
  badgeBg: string;
  badgeText: string;
  desc: string;
}[] = [
  {
    key: 'Math',
    emoji: '➕',
    iconBg: '#EEF2FF',
    badgeBg: '#EEF2FF',
    badgeText: INDIGO_DK,
    desc: 'Numbers, fractions & geometry',
  },
  {
    key: 'Science',
    emoji: '🔬',
    iconBg: '#ECFDF5',
    badgeBg: '#ECFDF5',
    badgeText: '#065F46',
    desc: 'Plants, animals, space & experiments',
  },
  {
    key: 'English',
    emoji: '📖',
    iconBg: '#FFF7ED',
    badgeBg: '#FFF7ED',
    badgeText: '#9A3412',
    desc: 'Reading, writing & vocabulary',
  },
];

const GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as Grade[];
const LANGUAGES = Object.keys(LANGUAGE_CONFIG) as Language[];
const MODELS = Object.keys(MODEL_CONFIG) as ModelQuality[];

export function SubjectPickerScreen({ navigation }: SubjectPickerScreenProps) {
  const [selectedGrade, setSelectedGrade] = useState<Grade>(5);
  const [selectedModel, setSelectedModel] = useState<ModelQuality>('fast');
  const [selectedLang, setSelectedLang] = useState<Language>('English');
  const [progress, setProgress] = useState<Record<
    Subject,
    ProgressEntry
  > | null>(null);
  const [streak, setStreak] = useState<StreakData | null>(null);

  useEffect(() => {
    getProgress().then(setProgress);
    getStreak().then(setStreak);
  }, []);

  const go = (subject: Subject) =>
    navigation.navigate('Chat', {
      subject,
      grade: selectedGrade,
      model: selectedModel,
      language: selectedLang,
    });

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
      >
        {/* Brand + hero */}
        <View style={styles.hero}>
          <View style={styles.brandRow}>
            <View style={styles.brandDot} />
            <Text style={styles.brandName}>EduReach</Text>
          </View>
          {streak && streak.currentStreak > 0 && (
            <View style={styles.streakBadge}>
              <Text style={styles.streakFire}>🔥</Text>
              <Text style={styles.streakText}>
                {streak.currentStreak} day streak
              </Text>
            </View>
          )}
          <Text style={styles.heading}>
            Learn <Text style={styles.headingAccent}>anything,</Text>
            {'\n'}anywhere.
          </Text>
          <Text style={styles.sub}>
            Grades 1–10 · 6 languages · works even offline ✦
          </Text>
        </View>

        {/* Grade */}
        <Text style={styles.sectionLabel}>Your Grade</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.pillRow}
        >
          {GRADES.map((g) => (
            <TouchableOpacity
              key={g}
              style={[
                styles.gradePill,
                selectedGrade === g && styles.gradePillOn,
              ]}
              onPress={() => setSelectedGrade(g)}
            >
              <Text
                style={[
                  styles.gradePillText,
                  selectedGrade === g && styles.gradePillTextOn,
                ]}
              >
                {g}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Language */}
        <Text style={[styles.sectionLabel, { marginTop: 22 }]}>Language</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.pillRow}
        >
          {LANGUAGES.map((lang) => (
            <TouchableOpacity
              key={lang}
              style={[
                styles.langPill,
                selectedLang === lang && styles.langPillOn,
              ]}
              onPress={() => setSelectedLang(lang)}
            >
              <Text style={styles.langFlag}>{LANGUAGE_CONFIG[lang].flag}</Text>
              <Text
                style={[
                  styles.langText,
                  selectedLang === lang && styles.langTextOn,
                ]}
              >
                {lang}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Tutor speed */}
        <Text style={[styles.sectionLabel, { marginTop: 22 }]}>
          Tutor Speed
        </Text>
        <View style={styles.modelRow}>
          {MODELS.map((m) => {
            const cfg = MODEL_CONFIG[m];
            const on = selectedModel === m;
            return (
              <TouchableOpacity
                key={m}
                style={[styles.modelCard, on && styles.modelCardOn]}
                onPress={() => setSelectedModel(m)}
              >
                <Text style={styles.modelEmoji}>{cfg.emoji}</Text>
                <Text style={[styles.modelLabel, on && styles.modelLabelOn]}>
                  {cfg.label}
                </Text>
                <Text style={styles.modelDesc}>{cfg.desc}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Subject heading */}
        <View style={styles.subjectHeadRow}>
          <Text style={styles.subjectHeadTitle}>Choose a Subject</Text>
          <Text style={styles.subjectHeadHint}>tap to start →</Text>
        </View>

        {/* Subject cards */}
        {SUBJECTS.map((s) => {
          const count = progress?.[s.key]?.messageCount ?? 0;
          return (
            <TouchableOpacity
              key={s.key}
              style={styles.subjectCard}
              onPress={() => go(s.key)}
              activeOpacity={0.8}
            >
              <View style={[styles.subjectIcon, { backgroundColor: s.iconBg }]}>
                <Text style={styles.subjectEmoji}>{s.emoji}</Text>
              </View>
              <View style={styles.subjectBody}>
                <Text style={styles.subjectName}>{s.key}</Text>
                <Text style={styles.subjectDesc}>{s.desc}</Text>
                {count > 0 && (
                  <View style={[styles.badge, { backgroundColor: s.badgeBg }]}>
                    <Text style={[styles.badgeText, { color: s.badgeText }]}>
                      🔥 {count} question{count !== 1 ? 's' : ''} asked
                    </Text>
                  </View>
                )}
              </View>
              <Text style={styles.subjectArrow}>›</Text>
            </TouchableOpacity>
          );
        })}

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            💡 Questions save offline and answer when you reconnect
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

