import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi } from '@/api/auth';
import { extractApiErrorDetail, extractApiErrorMessage } from '@/api/error';
import { useAuthStore } from '@/store/authStore';

const Login: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const setAuth = useAuthStore((state) => state.setAuth);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [tokenInput, setTokenInput] = useState('');
    const tokenInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        tokenInputRef.current?.focus();
    }, []);

    const handleBearerLogin = async () => {
        const token = tokenInput.trim();
        if (!token) {
            setError(t('login.errorEmptyToken'));
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const response = await authApi.meWithToken(token);
            const user = response.data.data.user;
            setAuth(token, user);
            navigate('/');
        } catch (err: unknown) {
            const detail = extractApiErrorDetail(err);
            if (detail === 'TOKEN_MISSING' || detail === 'TOKEN_INVALID') {
                setError(t('login.errorInvalidToken'));
            } else {
                setError(detail || extractApiErrorMessage(err, t('login.errorTokenFailed')));
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark text-slate-900 dark:text-white">
            <header className="flex items-center justify-between p-4 pb-2 sticky top-0 z-20">
                <button
                    type="button"
                    onClick={() => navigate(-1)}
                    aria-label={t('a11y.back')}
                    className="focus-ring flex items-center justify-center p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                >
                    <span className="material-symbols-outlined text-slate-900 dark:text-white text-2xl" aria-hidden="true">arrow_back</span>
                </button>
                <h2 className="text-lg font-bold leading-tight">{t('login.title')}</h2>
                <div className="w-10" />
            </header>

            <main className="flex-1 flex flex-col items-center justify-center px-6">
                <div className="w-full max-w-sm md:max-w-md">
                    <div className="flex flex-col items-center text-center mb-8">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-lg shadow-primary/20 mb-4">
                            <span className="material-symbols-outlined text-white text-4xl" aria-hidden="true">memory</span>
                        </div>
                        <h1 className="text-3xl font-bold tracking-tight mb-2">TeleMemory</h1>
                        <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                            {t('login.subtitleToken')}
                        </p>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm" aria-live="polite">
                            {error}
                        </div>
                    )}

                    <form
                        className="space-y-4"
                        onSubmit={(e) => {
                            e.preventDefault();
                            void handleBearerLogin();
                        }}
                    >
                        <label className="block">
                            <span className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">{t('login.bearerToken')}</span>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                                    <span className="material-symbols-outlined text-slate-400 text-xl" aria-hidden="true">key</span>
                                </div>
                                <input
                                    ref={tokenInputRef}
                                    className="form-input block w-full pl-11 pr-4 py-3.5 bg-white dark:bg-card-dark border border-slate-200 dark:border-border-dark rounded-xl text-base focus:ring-2 focus:ring-primary focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-muted-dark dark:text-white font-mono text-sm"
                                    placeholder={t('login.tokenPlaceholder')}
                                    type="text"
                                    value={tokenInput}
                                    onChange={(e) => setTokenInput(e.target.value)}
                                    disabled={loading}
                                    autoComplete="off"
                                    aria-label={t('login.bearerToken')}
                                />
                            </div>
                        </label>

                        <button
                            type="submit"
                            disabled={loading || !tokenInput.trim()}
                            className="focus-ring w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-semibold py-4 px-4 rounded-xl shadow-lg shadow-primary/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                        >
                            {loading ? <span>{t('login.verifying')}</span> : (
                                <>
                                    <span>{t('login.loginWithToken')}</span>
                                    <span className="material-symbols-outlined text-xl" aria-hidden="true">vpn_key</span>
                                </>
                            )}
                        </button>
                    </form>
                </div>
            </main>

            <footer className="p-6 text-center">
                <p className="text-xs text-slate-400">
                    {t('login.footer')}
                </p>
            </footer>
        </div>
    );
};

export default Login;
