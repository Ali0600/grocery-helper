import AsyncStorage from '@react-native-async-storage/async-storage';

import { MyStore } from './types';

const PLZ_KEY = 'plz';
const NONFOOD_KEY = 'showNonFood';
const MYSTORES_KEY = 'myStores';

export async function getStoredPlz(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(PLZ_KEY);
  } catch {
    return null;
  }
}

export async function setStoredPlz(plz: string): Promise<void> {
  try {
    await AsyncStorage.setItem(PLZ_KEY, plz);
  } catch {
    // Persistence is best-effort; the PLZ still applies for this session.
  }
}

export async function getStoredShowNonFood(): Promise<boolean> {
  try {
    return (await AsyncStorage.getItem(NONFOOD_KEY)) === '1';
  } catch {
    return false;
  }
}

export async function setStoredShowNonFood(value: boolean): Promise<void> {
  try {
    await AsyncStorage.setItem(NONFOOD_KEY, value ? '1' : '0');
  } catch {
    // best-effort
  }
}

export async function getStoredMyStores(): Promise<MyStore[]> {
  try {
    const raw = await AsyncStorage.getItem(MYSTORES_KEY);
    return raw ? (JSON.parse(raw) as MyStore[]) : [];
  } catch {
    return [];
  }
}

export async function setStoredMyStores(stores: MyStore[]): Promise<void> {
  try {
    await AsyncStorage.setItem(MYSTORES_KEY, JSON.stringify(stores));
  } catch {
    // best-effort
  }
}
