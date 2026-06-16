import AsyncStorage from '@react-native-async-storage/async-storage';

const PLZ_KEY = 'plz';

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
