import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, UserPlus, Database, Loader2, AlertCircle, Check } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

// Password strength helper
function getPasswordStrength(pwd: string): { score: number; label: string; color: string } {
  if (!pwd) return { score: 0, label: '', color: '' };
  let score = 0;
  if (pwd.length >= 8) score++;
  if (pwd.length >= 12) score++;
  if (/[A-Z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd)) score++;
  if (/[^A-Za-z0-9]/.test(pwd)) score++;

  if (score <= 1) return { score, label: 'Weak', color: 'bg-destructive' };
  if (score <= 2) return { score, label: 'Fair', color: 'bg-yellow-500' };
  if (score <= 3) return { score, label: 'Good', color: 'bg-blue-500' };
  return { score, label: 'Strong', color: 'bg-green-500' };
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, isLoading, error, clearError } = useAuthStore();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const strength = getPasswordStrength(password);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!fullName.trim()) errors.fullName = 'Full name is required.';
    if (!email.trim()) errors.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Enter a valid email address.';
    if (!password) errors.password = 'Password is required.';
    else if (password.length < 8) errors.password = 'Password must be at least 8 characters.';
    if (!confirmPassword) errors.confirmPassword = 'Please confirm your password.';
    else if (password !== confirmPassword) errors.confirmPassword = 'Passwords do not match.';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const clearField = (field: string) => {
    setFieldErrors((p) => ({ ...p, [field]: undefined as any }));
    clearError();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!validate()) return;
    try {
      await register(fullName.trim(), email, password);
      navigate('/dashboard', { replace: true });
    } catch {
      // Error displayed from store
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full bg-violet-500/5 blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Card */}
        <div className="bg-card border border-border rounded-2xl shadow-2xl overflow-hidden">
          {/* Header gradient bar */}
          <div className="h-1 bg-gradient-to-r from-violet-400 via-primary to-purple-400" />

          <div className="p-8">
            {/* Logo + Title */}
            <div className="flex flex-col items-center mb-8">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4 shadow-lg">
                <Database className="w-7 h-7 text-primary" />
              </div>
              <h1 className="text-2xl font-bold text-foreground tracking-tight">Create account</h1>
              <p className="text-muted-foreground text-sm mt-1">Get started with AskDB today</p>
            </div>

            {/* Global error */}
            {error && (
              <div className="flex items-start gap-3 p-4 mb-6 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm animate-fade-in">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-5">
              {/* Full Name */}
              <div className="space-y-1.5">
                <label htmlFor="register-fullname" className="text-sm font-medium text-foreground">
                  Full name
                </label>
                <input
                  id="register-fullname"
                  type="text"
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => { setFullName(e.target.value); clearField('fullName'); }}
                  placeholder="John Doe"
                  className={`w-full px-4 py-2.5 rounded-xl bg-secondary border text-sm text-foreground placeholder-muted-foreground outline-none transition-all duration-200
                    focus:ring-2 focus:ring-primary/40 focus:border-primary
                    ${fieldErrors.fullName ? 'border-destructive focus:ring-destructive/30' : 'border-border'}`}
                />
                {fieldErrors.fullName && (
                  <p className="text-xs text-destructive flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> {fieldErrors.fullName}
                  </p>
                )}
              </div>

              {/* Email */}
              <div className="space-y-1.5">
                <label htmlFor="register-email" className="text-sm font-medium text-foreground">
                  Email address
                </label>
                <input
                  id="register-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); clearField('email'); }}
                  placeholder="you@example.com"
                  className={`w-full px-4 py-2.5 rounded-xl bg-secondary border text-sm text-foreground placeholder-muted-foreground outline-none transition-all duration-200
                    focus:ring-2 focus:ring-primary/40 focus:border-primary
                    ${fieldErrors.email ? 'border-destructive focus:ring-destructive/30' : 'border-border'}`}
                />
                {fieldErrors.email && (
                  <p className="text-xs text-destructive flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> {fieldErrors.email}
                  </p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <label htmlFor="register-password" className="text-sm font-medium text-foreground">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="register-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); clearField('password'); }}
                    placeholder="Minimum 8 characters"
                    className={`w-full px-4 py-2.5 pr-12 rounded-xl bg-secondary border text-sm text-foreground placeholder-muted-foreground outline-none transition-all duration-200
                      focus:ring-2 focus:ring-primary/40 focus:border-primary
                      ${fieldErrors.password ? 'border-destructive focus:ring-destructive/30' : 'border-border'}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {/* Strength indicator */}
                {password && (
                  <div className="space-y-1">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <div
                          key={i}
                          className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                            i <= strength.score ? strength.color : 'bg-border'
                          }`}
                        />
                      ))}
                    </div>
                    <p className={`text-xs ${
                      strength.label === 'Strong' ? 'text-green-500' :
                      strength.label === 'Good' ? 'text-blue-500' :
                      strength.label === 'Fair' ? 'text-yellow-500' : 'text-destructive'
                    }`}>
                      {strength.label} password
                    </p>
                  </div>
                )}
                {fieldErrors.password && (
                  <p className="text-xs text-destructive flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> {fieldErrors.password}
                  </p>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-1.5">
                <label htmlFor="register-confirm" className="text-sm font-medium text-foreground">
                  Confirm password
                </label>
                <div className="relative">
                  <input
                    id="register-confirm"
                    type={showConfirm ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => { setConfirmPassword(e.target.value); clearField('confirmPassword'); }}
                    placeholder="Re-enter your password"
                    className={`w-full px-4 py-2.5 pr-12 rounded-xl bg-secondary border text-sm text-foreground placeholder-muted-foreground outline-none transition-all duration-200
                      focus:ring-2 focus:ring-primary/40 focus:border-primary
                      ${fieldErrors.confirmPassword ? 'border-destructive focus:ring-destructive/30' : 'border-border'}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((p) => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    tabIndex={-1}
                  >
                    {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                  {/* Match indicator */}
                  {confirmPassword && password === confirmPassword && (
                    <div className="absolute right-10 top-1/2 -translate-y-1/2">
                      <Check className="w-4 h-4 text-green-500" />
                    </div>
                  )}
                </div>
                {fieldErrors.confirmPassword && (
                  <p className="text-xs text-destructive flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> {fieldErrors.confirmPassword}
                  </p>
                )}
              </div>

              {/* Submit */}
              <button
                id="register-submit"
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-primary text-primary-foreground font-semibold text-sm
                  transition-all duration-200 hover:opacity-90 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed
                  shadow-lg shadow-primary/20 mt-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating account…
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    Create account
                  </>
                )}
              </button>
            </form>

            {/* Login link */}
            <p className="text-center text-sm text-muted-foreground mt-6">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-primary font-medium hover:underline underline-offset-4 transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-6">
          AskDB — Natural Language to SQL
        </p>
      </div>
    </div>
  );
}
