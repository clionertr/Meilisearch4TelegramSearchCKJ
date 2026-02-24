import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { aiConfigApi, AiConfigData } from '../src/api/ai_config';

const AIConfig: React.FC = () => {
    const navigate = useNavigate();
    const [config, setConfig] = useState<AiConfigData | null>(null);
    const [models, setModels] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ ok: boolean; message: string; latency?: number } | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Form state
    const [baseUrl, setBaseUrl] = useState('');
    const [model, setModel] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [showApiKey, setShowApiKey] = useState(false);

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
                if (data) {
                    setConfig(data);
                    setBaseUrl(data.base_url);
                    setModel(data.model);
                }
                setModels(modelsRes.data.data?.models ?? []);
            } catch (err: any) {
                setError(err.response?.data?.message || 'Failed to load AI config');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const res = await aiConfigApi.updateConfig({
                base_url: baseUrl,
                model: model,
                api_key: apiKey || undefined,
            });
            setConfig(res.data.data ?? null);
            setApiKey('');
        } catch (err: any) {
            setError(err.response?.data?.message || 'Failed to save config');
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const res = await aiConfigApi.testConnection();
            const data = res.data.data;
            if (data) {
                setTestResult({
                    ok: data.ok,
                    message: data.ok ? 'Connection verified' : (data.error_message || 'Connection failed'),
                    latency: data.latency_ms,
                });
            }
        } catch (err: any) {
            setTestResult({ ok: false, message: err.response?.data?.message || 'Test failed' });
        } finally {
            setTesting(false);
        }
    };

    return (
        <div className="bg-background-dark text-white min-h-screen">
            <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden max-w-[430px] mx-auto bg-background-dark border-x border-white/5 pb-32">
                <div className="flex items-center p-4 pb-2 justify-between sticky top-0 z-30 bg-background-dark/80 backdrop-blur-xl border-b border-white/5">
                    <button onClick={() => navigate(-1)} className="flex items-center justify-center w-10 h-10 rounded-full active:bg-white/10 transition-colors">
                        <span className="material-symbols-outlined text-2xl">arrow_back_ios_new</span>
                    </button>
                    <h2 className="text-lg font-bold leading-tight tracking-tight flex-1 text-center">AI Configuration</h2>
                    <div className="w-10"></div>
                </div>

                {loading && (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
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
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">API Settings</h3>
                            <div className="p-4 rounded-2xl bg-[#192d33] border border-white/5 space-y-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-slate-400 block px-1">API Endpoint URL</label>
                                    <input
                                        className="w-full bg-[#111e22] border-white/10 rounded-xl px-4 py-3 text-sm focus:ring-primary focus:border-primary placeholder:text-slate-600 outline-none"
                                        placeholder="https://api.openai.com/v1"
                                        type="text"
                                        value={baseUrl}
                                        onChange={e => setBaseUrl(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-slate-400 block px-1">API Key</label>
                                    <div className="relative">
                                        <input
                                            className="w-full bg-[#111e22] border-white/10 rounded-xl px-4 py-3 text-sm focus:ring-primary focus:border-primary placeholder:text-slate-600 outline-none"
                                            placeholder={config?.api_key_set ? 'Key is set (enter new to update)' : 'Enter your API key'}
                                            type={showApiKey ? 'text' : 'password'}
                                            value={apiKey}
                                            onChange={e => setApiKey(e.target.value)}
                                        />
                                        <button
                                            onClick={() => setShowApiKey(!showApiKey)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-xl cursor-pointer"
                                        >
                                            <span className="material-symbols-outlined">{showApiKey ? 'visibility_off' : 'visibility'}</span>
                                        </button>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between p-1">
                                    {testResult && (
                                        <div className="flex items-center gap-2">
                                            <span className={`material-symbols-outlined text-sm ${testResult.ok ? 'text-green-500' : 'text-red-500'}`}>
                                                {testResult.ok ? 'check_circle' : 'error'}
                                            </span>
                                            <span className="text-xs text-slate-300">
                                                {testResult.message}
                                                {testResult.latency !== undefined && ` (${testResult.latency}ms)`}
                                            </span>
                                        </div>
                                    )}
                                    {!testResult && <div />}
                                    <button
                                        onClick={handleTest}
                                        disabled={testing}
                                        className="text-xs font-bold text-primary px-3 py-1 bg-primary/10 rounded-full active:scale-95 transition-all disabled:opacity-50"
                                    >
                                        {testing ? 'Testing...' : 'Test Connection'}
                                    </button>
                                </div>
                            </div>
                        </section>

                        <section className="space-y-4">
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">Model Selection</h3>
                            <div className="p-4 rounded-2xl bg-[#192d33] border border-white/5 space-y-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-slate-400 block px-1">Model Name</label>
                                    <div className="relative">
                                        <input
                                            className="w-full bg-[#111e22] border-white/10 rounded-xl px-4 py-3 text-sm focus:ring-primary focus:border-primary placeholder:text-slate-600 outline-none"
                                            placeholder="e.g. gpt-4o"
                                            type="text"
                                            value={model}
                                            onChange={e => setModel(e.target.value)}
                                            list="model-list"
                                        />
                                        <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">expand_more</span>
                                    </div>
                                    {models.length > 0 && (
                                        <datalist id="model-list">
                                            {models.map(m => <option key={m} value={m} />)}
                                        </datalist>
                                    )}
                                </div>
                            </div>
                        </section>
                    </div>
                )}

                <div className="fixed bottom-0 left-0 right-0 max-w-[430px] mx-auto p-4 bg-background-dark/80 backdrop-blur-xl border-t border-white/5 z-40 pb-10">
                    <button
                        onClick={handleSave}
                        disabled={saving || loading}
                        className="w-full h-14 bg-primary text-background-dark font-bold rounded-2xl flex items-center justify-center shadow-lg active:scale-[0.98] transition-all disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Configuration'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AIConfig;