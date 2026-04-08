import { useState, FormEvent } from 'react';
import { apiClient, ApiError } from '../api/client';

interface LoginFormProps { onLogin: () => void; }

function LoginForm({ onLogin }: LoginFormProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiClient.login(username, password);
      onLogin();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.status === 401 ? 'Invalid username or password' : `Login failed: ${err.message}`);
      } else {
        setError('Unable to connect to server');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-phthalo">
            <svg className="h-8 w-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="font-display text-2xl font-bold text-phthalo-deep">Spectis</h1>
          <p className="mt-1 text-sm text-ui-text-tertiary">AI Observability Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-xl border border-ui-border bg-white p-6 shadow-sm">
          <h2 className="mb-6 font-display text-lg font-semibold text-ui-text">Sign in</h2>

          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <div className="mb-4">
            <label htmlFor="username" className="mb-1.5 block text-sm font-medium text-ui-text-secondary">Username</label>
            <input id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username"
              className="w-full rounded-lg border border-ui-border bg-cream px-3 py-2.5 text-sm text-ui-text placeholder-ui-text-tertiary outline-none focus:border-phthalo-mid focus:ring-1 focus:ring-phthalo-mid"
              placeholder="Enter your username" />
          </div>

          <div className="mb-6">
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ui-text-secondary">Password</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password"
              className="w-full rounded-lg border border-ui-border bg-cream px-3 py-2.5 text-sm text-ui-text placeholder-ui-text-tertiary outline-none focus:border-phthalo-mid focus:ring-1 focus:ring-phthalo-mid"
              placeholder="Enter your password" />
          </div>

          <button type="submit" disabled={loading}
            className="w-full rounded-lg bg-phthalo px-4 py-2.5 font-display text-sm font-semibold text-white transition-colors hover:bg-phthalo-deep disabled:cursor-not-allowed disabled:opacity-50">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginForm;
