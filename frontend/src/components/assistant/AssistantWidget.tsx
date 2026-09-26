import { Mic, MicOff, RotateCcw, SendHorizontal, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useI18n } from "../../i18n/I18nProvider";
import { formatINR } from "../../lib/format";
import { useAssistantChat } from "../../lib/queries";
import type { ChatMessage, Product } from "../../lib/types";
import { cn } from "../../lib/utils";
import { ProductImage } from "../ProductImage";
import { TrustChip } from "../TrustScore";
import { RichText } from "./RichText";
import { useSpeechInput } from "./useSpeechInput";

interface Turn extends ChatMessage {
  products?: Product[];
  error?: boolean;
}

const STORAGE_KEY = "shopsense.chat";
const HISTORY_TURNS = 10; // earlier messages sent for context

function loadTurns(): Turn[] {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "[]") as Turn[];
  } catch {
    return [];
  }
}

function MiniProduct({ product, onOpen }: { product: Product; onOpen: () => void }) {
  return (
    <Link
      to={`/products/${product.id}`}
      onClick={onOpen}
      className="flex items-center gap-3 rounded-xl border border-line bg-surface p-2 transition hover:border-brand/50"
    >
      <ProductImage src={product.image_url} title={product.title} category={product.category} className="h-14 w-14 shrink-0 rounded-lg" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{product.title}</p>
        <p className="truncate text-xs text-muted">{product.seller.business_name}</p>
        <div className="mt-0.5 flex items-center gap-2">
          <span className="text-sm font-bold tabular">{formatINR(product.price.final_price)}</span>
          <TrustChip score={product.seller.trust_score} label={String(Math.round(product.seller.trust_score))} />
        </div>
      </div>
    </Link>
  );
}

export function AssistantWidget() {
  const { t, lang } = useI18n();
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>(loadTurns);
  const [input, setInput] = useState("");
  const chat = useAssistantChat();
  const scroller = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(turns.slice(-30)));
    } catch {
      /* ignore */
    }
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns, chat.isPending]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const send = useCallback(
    (text: string) => {
      const message = text.trim();
      if (!message || chat.isPending) return;
      const history = turns
        .filter((turn) => !turn.error)
        .slice(-HISTORY_TURNS)
        .map(({ role, content }) => ({ role, content }));
      setTurns((prev) => [...prev, { role: "user", content: message }]);
      setInput("");
      chat.mutate(
        { message, history, language: lang },
        {
          onSuccess: (res) => setTurns((prev) => [...prev, { role: "assistant", content: res.reply, products: res.products }]),
          onError: (error) =>
            setTurns((prev) => [...prev, { role: "assistant", content: `${t("assistant_error")} ${error.message}`, error: true }]),
        },
      );
    },
    [chat, lang, t, turns],
  );

  const speech = useSpeechInput(lang, send);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-brand px-5 py-3.5 font-semibold text-on-brand shadow-xl shadow-brand/25 transition hover:scale-[1.03] hover:bg-brand-strong"
      >
        <Sparkles className="h-5 w-5" aria-hidden />
        {t("assistant_open")}
      </button>
    );
  }

  return (
    <section
      role="dialog"
      aria-label={t("assistant_title")}
      className="fixed inset-0 z-50 flex flex-col bg-surface sm:inset-auto sm:bottom-5 sm:right-5 sm:h-[min(640px,calc(100dvh-2.5rem))] sm:w-[400px] sm:rounded-2xl sm:border sm:border-line sm:shadow-2xl sm:shadow-black/20"
    >
      <header className="flex items-center gap-3 border-b border-line px-4 py-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-on-brand">
          <Sparkles className="h-5 w-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold leading-tight">{t("assistant_title")}</h2>
          <p className="truncate text-xs text-muted">{t("assistant_subtitle")}</p>
        </div>
        {turns.length > 0 && (
          <button onClick={() => setTurns([])} className="rounded-lg p-2 text-muted hover:bg-surface-2 hover:text-fg" aria-label={t("assistant_new_chat")} title={t("assistant_new_chat")}>
            <RotateCcw className="h-4 w-4" />
          </button>
        )}
        <button onClick={() => setOpen(false)} className="rounded-lg p-2 text-muted hover:bg-surface-2 hover:text-fg" aria-label={t("close")}>
          <X className="h-5 w-5" />
        </button>
      </header>

      <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
        <div className="max-w-[88%] rounded-2xl rounded-tl-sm bg-surface-2 px-3.5 py-2.5 text-sm">{t("assistant_greeting")}</div>

        {turns.length === 0 && (
          <div className="flex flex-col items-start gap-2">
            {(["sugg_1", "sugg_2", "sugg_3"] as const).map((key) => (
              <button key={key} onClick={() => send(t(key))} className="rounded-full border border-brand/40 bg-brand-soft px-3.5 py-1.5 text-left text-sm text-brand hover:border-brand">
                {t(key)}
              </button>
            ))}
          </div>
        )}

        {turns.map((turn, i) =>
          turn.role === "user" ? (
            <div key={i} className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-brand px-3.5 py-2.5 text-sm text-on-brand">
              {turn.content}
            </div>
          ) : (
            <div key={i} className="max-w-[92%] space-y-2">
              <div className={cn("rounded-2xl rounded-tl-sm px-3.5 py-2.5 text-sm", turn.error ? "bg-danger-soft text-danger" : "bg-surface-2")}>
                <RichText text={turn.content} />
              </div>
              {turn.products?.map((p) => (
                <MiniProduct key={p.id} product={p} onOpen={() => window.innerWidth < 640 && setOpen(false)} />
              ))}
            </div>
          ),
        )}

        {chat.isPending && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <span className="flex gap-1" aria-hidden>
              {[0, 150, 300].map((delay) => (
                <span key={delay} className="h-2 w-2 animate-bounce rounded-full bg-brand" style={{ animationDelay: `${delay}ms` }} />
              ))}
            </span>
            {t("assistant_thinking")}
          </div>
        )}
      </div>

      <form onSubmit={submit} className="border-t border-line p-3">
        <div className="flex items-end gap-2">
          {speech.supported && (
            <button
              type="button"
              onClick={speech.toggle}
              className={cn(
                "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border transition",
                speech.listening ? "animate-pulse border-danger bg-danger-soft text-danger" : "border-line text-muted hover:text-fg",
              )}
              aria-label={speech.listening ? t("assistant_listening") : t("assistant_speak")}
              title={speech.listening ? t("assistant_listening") : t("assistant_speak")}
            >
              {speech.listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            </button>
          )}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={1}
            maxLength={1000}
            placeholder={speech.listening ? t("assistant_listening") : t("assistant_placeholder")}
            aria-label={t("assistant_placeholder")}
            className="max-h-32 min-h-11 flex-1 resize-none rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-sm leading-6 focus:border-brand focus:bg-surface focus:outline-none focus:ring-4 focus:ring-ring"
          />
          <button
            type="submit"
            disabled={!input.trim() || chat.isPending}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand text-on-brand transition hover:bg-brand-strong disabled:opacity-40"
            aria-label={t("assistant_send")}
          >
            <SendHorizontal className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-muted">{t("assistant_disclaimer")}</p>
      </form>
    </section>
  );
}
