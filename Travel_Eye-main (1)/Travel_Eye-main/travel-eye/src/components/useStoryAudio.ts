"use client";

import { useEffect, useState } from "react";
import { getNarrationLanguage } from "@/lib/preferences";

export function useStoryAudio(text: string) {
  const [speaking, setSpeaking] = useState(false);
  const [unsupported, setUnsupported] = useState(false);

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, [text]);

  function stop() {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  }

  function toggle() {
    if (speaking) {
      stop();
      return;
    }

    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setUnsupported(true);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = getNarrationLanguage().code;
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.resume();
    window.speechSynthesis.getVoices();
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
    setUnsupported(false);
  }

  return { speaking, unsupported, toggle, stop };
}
