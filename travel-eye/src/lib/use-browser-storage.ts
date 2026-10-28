"use client";

import { useCallback, useSyncExternalStore } from "react";

function readEmpty() {
  return "";
}

export function useBrowserStorage(key: string, eventName: string): string {
  const subscribe = useCallback(
    (onChange: () => void) => {
      window.addEventListener("storage", onChange);
      window.addEventListener(eventName, onChange);
      return () => {
        window.removeEventListener("storage", onChange);
        window.removeEventListener(eventName, onChange);
      };
    },
    [eventName],
  );

  const getSnapshot = useCallback(() => localStorage.getItem(key) ?? "", [key]);

  return useSyncExternalStore(subscribe, getSnapshot, readEmpty);
}
