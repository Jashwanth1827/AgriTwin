import { Link } from "react-router-dom";
import { Compass, Home, Sprout } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Sprout className="h-7 w-7" />
        </div>
        <p className="mt-6 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          404
        </p>
        <h1 className="mt-1 text-2xl font-semibold">This field is not on the map</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you requested does not exist. Head back to the dashboard to continue working
          with your farms and decisions.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Link
            to="/dashboard"
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            <Home className="h-4 w-4" /> Dashboard
          </Link>
          <Link
            to="/farms"
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-input bg-card px-4 text-sm font-medium transition-colors hover:bg-secondary/60"
          >
            <Compass className="h-4 w-4" /> Farms
          </Link>
        </div>
      </div>
    </div>
  );
}
