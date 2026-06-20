import AsyncStorage from '@react-native-async-storage/async-storage';

import { BasketItem, MyStore } from './types';

const PLZ_KEY = 'plz';
const NONFOOD_KEY = 'showNonFood';
const MYSTORES_KEY = 'myStores';
const SORT_KEY = 'sortMode';
const BASKET_KEY = 'basket';

export type SortMode = 'discount' | 'unit';

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

export async function getStoredSortMode(): Promise<SortMode> {
  try {
    return (await AsyncStorage.getItem(SORT_KEY)) === 'unit' ? 'unit' : 'discount';
  } catch {
    return 'discount';
  }
}

export async function setStoredSortMode(mode: SortMode): Promise<void> {
  try {
    await AsyncStorage.setItem(SORT_KEY, mode);
  } catch {
    // best-effort
  }
}

export async function getStoredBasket(): Promise<BasketItem[]> {
  try {
    const raw = await AsyncStorage.getItem(BASKET_KEY);
    return raw ? (JSON.parse(raw) as BasketItem[]) : [];
  } catch {
    return [];
  }
}

export async function setStoredBasket(items: BasketItem[]): Promise<void> {
  try {
    await AsyncStorage.setItem(BASKET_KEY, JSON.stringify(items));
  } catch {
    // best-effort
  }
}
