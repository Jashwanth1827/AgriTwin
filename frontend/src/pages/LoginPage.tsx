import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";

import { AuthShell } from "../components/layout/AuthShell";
import { Alert } from "../components/ui/misc";
import { Button } from "../components/ui/button";
import { Field, Input } from "../components/ui/input";
import { useAuth } from "../lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("demo@agritwin.in");
  const [password, setPassword] = useState("Demo@12345");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(nextEmail: string, nextPassword: string) {
    setLoading(true);
    setError(null);
    try {
      await login(nextEmail, nextPassword);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Sign in"
      subtitle="Use your account, or start with the labelled demo workspace."
      footer={
        <>
          New to AgriTwin?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit(email, password);
        }}
      >
        {error ? <Alert variant="error">{error}</Alert> : null}
        <Field label="Email">
          <Input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
        </Field>
        <Field label="Password">
          <Input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
          />
        </Field>
        <Button type="submit" className="w-full" size="lg" loading={loading}>
          <LogIn className="h-4 w-4" />
          Sign in
        </Button>
      </form>

      <div className="mt-4 rounded-lg border border-dashed bg-secondary/40 p-3 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">Demo workspace</p>
        <p className="mt-1">
          Demo farms and buyer offers are clearly labelled. Market prices and historical
          yields come from real public datasets.
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-3 w-full"
          loading={loading}
          onClick={() => void submit("demo@agritwin.in", "Demo@12345")}
        >
          Sign in with the demo account
        </Button>
      </div>
    </AuthShell>
  );
}
