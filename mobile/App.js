import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, SafeAreaView, TouchableOpacity } from 'react-native';

export default function App() {
  const [riskLevel, setRiskLevel] = useState('LOW');
  
  // Simulated socket hook update
  useEffect(() => {
    // socket.on('anomaly')
  }, []);

  const getRiskColor = () => {
    switch (riskLevel) {
      case 'LOW': return '#10B981';
      case 'MEDIUM': return '#F59E0B';
      case 'HIGH': return '#EF4444';
      case 'CRITICAL': return '#991B1B';
      default: return '#10B981';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>ShieldCloud</Text>
        <Text style={styles.subtitle}>PQC SECURED</Text>
      </View>

      <View style={[styles.card, { borderColor: getRiskColor() }]}>
        <Text style={styles.cardTitle}>System Risk Level</Text>
        <Text style={[styles.riskText, { color: getRiskColor() }]}>{riskLevel}</Text>
        <Text style={styles.cardDesc}>End-to-end Kyber connections active</Text>
      </View>
      
      <View style={styles.statsGrid}>
        <View style={styles.statBox}>
          <Text style={styles.statVal}>45.2GB</Text>
          <Text style={styles.statLabel}>Storage</Text>
        </View>
        <View style={styles.statBox}>
          <Text style={styles.statVal}>1.2K</Text>
          <Text style={styles.statLabel}>Files</Text>
        </View>
      </View>

      <TouchableOpacity style={styles.button}>
        <Text style={styles.buttonText}>Upload Secure File</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0F19',
    padding: 20,
  },
  header: {
    marginTop: 40,
    marginBottom: 30,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 12,
    color: '#3B82F6',
    letterSpacing: 2,
    fontWeight: 'bold',
  },
  card: {
    backgroundColor: '#1A233A',
    padding: 24,
    borderRadius: 16,
    borderWidth: 1,
    marginBottom: 20,
  },
  cardTitle: {
    color: '#9CA3AF',
    fontSize: 14,
    textTransform: 'uppercase',
  },
  riskText: {
    fontSize: 48,
    fontWeight: '900',
    marginVertical: 10,
  },
  cardDesc: {
    color: '#D1D5DB',
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 30,
  },
  statBox: {
    flex: 1,
    backgroundColor: '#1A233A',
    padding: 20,
    borderRadius: 16,
    marginHorizontal: 5,
    alignItems: 'center',
  },
  statVal: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  statLabel: {
    color: '#9CA3AF',
    marginTop: 5,
  },
  button: {
    backgroundColor: '#3B82F6',
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
