import { cva, type VariantProps } from "class-variance-authority";
import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50 select-none",
  {
    variants: {
      variant: {
        primary: "bg-brand text-on-brand hover:bg-brand-strong shadow-sm",
        secondary: "bg-brand-soft text-brand hover:bg-brand-soft/70",
        outline: "border border-line bg-surface text-fg hover:bg-surface-2",
        ghost: "text-fg hover:bg-surface-2",
        danger: "border border-danger/40 bg-surface text-danger hover:bg-danger-soft",
      },
      size: {
        sm: "h-9 px-3 text-sm",
        md: "h-11 px-4 text-sm",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export function Button({ className, variant, size, loading, disabled, children, ...props }: ButtonProps) {
  return (
    <button className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} {...props}>
      {loading && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}
