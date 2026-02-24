import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { extractApiErrorDetail, extractApiErrorMessage } from '@/api/error';
import { useAuthStore } from '@/store/authStore';

type LoginStep = 'phone' | 'code' | 'password';

const Login: React.FC = () => {
    const navigate = useNavigate();
    const setAuth = useAuthStore((state) => state.setAuth);

    const [step, setStep] = useState<LoginStep>('phone');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [countdown, setCountdown] = useState(0);

    const [phoneNumber, setPhoneNumber] = useState('');
    const [code, setCode] = useState('');
    const [password, setPassword] = useState('');
    const [authSessionId, setAuthSessionId] = useState('');
    const [maskedPhone, setMaskedPhone] = useState('');

    useEffect(() => {
        let timer: number;
        if (countdown > 0) {
            timer = window.setInterval(() => {
                setCountdown((c) => c - 1);
            }, 1000);
        }
        return () => clearInterval(timer);
    }, [countdown]);

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
            setError(detail || extractApiErrorMessage(err, 'Failed to send code'));
        } finally {
            setLoading(false);
        }
    };

    const handleSignIn = async () => {
        if (!code) return;
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.signIn({
                auth_session_id: authSessionId,
                phone_number: phoneNumber,
                code: code,
                password: password || undefined
            });
            const data = response.data.data;
            setAuth(data.token, data.user);
            navigate('/');
        } catch (err: unknown) {
            const detail = extractApiErrorDetail(err);
            if (detail === 'PASSWORD_REQUIRED') {
                setStep('password');
            } else if (detail === 'CODE_INVALID') {
                setError('Invalid verification code');
            } else if (detail === 'CODE_EXPIRED' || detail === 'SESSION_NOT_FOUND') {
                setStep('code');
                setCode('');
                setPassword('');
                setCountdown(0);
                setError('Verification session expired. Please resend the code and try again.');
            } else if (detail?.includes('FLOOD_WAIT')) {
                setError(`Too many attempts. Please wait ${detail.split('_').pop()} seconds.`);
            } else {
                setError(detail || extractApiErrorMessage(err, 'Login failed'));
            }
        } finally {
            setLoading(false);
        }
    };

    const renderPhoneStep = () => (
        <div className="space-y-4">
            <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">Phone Number</span>
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                        <span className="material-symbols-outlined text-slate-400 text-xl">call</span>
                    </div>
                    <input
                        className="form-input block w-full pl-11 pr-4 py-3.5 bg-white dark:bg-[#192d33] border border-slate-200 dark:border-[#325a67] rounded-xl text-base focus:ring-2 focus:ring-primary focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-[#92bbc9] dark:text-white"
                        placeholder="+8613800138000"
                        type="tel"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        disabled={loading}
                    />
                </div>
            </label>
            <button
                onClick={handleSendCode}
                disabled={loading || !phoneNumber}
                className="w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-semibold py-4 px-4 rounded-xl shadow-lg shadow-primary/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
                {loading ? <span>Sending...</span> : (
                    <>
                        <span>Send Login Code</span>
                        <span className="material-symbols-outlined text-xl">send</span>
                    </>
                )}
            </button>
        </div>
    );

    const renderCodeStep = () => (
        <div className="space-y-4">
            <div className="text-center mb-2">
                <p className="text-sm text-slate-500">Code sent to {maskedPhone}</p>
            </div>
            <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">Verification Code</span>
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                        <span className="material-symbols-outlined text-slate-400 text-xl">password</span>
                    </div>
                    <input
                        className="form-input block w-full pl-11 pr-4 py-3.5 bg-white dark:bg-[#192d33] border border-slate-200 dark:border-[#325a67] rounded-xl text-base focus:ring-2 focus:ring-primary focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-[#92bbc9] dark:text-white"
                        placeholder="12345"
                        type="text"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        disabled={loading}
                    />
                </div>
            </label>
            <button
                onClick={handleSignIn}
                disabled={loading || !code}
                className="w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-semibold py-4 px-4 rounded-xl shadow-lg shadow-primary/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
                {loading ? <span>Verifying...</span> : (
                    <>
                        <span>Login</span>
                        <span className="material-symbols-outlined text-xl">login</span>
                    </>
                )}
            </button>
            <div className="text-center mt-2">
                <button
                    onClick={() => setStep('phone')}
                    className="text-sm text-primary hover:underline"
                >
                    Change phone number
                </button>
                {countdown > 0 ? (
                    <p className="text-xs text-slate-400 mt-2">Resend code in {countdown}s</p>
                ) : (
                    <button onClick={handleSendCode} className="text-xs text-primary hover:underline mt-2 block mx-auto">Resend code</button>
                )}
            </div>
        </div>
    );

    const renderPasswordStep = () => (
        <div className="space-y-4">
            <div className="text-center mb-2">
                <p className="text-sm text-slate-500">Two-Step Verification Required</p>
            </div>
            <label className="block">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 block">Cloud Password</span>
                <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                        <span className="material-symbols-outlined text-slate-400 text-xl">lock</span>
                    </div>
                    <input
                        className="form-input block w-full pl-11 pr-4 py-3.5 bg-white dark:bg-[#192d33] border border-slate-200 dark:border-[#325a67] rounded-xl text-base focus:ring-2 focus:ring-primary focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-[#92bbc9] dark:text-white"
                        placeholder="Your 2FA password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={loading}
                    />
                </div>
            </label>
            <button
                onClick={handleSignIn}
                disabled={loading || !password}
                className="w-full bg-primary hover:bg-sky-500 disabled:opacity-50 text-white font-semibold py-4 px-4 rounded-xl shadow-lg shadow-primary/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
                {loading ? <span>Verifying...</span> : (
                    <>
                        <span>Confirm Password</span>
                        <span className="material-symbols-outlined text-xl">verified_user</span>
                    </>
                )}
            </button>
        </div>
    );

    return (
        <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark text-slate-900 dark:text-white">
            <header className="flex items-center justify-between p-4 pb-2 sticky top-0 z-20">
                <button onClick={() => step === 'phone' ? navigate(-1) : setStep('phone')} className="flex items-center justify-center p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
                    <span className="material-symbols-outlined text-slate-900 dark:text-white text-2xl">arrow_back</span>
                </button>
                <h2 className="text-lg font-bold leading-tight">Login</h2>
                <div className="w-10"></div>
            </header>

            <main className="flex-1 flex flex-col items-center justify-center px-6">
                <div className="w-full max-w-sm">
                    <div className="flex flex-col items-center text-center mb-8">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-lg shadow-primary/20 mb-4">
                            <span className="material-symbols-outlined text-white text-4xl">memory</span>
                        </div>
                        <h1 className="text-3xl font-bold tracking-tight mb-2">TeleMemory</h1>
                        <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                            {step === 'phone' ? 'Log in to start indexing your messages.' : 'Verify your identity to continue.'}
                        </p>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    {step === 'phone' && renderPhoneStep()}
                    {step === 'code' && renderCodeStep()}
                    {step === 'password' && renderPasswordStep()}
                </div>
            </main>

            <footer className="p-6 text-center">
                <p className="text-xs text-slate-400">
                    By continuing, you agree to the indexing of your local data.
                </p>
            </footer>
        </div>
    );
};

export default Login;
