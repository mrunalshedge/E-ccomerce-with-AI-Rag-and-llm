import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

const fieldBase =
  "w-full rounded-xl border border-line bg-surface px-3.5 text-fg placeholder:text-muted/70 transition-colors focus:border-brand focus:outline-none focus:ring-4 focus:ring-ring";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(fieldBase, "h-11", className)} {...props} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(fieldBase, "min-h-24 py-2.5", className)} {...props} />;
}

/** Label + control + optional hint/error, wired up for screen readers. */
export function Field({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-fg">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-danger" role="alert">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="text-xs text-muted">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-line bg-surface", className)} {...props} />;
}

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      neutral: "bg-surface-2 text-muted",
      brand: "bg-brand-soft text-brand",
      warn: "bg-warn-soft text-warn",
      danger: "bg-danger-soft text-danger",
      info: "bg-info-soft text-info",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export function Badge({
  className,
  tone,
  ...props
}: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-surface-2", className)} aria-hidden />;
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon: ReactNode;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-line bg-surface px-6 py-14 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-soft text-brand">{icon}</div>
      <h2 className="text-lg font-semibold">{title}</h2>
      {body && <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry, retryLabel }: { message: string; onRetry?: () => void; retryLabel: string }) {
  return (
    <div role="alert" className="rounded-2xl border border-danger/30 bg-danger-soft px-5 py-4 text-sm text-danger">
      <p>{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 font-semibold underline underline-offset-2">
          {retryLabel}
        </button>
      )}
    </div>
  );
}
