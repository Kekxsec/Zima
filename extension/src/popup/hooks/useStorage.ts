import { useEffect, useState } from "react";

export function useLocalStorage<T>(key: string, fallback: T): [T, boolean] {
  const [value, setValue] = useState<T>(fallback);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    chrome.storage.local.get(key, (result) => {
      if (key in result) setValue(result[key] as T);
      setLoaded(true);
    });

    const listener = (changes: Record<string, chrome.storage.StorageChange>) => {
      if (key in changes) setValue(changes[key]!.newValue as T);
    };
    chrome.storage.local.onChanged.addListener(listener);
    return () => chrome.storage.local.onChanged.removeListener(listener);
  }, [key]);

  return [value, loaded];
}

export function useSessionStorage<T>(key: string, fallback: T): [T, boolean] {
  const [value, setValue] = useState<T>(fallback);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    chrome.storage.session.get(key, (result) => {
      if (key in result) setValue(result[key] as T);
      setLoaded(true);
    });

    const listener = (changes: Record<string, chrome.storage.StorageChange>) => {
      if (key in changes) setValue(changes[key]!.newValue as T);
    };
    chrome.storage.session.onChanged.addListener(listener);
    return () => chrome.storage.session.onChanged.removeListener(listener);
  }, [key]);

  return [value, loaded];
}
