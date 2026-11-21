import {
  createClient,
  type SupabaseClient,
  type Session,
} from "@supabase/supabase-js";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import PublicLanding from "./PublicLanding";
import "./cloud.css";

type Lang = "zh-CN" | "zh-TW" | "en";
const base = import.meta.env.BASE_URL;
let client: SupabaseClient;
let appId = "";
let owner = "";
let revision = 0;
let setup: Promise<void> | undefined;
let queued = Promise.resolve();
let latestWrite = 0;
export let savedState: any = null;
export let authLanguage: Lang =
  (localStorage.getItem("coach.language") as Lang) || "zh-CN";
export const ownerKey = (name: string) => appId + "." + owner + "." + name;
export function publicHome() {
  location.assign(base);
}
export async function apiFetch(path: string, options: RequestInit = {}) {
  const expected = owner;
  const { data } = await client.auth.getSession();
  if (!expected || data.session?.user.id !== expected || owner !== expected)
    throw Error("Session changed");
  const headers = new Headers(options.headers);
  headers.set("Authorization", "Bearer " + data.session.access_token);
  return fetch(base + path.replace(/^\//, ""), {
    ...options,
    headers,
    cache: "no-store",
  });
}
export async function cloudJson(path: string, options?: RequestInit) {
  const r = await apiFetch(path, options);
  if (!r.ok) throw Error("HTTP " + r.status);
  return r.json();
}
export function saveState(state: unknown) {
  const serial = ++latestWrite,
    expected = owner,
    id = appId === "claude" ? "draft" : "workspace";
  queued = queued
    .catch(() => {})
    .then(async () => {
      if (owner !== expected) throw Error("Session changed");
      if (serial !== latestWrite) return;
      const r = await cloudJson("/api/workspaces/" + id, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state, revision, name: id }),
      });
      revision = r.revision;
      savedState = state;
    });
  queued.catch(() => window.dispatchEvent(new Event("save-error")));
  return queued;
}
export async function clearWorkspace() {
  await queued.catch(() => {});
  await cloudJson("/api/workspace-data", { method: "DELETE" });
  savedState = null;
  revision = 0;
}
export function entryFeature<T extends string>(fallback: T): T {
  const feature = location.pathname.slice((base + "workspace/").length);
  return (
    ["overview", "resume", "match", "interview", "settings"].includes(feature)
      ? feature
      : fallback
  ) as T;
}
export function changeFeature(feature: string) {
  history.pushState({}, "", base + "workspace/" + feature);
}
function target() {
  const next = new URLSearchParams(location.search).get("next");
  return next?.startsWith(base + "workspace") && !next.includes("\\")
    ? next
    : base + "workspace";
}
async function configure() {
  const r = await fetch(base + "auth-config", { cache: "no-store" }),
    cfg = await r.json();
  if (!cfg.url || !cfg.key) throw Error("Cloud configuration missing");
  appId = cfg.app;
  client = createClient(cfg.url, cfg.key, {
    auth: {
      storageKey: "coach.auth." + appId,
      detectSessionInUrl: location.pathname === base + "auth/callback",
    },
  });
}
const words = {
  "zh-CN": {
    login: "登录",
    signup: "注册",
    email: "邮箱",
    password: "密码",
    confirm: "确认密码",
    start: "开始使用",
    back: "返回首页",
    forgot: "忘记密码",
    send: "发送重置邮件",
    check: "请检查邮箱并点击验证链接，然后返回此页面。",
    error: "认证失败，请检查输入或稍后重试。",
    mismatch: "两次密码不一致。",
    wait: "正在验证登录状态…",
    account: "账号",
    logout: "退出登录",
    change: "修改密码",
    newPassword: "新密码",
    updated: "密码已更新",
    saveError: "保存失败，请保留本页并检查网络。",
    strength: "至少 10 个字符，包含大小写字母和数字。",
    rate: "请求过于频繁，请稍后重试。",
    invalid: "邮箱或密码不正确。",
    unconfirmed: "请先验证邮箱。",
    mailError: "验证邮件暂时无法发送，请稍后重试。",
    challenge: "请完成安全验证。",
  },
  "zh-TW": {
    login: "登入",
    signup: "註冊",
    email: "電郵",
    password: "密碼",
    confirm: "確認密碼",
    start: "開始使用",
    back: "返回首頁",
    forgot: "忘記密碼",
    send: "傳送重設郵件",
    check: "請檢查電郵並點擊驗證連結，然後返回此頁。",
    error: "驗證失敗，請檢查輸入或稍後重試。",
    mismatch: "兩次密碼不一致。",
    wait: "正在驗證登入狀態…",
    account: "帳戶",
    logout: "登出",
    change: "修改密碼",
    newPassword: "新密碼",
    updated: "密碼已更新",
    saveError: "儲存失敗，請保留此頁並檢查網絡。",
    strength: "至少 10 個字元，包含大小寫字母與數字。",
    rate: "請求過於頻繁，請稍後重試。",
    invalid: "電郵或密碼不正確。",
    unconfirmed: "請先驗證電郵。",
    mailError: "驗證郵件暫時無法傳送，請稍後重試。",
    challenge: "請完成安全驗證。",
  },
  en: {
    login: "Log in",
    signup: "Sign up",
    email: "Email",
    password: "Password",
    confirm: "Confirm password",
    start: "Get started",
    back: "Back to home",
    forgot: "Forgot password",
    send: "Send reset email",
    check:
      "Check your inbox and follow the verification link, then return here.",
    error: "Authentication failed. Check your details or try again later.",
    mismatch: "Passwords do not match.",
    wait: "Verifying your session…",
    account: "Account",
    logout: "Log out",
    change: "Change password",
    newPassword: "New password",
    updated: "Password updated",
    saveError: "Save failed. Keep this tab open and check the connection.",
    strength: "At least 10 characters with uppercase, lowercase and numbers.",
    rate: "Too many requests. Try again later.",
    invalid: "Incorrect email or password.",
    unconfirmed: "Verify your email first.",
    mailError: "Verification email could not be sent. Try again later.",
    challenge: "Complete the security check.",
  },
};
function strong(password: string) {
  return (
    password.length >= 10 &&
    /[a-z]/.test(password) &&
    /[A-Z]/.test(password) &&
    /[0-9]/.test(password)
  );
}
export function AuthGate({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(location.pathname),
    [lang, setLang] = useState<Lang>(authLanguage);
  const [ready, setReady] = useState(false),
    [signed, setSigned] = useState(false),
    [email, setEmail] = useState("");
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [menu, setMenu] = useState(false),
    [failed, setFailed] = useState(false);
  const navigation = useRef<(url: string) => void>(() => {});
  const t = words[lang] || words["zh-CN"];
  const view = path.slice(base.length).replace(/\/$/, "");
  const home = !view,
    privatePage = view.startsWith("workspace"),
    signup = view === "signup",
    forgot = view === "forgot-password",
    recover = view === "reset-password";
  function navigate(url: string) {
    history.pushState({}, "", url);
    setPath(location.pathname);
    setError("");
    setMessage("");
    setMenu(false);
  }
  navigation.current = navigate;
  function language(v: Lang) {
    authLanguage = v;
    localStorage.setItem("coach.language", v);
    document.documentElement.lang = v;
    setLang(v);
  }
  useEffect(() => {
    const pop = () => {
      setPath(location.pathname);
      setError("");
      setMessage("");
      setMenu(false);
    };
    const err = () => setFailed(true);
    window.addEventListener("popstate", pop);
    window.addEventListener("save-error", err);
    let live = true,
      sub: { unsubscribe(): void } | undefined,
      seq = 0;
    async function update(session: Session | null, event: string) {
      if (owner && session?.user.id === owner) return;
      const current = ++seq;
      if (!live) return;
      if (owner && session?.user.id !== owner) {
        owner = "";
        savedState = null;
        revision = 0;
        location.replace(base);
        return;
      }
      if (!session) {
        setSigned(false);
        setReady(true);
        return;
      }
      if (owner === session.user.id) return;
      try {
        const r = await fetch(base + "api/me", {
          headers: { Authorization: "Bearer " + session.access_token },
          cache: "no-store",
        });
        if (!r.ok) throw Error("unauthorized");
        const me = await r.json();
        if (!live || current !== seq) return;
        if (me.id !== session.user.id) throw Error("identity");
        owner = me.id;
        if (appId !== "codex_v2") {
          const snapshot = await apiFetch(
            "/api/workspaces/" + (appId === "claude" ? "draft" : "workspace"),
          );
          if (snapshot.ok) {
            const record = await snapshot.json();
            savedState = record.state;
            revision = record.revision;
          } else if (snapshot.status !== 404) throw Error("load");
        }
        if (!live || current !== seq) return;
        setEmail(session.user.email || "");
        setSigned(true);
        setError("");
        if (
          event === "PASSWORD_RECOVERY" ||
          new URLSearchParams(location.search).get("mode") === "recovery"
        )
          navigation.current(base + "reset-password");
        else if (
          location.pathname === base + "auth/callback" ||
          ["login", "signup"].includes(location.pathname.slice(base.length))
        )
          navigation.current(target());
      } catch {
        if (live) {
          owner = "";
          savedState = null;
          setSigned(false);
          setError("error");
        }
      } finally {
        if (live) setReady(true);
      }
    }
    (setup ||= configure())
      .then(() => {
        if (live)
          sub = client.auth.onAuthStateChange((event, session) => {
            setTimeout(() => void update(session, event), 0);
          }).data.subscription;
      })
      .catch(() => {
        if (live) {
          setError("error");
          setReady(true);
        }
      });
    const observer = new MutationObserver(() => {
      const value = document.documentElement.lang as Lang;
      if (words[value]) setLang(value);
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["lang"],
    });
    return () => {
      live = false;
      sub?.unsubscribe();
      observer.disconnect();
      window.removeEventListener("popstate", pop);
      window.removeEventListener("save-error", err);
    };
  }, []);
  useEffect(() => {
    if (ready && privatePage && !signed)
      navigate(
        base +
          "login?next=" +
          encodeURIComponent(location.pathname + location.search),
      );
  }, [ready, privatePage, signed]);
  async function submit(e: FormEvent<HTMLFormElement>, change = false) {
    e.preventDefault();
    setError("");
    setMessage("");
    const form = e.currentTarget,
      fields = new FormData(form),
      password = String(fields.get("password") || "");
    if ((signup || change || recover) && !strong(password)) {
      setError("strength");
      return;
    }
    if (signup && password !== fields.get("confirm")) {
      setError("mismatch");
      return;
    }
    setBusy(true);
    try {
      await (setup ||= configure());
      let result;
      if (change || recover)
        result = await client.auth.updateUser({ password });
      else if (forgot)
        result = await client.auth.resetPasswordForEmail(
          String(fields.get("email")),
          {
            redirectTo: location.origin + base + "auth/callback?mode=recovery",
          },
        );
      else if (signup)
        result = await client.auth.signUp({
          email: String(fields.get("email")),
          password,
          options: {
            emailRedirectTo: location.origin + base + "auth/callback",
          },
        });
      else
        result = await client.auth.signInWithPassword({
          email: String(fields.get("email")),
          password,
        });
      if (result.error) throw result.error;
      form.reset();
      if (change || recover) {
        setMessage("updated");
        if (recover) navigate(base + "workspace");
      } else if (forgot || signup) setMessage("check");
      else navigate(target());
    } catch (err: any) {
      setError(
        err?.status === 429
          ? "rate"
          : err?.code === "invalid_credentials"
            ? "invalid"
            : err?.code === "email_not_confirmed"
              ? "unconfirmed"
              : err?.code === "unexpected_failure" ||
                  err?.code === "over_email_send_rate_limit"
                ? "mailError"
                : "error",
      );
    } finally {
      setBusy(false);
    }
  }
  if (home)
    return (
      <PublicLanding
        lang={lang}
        setLang={language}
        begin={() =>
          navigate(ready && signed ? base + "workspace" : base + "login")
        }
      />
    );
  if (privatePage) {
    if (!ready || !signed)
      return <main className="account-wait">{t.wait}</main>;
    return (
      <>
        <div className="account-tools">
          <button
            title={t.account}
            aria-label={t.account}
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            {email.slice(0, 1).toUpperCase()}
          </button>
          {menu && (
            <section>
              <span className="account-email">{email}</span>
              <form onSubmit={(e) => submit(e, true)}>
                <label>
                  {t.newPassword}
                  <input
                    name="password"
                    type="password"
                    minLength={10}
                    autoComplete="new-password"
                    required
                  />
                </label>
                <p>{t.strength}</p>
                <button disabled={busy}>{t.change}</button>
              </form>
              <button
                onClick={async () => {
                  setBusy(true);
                  try {
                    await queued.catch(() => {});
                    const result = await client.auth.signOut({
                      scope: "local",
                    });
                    if (result.error) throw result.error;
                    owner = "";
                    savedState = null;
                    location.replace(base);
                  } catch {
                    setError("error");
                    setBusy(false);
                  }
                }}
              >
                {t.logout}
              </button>
              {error && <p role="alert">{t[error as keyof typeof t]}</p>}
              {message && <p role="status">{t[message as keyof typeof t]}</p>}
            </section>
          )}
        </div>
        {failed && (
          <p className="cloud-error" role="alert">
            {t.saveError}
          </p>
        )}
        {children}
      </>
    );
  }
  return (
    <main className="account-enter">
      <div className="auth-card">
        <header>
          <strong>AI Career Coach</strong>
          <select
            aria-label="Language"
            value={lang}
            onChange={(e) => language(e.target.value as Lang)}
          >
            <option value="zh-CN">简体中文</option>
            <option value="zh-TW">繁體中文</option>
            <option value="en">English</option>
          </select>
        </header>
        <button className="auth-back" onClick={() => navigate(base)}>
          ← {t.back}
        </button>
        {!forgot && !recover && (
          <nav aria-label="Authentication">
            <button
              aria-current={!signup ? "page" : undefined}
              onClick={() => navigate(base + "login")}
            >
              {t.login}
            </button>
            <button
              aria-current={signup ? "page" : undefined}
              onClick={() => navigate(base + "signup")}
            >
              {t.signup}
            </button>
          </nav>
        )}
        <h1>
          {recover ? t.change : forgot ? t.forgot : signup ? t.signup : t.login}
        </h1>
        <form onSubmit={(e) => submit(e)}>
          {!recover && (
            <label>
              {t.email}
              <input
                name="email"
                type="email"
                autoComplete="username"
                required
              />
            </label>
          )}
          {!forgot && (
            <label>
              {recover ? t.newPassword : t.password}
              <input
                name="password"
                type="password"
                minLength={signup || recover ? 10 : 1}
                autoComplete={
                  signup || recover ? "new-password" : "current-password"
                }
                required
              />
            </label>
          )}
          {signup && (
            <>
              <label>
                {t.confirm}
                <input
                  name="confirm"
                  type="password"
                  autoComplete="new-password"
                  required
                />
              </label>
              <p>{t.strength}</p>
            </>
          )}

          <button disabled={busy || !ready}>
            {busy
              ? "…"
              : recover
                ? t.change
                : forgot
                  ? t.send
                  : signup
                    ? t.signup
                    : t.login}
          </button>
        </form>
        {!forgot && !recover && (
          <button
            className="auth-link"
            onClick={() => navigate(base + "forgot-password")}
          >
            {t.forgot}
          </button>
        )}
        {error && <p role="alert">{t[error as keyof typeof t] || t.error}</p>}
        {message && <p role="status">{t[message as keyof typeof t]}</p>}
      </div>
    </main>
  );
}
