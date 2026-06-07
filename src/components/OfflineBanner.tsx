import React from 'react';
import { Text, View } from 'react-native';
import { OfflineBannerProps } from '../types';
import { styles } from './OfflineBanner.styles';

export function OfflineBanner({ queueLength }: OfflineBannerProps) {
  return (
    <View style={styles.banner}>
      <Text style={styles.icon}>📡</Text>
      <Text style={styles.text}>
        {queueLength > 0
          ? `Offline — ${queueLength} question${queueLength > 1 ? 's' : ''} queued`
          : 'Offline — questions will be sent when you reconnect'}
      </Text>
    </View>
  );
}

