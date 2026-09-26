import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes, letting later ones win (`cn("p-2", big && "p-4")`). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
