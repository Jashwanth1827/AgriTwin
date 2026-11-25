import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";

import { AuthShell } from "../components/layout/AuthShell";
import { Alert } from "../components/ui/misc";
import { Button } from "../components/ui/button";
import { Field, Input, Select } from "../components/ui/input";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { SystemOptions } from "../types";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    phone: "",
    state: "",
    district: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const options = useQuery({
    queryKey: ["system-options"],
    queryFn: () => api.get<SystemOptions>("/system/options"),
  });

  function update(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        phone: form.phone || undefined,
        state: form.state || undefined,
        district: form.district || undefined,
      });
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Your farms, buyers and decisions stay isolated to your account."
      footer={
        <>
          Already registered?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form className="space-y-4" onSubmit={submit}>
        {error ? <Alert variant="error">{error}</Alert> : null}
        <Field label="Full name">
          <Input
            required
            minLength={2}
            value={form.full_name}
            onChange={(event) => update("full_name", event.target.value)}
            placeholder="Ravi Patil"
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Email">
            <Input
              type="email"
              required
              autoComplete="email"
              value={form.email}
              onChange={(event) => update("email", event.target.value)}
              placeholder="you@example.com"
            />
          </Field>
          <Field label="Phone (optional)">
            <Input
              value={form.phone}
              onChange={(event) => update("phone", event.target.value)}
              placeholder="+91 90000 00000"
            />
          </Field>
        </div>
        <Field label="Password" hint="At least 8 characters with a letter and a digit.">
          <Input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={(event) => update("password", event.target.value)}
            placeholder="••••••••"
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="State (optional)">
            <Select value={form.state} onChange={(event) => update("state", event.target.value)}>
              <option value="">Select state</option>
              {(options.data?.states ?? []).map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="District (optional)">
            <Input
              value={form.district}
              onChange={(event) => update("district", event.target.value)}
              placeholder="Nashik"
            />
          </Field>
        </div>
        <Button type="submit" className="w-full" size="lg" loading={loading}>
          <UserPlus className="h-4 w-4" />
          Create account
        </Button>
      </form>
    </AuthShell>
  );
}
