import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, LogIn, Database, Loader2, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  const validate = (): boolean => {
    const errors: { email?: string; password?: string } = {};
    if (!email.trim()) errors.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Enter a valid email address.';
    if (!password) errors.password = 'Password is required.';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validate()) return;
    try {
      await login(email, password);
      navigate('/dashboard', { replace: true });
    } catch {
      // Error is displayed from the store
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-primary/5 blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-primary/3 blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Card */}
        <div className="bg-card border border-border rounded-2xl shadow-2xl overflow-hidden">
          {/* Header gradient bar */}
          <div className="h-1 bg-gradient-to-r from-primary via-violet-400 to-purple-300" />

          <div className="p-8">
            {/* Logo + Title */}
            <div className="flex flex-col items-center mb-8">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4 shadow-lg">
                <Database className="w-7 h-7 text-primary" />
              </div>
              <h1 className="text-2xl font-bold text-foreground tracking-tight">Welcome back</h1>
              <p className="text-muted-foreground text-sm mt-1">Sign in to your AskDB account</p>
            </div>

            {/* Global error */}
            {error && (
              <div className="flex items-start gap-3 p-4 mb-6 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm animate-fade-in">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-5">
              {/* Email */}
              <div className="space-y-1.5">
                <label htmlFor="login-email" className="text-sm font-medium text-foreground">
                  Email address
                </label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setFieldErrors((p) => ({ ...p, email: undefined })); clearError(); }}
                  placeholder="you@example.com"
                  className={`w-full px-4 py-2.5 rounded-xl bg-secondary border text-sm text-foreground placeholder-muted-foreground outline-none transition-all duration-200
                    focus:ring-2 focus:ring-primary/40 focus:border-primary
                    ${fieldErrors.email ? 'border-destructive focus:ring-destructive/30' : 'border-border'}`}
                />
                {fieldErrors.email && (
                  <p className="text-xs text-destructive flex items-center gap-1 mt-1">
                    <AlertCircle className="w-3 h-3" /> {fieldErrors.email}
                  </p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <label htmlFor="login-password" className="text-sm font-medium text-foreground">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setFieldErrors((p) => ({ ...p, password: undefined })); clearError(); }}
                    placeholder="••••••••"
                    className={`w-full px-4 py-2.5 pr-12 rounded-xl bg-secondary border text-sm text-foreground placeholder-muted-foreground outline-none transition-all duration-200
                      focus:ring-2 focus:ring-primary/40 focus:border-primary
                      ${fieldErrors.password ? 'border-destructive focus:ring-destructive/30' : 'border-border'}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    tabIndex={-1}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p className="text-xs text-destructive flex items-center gap-1 mt-1">
                    <AlertCircle className="w-3 h-3" /> {fieldErrors.password}
                  </p>
                )}
              </div>

              {/* Submit */}
              <button
                id="login-submit"
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-primary text-primary-foreground font-semibold text-sm
                  transition-all duration-200 hover:opacity-90 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed
                  shadow-lg shadow-primary/20 mt-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" />
                    Sign in
                  </>
                )}
              </button>
            </form>

            {/* Register link */}
            <p className="text-center text-sm text-muted-foreground mt-6">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="text-primary font-medium hover:underline underline-offset-4 transition-colors"
              >
                Create account
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          AskDB — Natural Language to SQL
        </p>
      </div>
    </div>
  );
}
