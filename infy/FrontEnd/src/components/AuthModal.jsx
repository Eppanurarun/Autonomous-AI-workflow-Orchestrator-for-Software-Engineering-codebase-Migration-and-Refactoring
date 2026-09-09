import { useState } from "react";
import { X, Lock, Mail, User, ShieldCheck, Sparkles, AlertCircle } from "lucide-react";
import { loginUser, signupUser } from "../services/api";

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("developer");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let res;
      if (isSignUp) {
        if (!fullName.trim()) {
          throw new Error("Full name is required.");
        }
        res = await signupUser({ email, password, full_name: fullName, role });
      } else {
        res = await loginUser({ email, password });
      }
      onAuthSuccess(res);
      onClose();
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = (type) => {
    setError("");
    setIsSignUp(false);
    if (type === "admin") {
      setEmail("admin@codeguard.ai");
      setPassword("admin");
    } else {
      setEmail("sumit@codeguard.ai");
      setPassword("password123");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md rounded-2xl border border-cyan-400/20 bg-slate-900/95 p-6 shadow-2xl backdrop-blur-xl sm:p-8">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
        >
          <X size={18} />
        </button>

        <div className="text-center">
          <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-glow">
            <ShieldCheck size={26} />
          </div>
          <h3 className="text-2xl font-extrabold text-white">
            {isSignUp ? "Create Developer Account" : "Sign In to CodeGuard AI"}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {isSignUp ? "Access AI-powered code analysis & vulnerability detection" : "Welcome back! Enter your credentials to continue"}
          </p>
        </div>

        {/* Demo Quick Fills */}
        <div className="mt-5 flex gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-2">
          <button
            type="button"
            onClick={() => handleDemoFill("dev")}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-cyan-500/10 py-2 text-xs font-semibold text-cyan-300 border border-cyan-500/20 hover:bg-cyan-500/20 transition"
          >
            <User size={13} /> Demo Developer
          </button>
          <button
            type="button"
            onClick={() => handleDemoFill("admin")}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-indigo-500/10 py-2 text-xs font-semibold text-indigo-300 border border-indigo-500/20 hover:bg-indigo-500/20 transition"
          >
            <Sparkles size={13} /> Demo Admin
          </button>
        </div>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-300">
            <AlertCircle size={15} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {isSignUp && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
              <div className="relative">
                <User size={16} className="absolute left-3 top-3 text-slate-500" />
                <input
                  type="text"
                  required
                  placeholder="Sumit Kumar Singh"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950/80 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
            <div className="relative">
              <Mail size={16} className="absolute left-3 top-3 text-slate-500" />
              <input
                type="email"
                required
                placeholder="developer@codeguard.ai"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-3 text-slate-500" />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
              />
            </div>
          </div>

          {isSignUp && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Account Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 py-2.5 px-3 text-sm text-white focus:border-cyan-400 focus:outline-none"
              >
                <option value="developer">Developer</option>
                <option value="admin">Administrator</option>
              </select>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-600 py-3 text-sm font-extrabold text-slate-950 shadow-glow transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Processing..." : isSignUp ? "Create Account" : "Sign In"}
          </button>
        </form>

        <div className="mt-5 text-center text-xs text-slate-400">
          {isSignUp ? "Already have an account?" : "Don't have an account yet?"}{" "}
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError("");
            }}
            className="font-bold text-cyan-400 hover:underline"
          >
            {isSignUp ? "Sign In" : "Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
}
