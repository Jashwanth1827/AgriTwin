import type { HTMLAttributes } from "react";

import { cn } from "../../lib/utils";

type Variant = "default" | "secondary" | "outline" | "success" | "warning" | "danger" | "info" | "demo";

const variants: Record<Variant, string> = {
  default: "border-transparent bg-primary/10 text-primary",
  secondary: "border-transparent bg-secondary text-secondary-foreground",
  outline: "text-foreground",
  success: "border-transparent bg-emerald-100 text-emerald-800",
  warning: "border-transparent bg-amber-100 text-amber-900",
  danger: "border-transparent bg-rose-100 text-rose-800",
  info: "border-transparent bg-sky-100 text-sky-800",
  demo: "border-amber-300 bg-amber-50 text-amber-900",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
