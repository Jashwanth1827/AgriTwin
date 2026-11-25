import type { ReactNode } from "react";
import { Sprout, ShieldCheck, TrendingUp, Wheat } from "lucide-react";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-primary p-10 text-primary-foreground lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, white 0, transparent 35%), radial-gradient(circle at 80% 70%, white 0, transparent 30%)",
          }}
        />
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15">
              <Sprout className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xl font-semibold">AgriTwin</p>
              <p className="text-sm text-primary-foreground/80">
                Crop-to-cash decision support for Indian farmers
              </p>
            </div>
          </div>

          <div className="mt-16 max-w-md space-y-6">
            <h2 className="text-3xl font-semibold leading-tight">
              One twin of your farm. Every signal that matters.
            </h2>
            <p className="text-primary-foreground/85">
              Combine crop-health screening, yield estimates, mandi intelligence, buyer
              offers and transport costs into a single explainable sell / wait / inspect
              decision.
            </p>
            <ul className="space-y-3 text-sm text-primary-foreground/90">
              <li className="flex items-start gap-3">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                Uncertainty-aware: every estimate carries a confidence interval.
              </li>
              <li className="flex items-start gap-3">
                <TrendingUp className="mt-0.5 h-4 w-4 shrink-0" />
                Real public market data, with data-freshness penalties made visible.
              </li>
              <li className="flex items-start gap-3">
                <Wheat className="mt-0.5 h-4 w-4 shrink-0" />
                Deterministic, documented rules — never a black-box chatbot.
              </li>
            </ul>
          </div>
        </div>

        <p className="relative text-xs text-primary-foreground/70">
          Decision support only. Confirm agronomic and commercial choices with local
          extension officers and buyers.
        </p>
      </div>

      <div className="flex items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sprout className="h-5 w-5" />
            </div>
            <div>
              <p className="font-semibold">AgriTwin</p>
              <p className="text-xs text-muted-foreground">Crop-to-cash decisions</p>
            </div>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          <div className="mt-6">{children}</div>
          <div className="mt-6 text-sm text-muted-foreground">{footer}</div>
        </div>
      </div>
    </div>
  );
}
