import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { LogIn, MessageCircleHeart, UserPlus, UserRound } from "lucide-react";

import { useAuth, type UserRole } from "../app/auth";
import scirScLogo from "../assets/logo-mark.png";

export function LoginPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [role, setRole] = useState<UserRole>("visitor");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (username.trim().length < 3) {
      setError("用户名至少需要 3 个字符。");
      return;
    }
    if (password.length < 8) {
      setError("密码至少需要 8 个字符。");
      return;
    }
    if (mode === "register" && !displayName.trim()) {
      setError("请输入显示名称。");
      return;
    }
    if (mode === "register" && !inviteCode.trim()) {
      setError("请输入邀请码。");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "register") {
        await register({
          username: username.trim(),
          password,
          displayName: displayName.trim(),
          role,
          inviteCode: inviteCode.trim(),
        });
      } else {
        await login(username.trim(), password);
      }
      navigate("/", { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "认证失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-8 md:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="surface-glow rounded-[30px] border border-white/70 bg-white/84 p-6 shadow-soft backdrop-blur md:p-8">
          <img src={scirScLogo} alt="心灵笔友标志" className="h-28 w-40 object-contain mix-blend-multiply" />
          <h1 className="mt-8 font-serif text-4xl text-ink md:text-5xl"><span className="lilac-text">心灵笔友</span></h1>
          <p className="mt-4 max-w-xl text-sm leading-8 text-ink/68">注册账号后，用户信箱、人工来信与咨询师任务都会绑定到真实账号。</p>
          <div className="mt-8 grid gap-3 text-sm text-ink/72 sm:grid-cols-2">
            <div className="rounded-[22px] border border-line bg-paper/75 p-4">
              <MessageCircleHeart size={18} className="text-amber" />
              <p className="mt-3 font-semibold text-ink">咨询师工作区</p>
              <p className="mt-1 leading-6">接收随机分配的人工来信，管理个人任务。</p>
            </div>
            <div className="rounded-[22px] border border-line bg-paper/75 p-4">
              <UserRound size={18} className="text-amber" />
              <p className="mt-3 font-semibold text-ink">用户信箱</p>
              <p className="mt-1 leading-6">保留来信、回信和人工咨询进度。</p>
            </div>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="rounded-[30px] border border-line bg-white/88 p-6 shadow-soft backdrop-blur md:p-8">
          <div className="inline-flex rounded-full border border-line bg-paper/75 p-1">
            <button type="button" onClick={() => setMode("login")} className={`rounded-full px-5 py-2 text-sm ${mode === "login" ? "lilac-gradient text-white" : "text-ink/72"}`}>登录</button>
            <button type="button" onClick={() => setMode("register")} className={`rounded-full px-5 py-2 text-sm ${mode === "register" ? "lilac-gradient text-white" : "text-ink/72"}`}>注册</button>
          </div>
          <h2 className="mt-5 font-serif text-3xl text-ink">{mode === "login" ? "欢迎回来" : "创建账号"}</h2>

          {mode === "register" ? (
            <>
              <div className="mt-5 inline-flex rounded-full border border-line bg-paper/75 p-1">
                <button type="button" onClick={() => setRole("visitor")} className={`rounded-full px-4 py-2 text-sm ${role === "visitor" ? "lilac-gradient text-white" : "text-ink/72"}`}>用户</button>
                <button type="button" onClick={() => setRole("counselor")} className={`rounded-full px-4 py-2 text-sm ${role === "counselor" ? "lilac-gradient text-white" : "text-ink/72"}`}>咨询师</button>
              </div>
              <label className="mt-5 block text-sm text-ink/72">显示名称<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} className="mt-2 w-full rounded-[16px] border border-line bg-paper/75 px-4 py-3 outline-none focus:border-amber" /></label>
              <label className="mt-4 block text-sm text-ink/72">邀请码<input value={inviteCode} onChange={(event) => setInviteCode(event.target.value)} className="mt-2 w-full rounded-[16px] border border-line bg-paper/75 px-4 py-3 outline-none focus:border-amber" /></label>
            </>
          ) : null}

          <label className="mt-5 block text-sm text-ink/72">用户名<input value={username} onChange={(event) => setUsername(event.target.value)} className="mt-2 w-full rounded-[16px] border border-line bg-paper/75 px-4 py-3 outline-none focus:border-amber" /></label>
          <label className="mt-4 block text-sm text-ink/72">密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-[16px] border border-line bg-paper/75 px-4 py-3 outline-none focus:border-amber" /></label>
          {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
          <button type="submit" disabled={submitting} className="lilac-gradient mt-8 inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium text-white shadow-card disabled:opacity-55">
            {mode === "login" ? <LogIn size={16} /> : <UserPlus size={16} />}
            {submitting ? "请稍候..." : mode === "login" ? "登录" : "注册并进入"}
          </button>
        </form>
      </div>
    </main>
  );
}
