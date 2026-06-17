import AsyncStorage from '@react-native-async-storage/async-storage';

const PLZ_KEY = 'plz';
const NONFOOD_KEY = 'showNonFood';

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
