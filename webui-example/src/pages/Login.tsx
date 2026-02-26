import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi } from '@/api/auth';
import { extractApiErrorDetail, extractApiErrorMessage } from '@/api/error';
import { useAuthStore } from '@/store/authStore';

type LoginStep = 'phone' | 'code' | 'password';
type LoginMode = 'phone' | 'token';

const Login: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const setAuth = useAuthStore((state) => state.setAuth);

    const [loginMode, setLoginMode] = useState<LoginMode>('phone');
    const [step, setStep] = useState<LoginStep>('phone');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [countdown, setCountdown] = useState(0);

    const [phoneNumber, setPhoneNumber] = useState('');
    const [code, setCode] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [authSessionId, setAuthSessionId] = useState('');
    const [maskedPhone, setMaskedPhone] = useState('');
    const [tokenInput, setTokenInput] = useState('');

    const phoneInputRef = useRef<HTMLInputElement>(null);
    const codeInputRef = useRef<HTMLInputElement>(null);
    const passwordInputRef = useRef<HTMLInputElement>(null);
    const tokenInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        let timer: number;
        if (countdown > 0) {
            timer = window.setInterval(() => {
                setCountdown((c) => c - 1);
            }, 1000);
        }
        return () => clearInterval(timer);
    }, [countdown]);

    useEffect(() => {
        if (loginMode === 'token') tokenInputRef.current?.focus();
        if (loginMode === 'phone' && step === 'phone') phoneInputRef.current?.focus();
        if (loginMode === 'phone' && step === 'code') codeInputRef.current?.focus();
        if (loginMode === 'phone' && step === 'password') passwordInputRef.current?.focus();
    }, [loginMode, step]);

    const handleSendCode = async () => {
        if (!phoneNumber) return;
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.sendCode({ phone_number: phoneNumber });
            const data = response.data.data;
            setAuthSessionId(data.auth_session_id);
            setMaskedPhone(data.phone_number_masked);
            setStep('code');
            setCountdown(data.expires_in || 60);
        } catch (err: unknown) {
            const detail = extractApiErrorDetail(err);
            setError(detail || extractApiErrorMessage(err, t('login.errorSendCode')));
        } finally {
            setLoading(false);
        }
    };

    const handleSignIn = async () => {
        if (!code && step !== 'password') return;
        if (!password && step === 'password') return;

        setLoading(true);
        setError(null);
        try {
            const response = await authApi.signIn({
                auth_session_id: authSessionId,
                phone_number: phoneNumber,
                code,
                password: password || undefined,
            });
            const data = response.data.data;
            setAuth(data.token, data.user);
            navigate('/');
        } catch (err: unknown) {
            const detail = extractApiErrorDetail(err);
            if (detail === 'PASSWORD_REQUIRED') {
                setStep('password');
            } else if (detail === 'CODE_INVALID') {
                setError(t('login.errorInvalidCode'));
            } else if (detail === 'CODE_EXPIRED' || detail === 'SESSION_NOT_FOUND') {
                setStep('code');
                setCode('');
                setPassword('');
                setCountdown(0);
                setError(t('login.errorSessionExpired'));
            } else if (detail?.includes('FLOOD_WAIT')) {
                setError(t('login.errorTooManyAttempts', { seconds: detail.split('_').pop() }));
            } else {
                setError(detail || extractApiErrorMessage(err, t('login.errorLoginFailed')));
            }
        } finally {
            setLoading(false);
        }
    };

    const handleTokenLogin = async () => {
        const token = tokenInput.trim();
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.tokenLogin({ token });
            const data = response.data.data;
            setAuth(data.token, data.user);
            navigate('/');
        } catch (err: unknown) {
            const detail = extractApiErrorDetail(err);
            if (detail === 'TOKEN_INVALID') {
                setError(t('login.errorInvalidToken'));
            } else if (detail === 'TOKEN_EMPTY') {
                setError(t('login.errorEmptyToken'));
            } else {
                setError(detail || extractApiErrorMessage(err, t('login.errorTokenFailed')));
            }
        } finally {
            setLoading(false);
        }
    };

    const switchMode = (mode: LoginMode) => {
        setLoginMode(mode);
        setError(null);
        setStep('phone');
    };

    const renderPhoneStep = () => (
        <form
            className="space-y-4"
            onSubmit={(e) => {
                e.preventDefault();
                void handleSendCode();
            }}
        >
            <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">{t('login.phoneNumber')}</span>
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                        <span className="material-symbols-outlined text-slate-400 text-xl" aria-hidden="true">call</span>
                    </div>
                    <input
                        ref={phoneInputRef}
                        className="form-input block w-full pl-11 pr-4 py-3.5 bg-white dark:bg-card-dark border border-slate-200 dark:border-border-dark rounded-xl text-base focus:ring-2 focus:ring-primary focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-muted-dark dark:text-white"
                        placeholder="+8613800138000"
                        type="tel"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        disabled={loading}
                        aria-label={t('login.phoneNumber')}
                    />
                </div>
            </label>
            <button
                type="submit"
                disabled={loading || !phoneNumber}
                className="focus-ring w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-semibold py-4 px-4 rounded-xl shadow-lg shadow-primary/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
                {loading ? <span>{t('login.sending')}</span> : (
                    <>
                        <span>{t('login.sendCode')}</span>
                        <span className="material-symbols-outlined text-xl" aria-hidden="true">send</span>
                    </>
                )}
            </button>
        </form>
    );

    const renderCodeStep = () => (
        <form
            className="space-y-4"
            onSubmit={(e) => {
                e.preventDefault();
                void handleSignIn();
            }}
        >
            <div className="text-center mb-2">
                <p className="text-sm text-slate-500">{t('login.codeSentTo', { phone: maskedPhone })}</p>
            </div>
            <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">{t('login.verificationCode')}</span>
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                        <span className="material-symbols-outlined text-slate-400 text-xl" aria-hidden="true">password</span>
                    </div>
                    <input
                        ref={codeInputRef}
                        className="form-input block w-full pl-11 pr-4 py-3.5 bg-white dark:bg-card-dark border border-slate-200 dark:border-border-dark rounded-xl text-base focus:ring-2 focus:ring-primary focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-muted-dark dark:text-white"
                        placeholder="12345"
                        type="text"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        disabled={loading}
                        aria-label={t('login.verificationCode')}
                    />
                </div>
            </label>
            <button
                type="submit"
                disabled={loading || !code}
                className="focus-ring w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-semibold py-4 px-4 rounded-xl shadow-lg shadow-primary/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
                {loading ? <span>{t('login.verifying')}</span> : (
                    <>
                        <span>{t('login.login')}</span>
                        <span className="material-symbols-outlined text-xl" aria-hidden="true">login</span>
                    </>
                )}
            </button>
            <div className="text-center mt-2">
                <button
                    type="button"
                    onClick={() => setStep('phone')}
                    className="focus-ring text-sm text-primary hover:underline"
                >
                    {t('login.changePhone')}
                </button>
                {countdown > 0 ? (
                    <p className="text-xs text-slate-400 mt-2">{t('login.resendIn', { count: countdown })}</p>
                ) : (
                    <button type="button" onClick={() => void handleSendCode()} className="focus-ring text-xs text-primary hover:underline mt-2 block mx-auto">{t('login.resendCode')}</button>
                )}
            </div>
        </form>
    );

    const renderPasswordStep = () => (
        <form
            className="space-y-4"
            onSubmit={(e) => {
                e.preventDefault();
                void handleSignIn();
            }}
        >
            <div className="text-center mb-2">
                <p className="text-sm text-slate-500">{t('login.twoStepRequired')}</p>
            </div>
            <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">{t('login.cloudPassword')}</span>
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                        <span className="material-symbols-outlined text-slate-400 text-xl" aria-hidden="true">lock</span>
                    </div>
                    <input
                        ref={passwordInputRef}
                        className="form-input block w-full pl-11 pr-11 py-3.5 bg-white dark:bg-card-dark border border-slate-200 dark:border-border-dark rounded-xl text-base focus:ring-2 focus:ring-primary focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-muted-dark dark:text-white"
                        placeholder={t('login.passwordPlaceholder')}
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={loading}
                        aria-label={t('login.cloudPassword')}
                    />
                    <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        aria-label={t('a11y.togglePasswordVisibility')}
                        className="focus-ring absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
                    >
                        <span className="material-symbols-outlined" aria-hidden="true">{showPassword ? 'visibility_off' : 'visibility'}</span>
                    </button>
                </div>
            </label>
            <button
                type="submit"
                disabled={loading || !password}
                className="focus-ring w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-semibold py-4 px-4 rounded-xl shadow-lg shadow-primary/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
                {loading ? <span>{t('login.verifying')}</span> : (
                    <>
                        <span>{t('login.confirmPassword')}</span>
                        <span className="material-symbols-outlined text-xl" aria-hidden="true">verified_user</span>
                    </>
                )}
            </button>
        </form>
    );

    const renderTokenStep = () => (
        <form
            className="space-y-4"
            onSubmit={(e) => {
                e.preventDefault();
                void handleTokenLogin();
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
            <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
                {t('login.tokenHint')} <code className="bg-slate-100 dark:bg-code-dark px-1.5 py-0.5 rounded text-[11px]">session/auth_tokens.json</code>
            </p>
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
    );

    return (
        <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark text-slate-900 dark:text-white">
            <header className="flex items-center justify-between p-4 pb-2 sticky top-0 z-20">
                <button
                    type="button"
                    onClick={() => step === 'phone' && loginMode === 'phone' ? navigate(-1) : (loginMode === 'token' ? navigate(-1) : setStep('phone'))}
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
                            {loginMode === 'token'
                                ? t('login.subtitleToken')
                                : (step === 'phone' ? t('login.subtitlePhone') : t('login.subtitleVerify'))}
                        </p>
                    </div>

                    <div className="flex bg-slate-100 dark:bg-dropdown-dark rounded-xl p-1 mb-6" role="tablist" aria-label={t('login.title')}>
                        <button
                            type="button"
                            onClick={() => switchMode('phone')}
                            role="tab"
                            aria-selected={loginMode === 'phone'}
                            className={`focus-ring flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-medium transition-all ${loginMode === 'phone' ? 'bg-white dark:bg-highlight-dark text-primary shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}`}
                        >
                            <span className="material-symbols-outlined text-lg" aria-hidden="true">phone_iphone</span>
                            <span>{t('login.modePhone')}</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => switchMode('token')}
                            role="tab"
                            aria-selected={loginMode === 'token'}
                            className={`focus-ring flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-medium transition-all ${loginMode === 'token' ? 'bg-white dark:bg-highlight-dark text-primary shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}`}
                        >
                            <span className="material-symbols-outlined text-lg" aria-hidden="true">vpn_key</span>
                            <span>{t('login.modeToken')}</span>
                        </button>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm" aria-live="polite">
                            {error}
                        </div>
                    )}

                    {loginMode === 'token' && renderTokenStep()}
                    {loginMode === 'phone' && step === 'phone' && renderPhoneStep()}
                    {loginMode === 'phone' && step === 'code' && renderCodeStep()}
                    {loginMode === 'phone' && step === 'password' && renderPasswordStep()}
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
