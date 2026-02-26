import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { aiConfigApi, AiConfigData } from '@/api/ai_config';
import { extractApiErrorMessage } from '@/api/error';
import { Skeleton } from '@/components/common/Skeleton';

const AIConfig: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();

    const [config, setConfig] = useState<AiConfigData | null>(null);
    const [models, setModels] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ ok: boolean; message: string; latency?: number } | null>(null);
    const [error, setError] = useState<string | null>(null);

    const [baseUrl, setBaseUrl] = useState('');
    const [model, setModel] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [showApiKey, setShowApiKey] = useState(false);
    const isMountedRef = useRef(false);

    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const [configRes, modelsRes] = await Promise.all([
                    aiConfigApi.getConfig(),
                    aiConfigApi.getModels(),
                ]);
                const data = configRes.data.data;
                if (!isMountedRef.current) {
                    return;
                }
                if (data) {
                    setConfig(data);
                    setBaseUrl(data.base_url);
                    setModel(data.model);
                }
                setModels(modelsRes.data.data?.models ?? []);
            } catch (err: unknown) {
                if (isMountedRef.current) {
                    setError(extractApiErrorMessage(err, t('aiConfig.loadFailed')));
                }
            } finally {
                if (isMountedRef.current) {
                    setLoading(false);
                }
            }
        };
        void fetchData();
    }, [t]);

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const res = await aiConfigApi.updateConfig({
                base_url: baseUrl,
                model,
                api_key: apiKey,
            });
            if (isMountedRef.current) {
                setConfig(res.data.data ?? null);
                setApiKey('');
            }
        } catch (err: unknown) {
            if (isMountedRef.current) {
                setError(extractApiErrorMessage(err, t('aiConfig.saveFailed')));
            }
        } finally {
            if (isMountedRef.current) {
                setSaving(false);
            }
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const res = await aiConfigApi.testConnection();
            const data = res.data.data;
            if (data && isMountedRef.current) {
                setTestResult({
                    ok: data.ok,
                    message: data.ok ? t('aiConfig.testOk') : (data.error_message || t('aiConfig.testFailed')),
                    latency: data.latency_ms,
                });
            }
        } catch (err: unknown) {
            if (isMountedRef.current) {
                setTestResult({ ok: false, message: extractApiErrorMessage(err, t('aiConfig.testFailedFallback')) });
            }
        } finally {
            if (isMountedRef.current) {
                setTesting(false);
            }
        }
    };

    return (
        <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-white min-h-screen">
            <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden mx-auto bg-background-light dark:bg-background-dark pb-6">
                <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-30 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl border-b border-slate-200 dark:border-white/5">
                    <button
                        type="button"
                        onClick={() => navigate(-1)}
                        aria-label={t('a11y.back')}
                        className="focus-ring flex items-center justify-center w-10 h-10 rounded-full hover:bg-black/5 dark:hover:bg-white/5 active:bg-black/10 dark:active:bg-white/10 transition-colors"
                    >
                        <span className="material-symbols-outlined text-2xl" aria-hidden="true">arrow_back_ios_new</span>
                    </button>
                    <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center">{t('aiConfig.title')}</h2>
                    <div className="w-10" />
                </div>

                {loading && (
                    <div className="p-4 space-y-6" aria-busy="true">
                        <div className="space-y-3">
                            <Skeleton variant="text" width="6rem" className="h-4" />
                            <Skeleton variant="card" height="9rem" />
                        </div>
                        <div className="space-y-3">
                            <Skeleton variant="text" width="8rem" className="h-4" />
                            <Skeleton variant="card" height="5rem" />
                        </div>
                    </div>
                )}

                {error && (
                    <div className="mx-4 mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
                        {error}
                    </div>
                )}

                {!loading && (
                    <div className="p-4 space-y-6">
                        <section className="space-y-4">
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 px-1">{t('aiConfig.apiSettings')}</h3>
                            <div className="p-4 rounded-2xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 space-y-4 shadow-sm">
                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-slate-500 dark:text-slate-400 block px-1">{t('aiConfig.endpointLabel')}</label>
                                    <input
                                        className="w-full bg-slate-100 dark:bg-button-secondary-dark border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary placeholder:text-slate-400 dark:placeholder:text-slate-600 outline-none"
                                        placeholder={t('aiConfig.endpointPlaceholder')}
                                        type="text"
                                        value={baseUrl}
                                        onChange={(e) => setBaseUrl(e.target.value)}
                                        aria-label={t('aiConfig.endpointLabel')}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-slate-500 dark:text-slate-400 block px-1">{t('aiConfig.apiKeyLabel')}</label>
                                    <div className="relative">
                                        <input
                                            className="w-full bg-slate-100 dark:bg-button-secondary-dark border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary placeholder:text-slate-400 dark:placeholder:text-slate-600 outline-none"
                                            placeholder={config?.api_key_set ? t('aiConfig.apiKeyPlaceholderSet') : t('aiConfig.apiKeyPlaceholderUnset')}
                                            type={showApiKey ? 'text' : 'password'}
                                            value={apiKey}
                                            onChange={(e) => setApiKey(e.target.value)}
                                            aria-label={t('aiConfig.apiKeyLabel')}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowApiKey(!showApiKey)}
                                            aria-label={t('a11y.togglePasswordVisibility')}
                                            className="focus-ring absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-xl cursor-pointer"
                                        >
                                            <span className="material-symbols-outlined" aria-hidden="true">{showApiKey ? 'visibility_off' : 'visibility'}</span>
                                        </button>
                                    </div>
                                    {config?.api_key_set && apiKey.length === 0 && (
                                        <p className="text-[11px] text-amber-600 dark:text-amber-300 px-1">{t('aiConfig.clearKeyHint')}</p>
                                    )}
                                </div>
                                <div className="flex items-center justify-between p-1">
                                    {testResult && (
                                        <div className="flex items-center gap-2" aria-live="polite">
                                            <span className={`material-symbols-outlined text-sm ${testResult.ok ? 'text-green-500' : 'text-red-500'}`} aria-hidden="true">
                                                {testResult.ok ? 'check_circle' : 'error'}
                                            </span>
                                            <span className="text-xs text-slate-600 dark:text-slate-300">
                                                {testResult.message}
                                                {testResult.latency !== undefined && ` (${testResult.latency}ms)`}
                                            </span>
                                        </div>
                                    )}
                                    {!testResult && <div />}
                                    <button
                                        type="button"
                                        onClick={handleTest}
                                        disabled={testing}
                                        className="focus-ring text-xs font-bold text-primary px-3 py-1 bg-primary/10 rounded-full active:scale-95 transition-all disabled:opacity-50"
                                    >
                                        {testing ? t('aiConfig.testing') : t('aiConfig.testConnection')}
                                    </button>
                                </div>
                            </div>
                        </section>

                        <section className="space-y-4">
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 px-1">{t('aiConfig.modelSelection')}</h3>
                            <div className="p-4 rounded-2xl bg-white dark:bg-card-dark border border-slate-200 dark:border-white/5 space-y-4 shadow-sm">
                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-slate-500 dark:text-slate-400 block px-1">{t('aiConfig.modelName')}</label>
                                    <div className="relative">
                                        <input
                                            className="w-full bg-slate-100 dark:bg-button-secondary-dark border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary placeholder:text-slate-400 dark:placeholder:text-slate-600 outline-none"
                                            placeholder={t('aiConfig.modelPlaceholder')}
                                            type="text"
                                            value={model}
                                            onChange={(e) => setModel(e.target.value)}
                                            list="model-list"
                                            aria-label={t('aiConfig.modelName')}
                                        />
                                        <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-slate-500" aria-hidden="true">expand_more</span>
                                    </div>
                                    {models.length > 0 && (
                                        <datalist id="model-list">
                                            {models.map((m) => <option key={m} value={m} />)}
                                        </datalist>
                                    )}
                                </div>
                            </div>
                        </section>
                    </div>
                )}

                <div className="sticky bottom-0 p-4 bg-background-light/80 dark:bg-background-dark/80 backdrop-blur-xl border-t border-slate-200 dark:border-white/5 z-40">
                    <button
                        type="button"
                        onClick={handleSave}
                        disabled={saving || loading}
                        className="focus-ring w-full h-14 bg-primary text-white font-bold rounded-2xl flex items-center justify-center shadow-lg active:scale-[0.98] transition-all disabled:opacity-50"
                    >
                        {saving ? t('aiConfig.saving') : t('aiConfig.saveConfiguration')}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AIConfig;
