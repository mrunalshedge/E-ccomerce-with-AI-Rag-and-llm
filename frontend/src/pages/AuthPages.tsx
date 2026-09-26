import { ShieldCheck, ShoppingBag, Store } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/ui/button";
import { Card, Field, Input } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import { cn } from "../lib/utils";

function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="mx-auto max-w-md py-4 sm:py-10">
      <div className="mb-6 text-center">
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand text-on-brand">
          <ShieldCheck className="h-7 w-7" aria-hidden />
        </span>
        <h1 className="text-2xl font-bold">{title}</h1>
        <p className="mt-1 text-muted">{subtitle}</p>
      </div>
      <Card className="p-6">{children}</Card>
      <p className="mt-5 text-center text-sm text-muted">{footer}</p>
    </div>
  );
}

/** Where to go after logging in: back to the page that asked, else home. */
function useReturnTo(): string {
  const location = useLocation();
  return (location.state as { from?: string } | null)?.from ?? "/";
}

export function LoginPage() {
  const { t } = useI18n();
  const { login } = useAuth();
  const navigate = useNavigate();
  const returnTo = useReturnTo();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const user = await login(email.trim(), password);
      toast.success(t("welcome", { name: user.name.split(" ")[0] }));
      navigate(returnTo, { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPending(false);
    }
  };

  return (
    <AuthShell
      title={t("login_title")}
      subtitle={t("login_subtitle")}
      footer={<>{t("no_account")} <Link to="/register" state={{ from: returnTo }} className="font-semibold text-brand hover:underline">{t("register")}</Link></>}
    >
      <form onSubmit={submit} className="space-y-4">
        <Field id="email" label={t("email")}>
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field id="password" label={t("password")}>
          <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error && <p className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger" role="alert">{error}</p>}
        <Button type="submit" size="lg" className="w-full" loading={pending}>
          {pending ? t("logging_in") : t("login")}
        </Button>
        <p className="rounded-xl bg-surface-2 px-3 py-2 text-center text-xs text-muted">{t("demo_hint")}</p>
      </form>
    </AuthShell>
  );
}

export function RegisterPage() {
  const { t } = useI18n();
  const { register } = useAuth();
  const navigate = useNavigate();
  const returnTo = useReturnTo();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [role, setRole] = useState<"customer" | "seller">("customer");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const user = await register({ ...form, email: form.email.trim(), role });
      toast.success(t("welcome", { name: user.name.split(" ")[0] }));
      navigate(role === "customer" ? returnTo : "/", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPending(false);
    }
  };

  const roleOption = (value: "customer" | "seller", icon: ReactNode, label: string) => (
    <label className={cn("flex cursor-pointer items-center justify-center gap-2 rounded-xl border-2 px-3 py-3 text-sm font-medium transition", role === value ? "border-brand bg-brand-soft text-brand" : "border-line hover:border-brand/40")}>
      <input type="radio" name="role" className="sr-only" checked={role === value} onChange={() => setRole(value)} />
      {icon}
      {label}
    </label>
  );

  return (
    <AuthShell
      title={t("register_title")}
      subtitle={t("register_subtitle")}
      footer={<>{t("have_account")} <Link to="/login" state={{ from: returnTo }} className="font-semibold text-brand hover:underline">{t("login")}</Link></>}
    >
      <form onSubmit={submit} className="space-y-4">
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium">{t("account_type")}</legend>
          <div className="grid grid-cols-2 gap-2">
            {roleOption("customer", <ShoppingBag className="h-4 w-4" />, t("role_customer"))}
            {roleOption("seller", <Store className="h-4 w-4" />, t("role_seller"))}
          </div>
        </fieldset>
        <Field id="name" label={t("name")}>
          <Input id="name" autoComplete="name" required maxLength={120} value={form.name} onChange={set("name")} />
        </Field>
        <Field id="email" label={t("email")}>
          <Input id="email" type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
        </Field>
        <Field id="password" label={t("password")} hint={t("password_hint")}>
          <Input id="password" type="password" autoComplete="new-password" required minLength={8} value={form.password} onChange={set("password")} />
        </Field>
        {error && <p className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger" role="alert">{error}</p>}
        <Button type="submit" size="lg" className="w-full" loading={pending}>
          {pending ? t("creating_account") : t("register")}
        </Button>
        <p className="text-center text-xs text-muted">{t("consent_note")}</p>
      </form>
    </AuthShell>
  );
}
