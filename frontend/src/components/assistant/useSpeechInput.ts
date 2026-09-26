import { useCallback, useEffect, useRef, useState } from "react";

import type { Language } from "../../lib/types";

// Minimal typings for the Web Speech API (Chrome/Edge/Safari; not in TS's DOM lib yet).
interface SpeechRecognitionResultEvent {
  results: { [index: number]: { [index: number]: { transcript: string } }; length: number };
}
interface SpeechRecognitionInstance {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

const SPEECH_LOCALES: Record<Language, string> = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

function recognitionClass(): SpeechRecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Voice input in the UI language (Indian English, Hindi or Marathi). Free: runs in the browser. */
export function useSpeechInput(lang: Language, onText: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const recognition = useRef<SpeechRecognitionInstance | null>(null);
  const supported = recognitionClass() !== null;

  useEffect(() => () => recognition.current?.stop(), []);

  const toggle = useCallback(() => {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const Ctor = recognitionClass();
    if (!Ctor) return;
    const r = new Ctor();
    r.lang = SPEECH_LOCALES[lang];
    r.interimResults = false;
    r.maxAlternatives = 1;
    r.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript?.trim();
      if (text) onText(text);
    };
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    recognition.current = r;
    setListening(true);
    r.start();
  }, [lang, listening, onText]);

  return { supported, listening, toggle };
}
