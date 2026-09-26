import { BookOpen, Cpu, House, Package, Shirt, ShoppingBasket, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { cn } from "../lib/utils";

const CATEGORY_STYLE: Record<string, { icon: LucideIcon; tint: string }> = {
  clothing: { icon: Shirt, tint: "from-rose-100 to-orange-50 text-rose-700 dark:from-rose-950 dark:to-orange-950 dark:text-rose-300" },
  home: { icon: House, tint: "from-sky-100 to-indigo-50 text-sky-700 dark:from-sky-950 dark:to-indigo-950 dark:text-sky-300" },
  grocery: { icon: ShoppingBasket, tint: "from-lime-100 to-emerald-50 text-emerald-700 dark:from-lime-950 dark:to-emerald-950 dark:text-emerald-300" },
  electronics: { icon: Cpu, tint: "from-violet-100 to-slate-50 text-violet-700 dark:from-violet-950 dark:to-slate-900 dark:text-violet-300" },
  books: { icon: BookOpen, tint: "from-amber-100 to-yellow-50 text-amber-700 dark:from-amber-950 dark:to-yellow-950 dark:text-amber-300" },
};
const FALLBACK = { icon: Package, tint: "from-stone-100 to-stone-50 text-stone-600 dark:from-stone-900 dark:to-stone-950 dark:text-stone-300" };

/** Product photo, or a tinted category illustration when the seller hasn't added one. */
export function ProductImage({
  src,
  title,
  category,
  className,
  large = false,
}: {
  src: string | null;
  title: string;
  category: string;
  className?: string;
  large?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const { icon: Icon, tint } = CATEGORY_STYLE[category] ?? FALLBACK;

  if (src && !failed) {
    return (
      <img
        src={src}
        alt={title}
        loading="lazy"
        onError={() => setFailed(true)}
        className={cn("aspect-square w-full rounded-xl object-cover", className)}
      />
    );
  }
  return (
    <div
      role="img"
      aria-label={title}
      className={cn("flex aspect-square w-full items-center justify-center rounded-xl bg-gradient-to-br", tint, className)}
    >
      <Icon className={large ? "h-24 w-24" : "h-12 w-12"} strokeWidth={1.4} aria-hidden />
    </div>
  );
}
