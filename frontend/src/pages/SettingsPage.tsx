import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  CheckCheck,
  Database,
  FileJson,
  Globe2,
  Save,
  Scale,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useOptions } from "../hooks/useReference";
import { formatDateTime, titleCase } from "../lib/utils";
import type { DecisionPolicy, NotificationItem, SystemStatus, User } from "../types";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Field, Input, Select } from "../components/ui/input";
import { Alert, KeyValue, LoadingBlock, PageHeader, Tabs } from "../components/ui/misc";

const TABS = [
  { value: "profile", label: "Profile" },
  { value: "notifications", label: "Notifications" },
  { value: "system", label: "System" },
  { value: "policy", label: "Decision policy" },
];

function ProfileTab() {
  const { user, setUser } = useAuth();
  const options = useOptions();
  const [form, setForm] = useState({
    full_name: user?.full_name ?? "",
    phone: user?.phone ?? "",
    state: user?.state ?? "",
    district: user?.district ?? "",
    preferred_language: user?.preferred_language ?? "en",
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setForm({
        full_name: user.full_name,
        phone: user.phone ?? "",
        state: user.state ?? "",
        district: user.district ?? "",
        preferred_language: user.preferred_language,
      });
    }
  }, [user]);

  const save = useMutation({
    mutationFn: () =>
      api.patch<User>("/auth/me", {
        full_name: form.full_name.trim(),
        phone: form.phone.trim() || null,
        state: form.state || null,
        district: form.district.trim() || null,
        preferred_language: form.preferred_language,
      }),
    onSuccess: (updated) => {
      setUser(updated);
      setMessage("Profile updated.");
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserRound className="h-4 w-4 text-primary" /> Account details
          </CardTitle>
          <CardDescription>Your farms, buyers and decisions stay isolated to this account.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {message ? <Alert variant="success">{message}</Alert> : null}
          {error ? <Alert variant="error">{error}</Alert> : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name" className="sm:col-span-2">
              <Input
                value={form.full_name}
                onChange={(event) => setForm({ ...form, full_name: event.target.value })}
              />
            </Field>
            <Field label="Email">
              <Input value={user?.email ?? ""} disabled />
            </Field>
            <Field label="Phone">
              <Input
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
              />
            </Field>
            <Field label="State">
              <Select
                value={form.state}
                onChange={(event) => setForm({ ...form, state: event.target.value })}
              >
                <option value="">Not set</option>
                {(options.data?.states ?? []).map((state) => (
                  <option key={state} value={state}>
                    {state}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="District">
              <Input
                value={form.district}
                onChange={(event) => setForm({ ...form, district: event.target.value })}
              />
            </Field>
            <Field label="Preferred language">
              <Select
                value={form.preferred_language}
                onChange={(event) => setForm({ ...form, preferred_language: event.target.value })}
              >
                <option value="en">English</option>
                <option value="hi">हिन्दी</option>
                <option value="mr">मराठी</option>
                <option value="ta">தமிழ்</option>
                <option value="te">తెలుగు</option>
                <option value="kn">ಕನ್ನಡ</option>
              </Select>
            </Field>
          </div>
          <Button onClick={() => save.mutate()} loading={save.isPending}>
            <Save className="h-4 w-4" /> Save profile
          </Button>
        </CardContent>
      </Card>

      <Card className="h-fit">
        <CardHeader>
          <CardTitle>Account snapshot</CardTitle>
        </CardHeader>
        <CardContent>
          <KeyValue label="User ID" value={`#${user?.id}`} />
          <KeyValue label="Email" value={user?.email ?? "—"} />
          <KeyValue label="Member since" value={formatDateTime(user?.created_at)} />
          <KeyValue
            label="Demo account"
            value={
              user?.is_demo ? <Badge variant="demo">YES</Badge> : <Badge variant="success">NO</Badge>
            }
          />
          <KeyValue label="Language" value={titleCase(user?.preferred_language ?? "en")} />
        </CardContent>
      </Card>
    </div>
  );
}

function NotificationsTab() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<NotificationItem[]>("/system/notifications"),
  });

  const markRead = useMutation({
    mutationFn: (id: number) => api.post<NotificationItem>(`/system/notifications/${id}/read`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    onError: (err: Error) => setError(err.message),
  });

  const markAll = useMutation({
    mutationFn: () => api.post("/system/notifications/read-all"),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    onError: (err: Error) => setError(err.message),
  });

  const unread = notifications.data?.filter((row) => !row.is_read).length ?? 0;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" /> Notifications
          </CardTitle>
          <CardDescription>{unread} unread</CardDescription>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => markAll.mutate()}
          loading={markAll.isPending}
          disabled={unread === 0}
        >
          <CheckCheck className="h-4 w-4" /> Mark all read
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        {error ? <Alert variant="error">{error}</Alert> : null}
        {notifications.isLoading ? (
          <LoadingBlock />
        ) : notifications.data && notifications.data.length > 0 ? (
          notifications.data.map((row) => (
            <div
              key={row.id}
              className={`rounded-lg border p-3 ${row.is_read ? "bg-card" : "bg-primary/5"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{row.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{row.message}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDateTime(row.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  <Badge variant="secondary">{row.category}</Badge>
                  {!row.is_read ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => markRead.mutate(row.id)}
                      loading={markRead.isPending}
                    >
                      Mark read
                    </Button>
                  ) : null}
                </div>
              </div>
            </div>
          ))
        ) : (
          <p className="py-8 text-center text-sm text-muted-foreground">No notifications.</p>
        )}
      </CardContent>
    </Card>
  );
}

function SystemTab() {
  const status = useQuery({
    queryKey: ["system-status"],
    queryFn: () => api.get<SystemStatus>("/system/status"),
  });

  if (status.isLoading) return <LoadingBlock label="Checking system status…" />;
  if (status.isError) return <Alert variant="error">{(status.error as Error).message}</Alert>;
  const data = status.data!;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
              <Activity className="h-3 w-3" /> Version
            </p>
            <p className="mt-1 text-lg font-semibold">{data.version}</p>
            <p className="text-xs text-muted-foreground">{data.environment}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
              <Database className="h-3 w-3" /> Database
            </p>
            <p className="mt-1 text-lg font-semibold">{data.database_backend}</p>
            <p className="text-xs text-muted-foreground">{data.data_mode} data mode</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
              <ShieldCheck className="h-3 w-3" /> Demo mode
            </p>
            <p className="mt-1 text-lg font-semibold">{data.demo_mode ? "Enabled" : "Disabled"}</p>
            <p className="text-xs text-muted-foreground">Demo records are always labelled</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
              <Globe2 className="h-3 w-3" /> Server time
            </p>
            <p className="mt-1 text-sm font-semibold">{formatDateTime(data.server_time)}</p>
            <p className="text-xs text-muted-foreground">UTC</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Models</CardTitle>
          <CardDescription>Live artifact availability, never simulated</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.models.map((model) => (
            <div
              key={model.name}
              className="flex flex-wrap items-start justify-between gap-3 rounded-lg border p-3"
            >
              <div>
                <p className="text-sm font-medium">{titleCase(model.name)}</p>
                <p className="text-xs text-muted-foreground">{model.message ?? "—"}</p>
              </div>
              <div className="flex items-center gap-2">
                {model.version ? <Badge variant="outline">{model.version}</Badge> : null}
                <Badge
                  variant={
                    model.mode === "real"
                      ? "success"
                      : model.mode === "demo"
                        ? "demo"
                        : model.available
                          ? "info"
                          : "danger"
                  }
                >
                  {model.mode}
                </Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>External providers</CardTitle>
            <CardDescription>Keyless public services</CardDescription>
          </CardHeader>
          <CardContent>
            {Object.entries(data.providers).map(([key, value]) => (
              <KeyValue
                key={key}
                label={titleCase(key)}
                value={
                  <span className="flex items-center gap-2">
                    {value.name}
                    <Badge variant={value.configured ? "success" : "secondary"}>
                      {value.configured ? "configured" : "disabled"}
                    </Badge>
                  </span>
                }
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notices</CardTitle>
            <CardDescription>Data limitations surfaced by the backend</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.notices.map((notice) => (
              <Alert key={notice} variant="info">
                {notice}
              </Alert>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function PolicyTab() {
  const policy = useQuery({
    queryKey: ["decision-policy"],
    queryFn: () => api.get<DecisionPolicy>("/decisions/policy"),
  });

  if (policy.isLoading) return <LoadingBlock label="Loading decision policy…" />;
  if (policy.isError) return <Alert variant="error">{(policy.error as Error).message}</Alert>;
  const data = policy.data!;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-primary" /> Policy {data.version}
          </CardTitle>
          <CardDescription>{data.notes}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <div>
            <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground">
              <FileJson className="h-3 w-3" /> Finance
            </p>
            {Object.entries(data.finance).map(([key, value]) => (
              <KeyValue key={key} label={titleCase(key)} value={String(value)} />
            ))}
          </div>
          <div>
            <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground">
              <FileJson className="h-3 w-3" /> Freshness
            </p>
            {Object.entries(data.freshness).map(([key, value]) => (
              <KeyValue
                key={key}
                label={titleCase(key)}
                value={typeof value === "object" ? JSON.stringify(value) : String(value)}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Risk weights</CardTitle>
            <CardDescription>Weights must sum to 1.0</CardDescription>
          </CardHeader>
          <CardContent>
            {Object.entries(data.risk).map(([key, value]) => (
              <KeyValue
                key={key}
                label={titleCase(key)}
                value={typeof value === "object" ? JSON.stringify(value) : String(value)}
              />
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Decision rules</CardTitle>
            <CardDescription>INSPECT → WAIT → SELL</CardDescription>
          </CardHeader>
          <CardContent>
            {Object.entries(data.policy).map(([key, value]) => (
              <KeyValue
                key={key}
                label={titleCase(key)}
                value={typeof value === "object" ? JSON.stringify(value) : String(value)}
              />
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [params, setParams] = useSearchParams();
  const requested = params.get("tab");
  const initial = TABS.some((tab) => tab.value === requested) ? requested! : "profile";
  const [tab, setTab] = useState(initial);

  // The notification bell navigates here with ?tab=notifications while this page is
  // already mounted, so keep the visible tab in sync with the URL.
  useEffect(() => {
    if (TABS.some((item) => item.value === requested)) {
      setTab(requested!);
    } else if (requested === null) {
      setTab("profile");
    }
  }, [requested]);

  function change(value: string) {
    setTab(value);
    setParams(value === "profile" ? {} : { tab: value }, { replace: true });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Manage your profile, notifications, system status and the decision policy."
        actions={<Tabs tabs={TABS} value={tab} onChange={change} />}
      />
      {tab === "profile" ? <ProfileTab /> : null}
      {tab === "notifications" ? <NotificationsTab /> : null}
      {tab === "system" ? <SystemTab /> : null}
      {tab === "policy" ? <PolicyTab /> : null}
    </div>
  );
}
