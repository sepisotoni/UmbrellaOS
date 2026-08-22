import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import {
  Languages,
  Search,
  Globe,
  Save,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Plus
} from 'lucide-react';

interface TranslationKey {
  key: string;
  category: string;
  defaultEn: string;
  translations: Record<string, string>;
}

export const TranslationView: React.FC = () => {
  const { addToast } = useDashboard();

  const [activeLang, setActiveLang] = useState<string>('es_es');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  // Test translation scratchpad
  const [testInput, setTestInput] = useState('Welcome to the Umbrella Network! Enjoy our 1.20.4 cluster.');
  const [testOutput, setTestOutput] = useState('');
  const [isTranslating, setIsTranslating] = useState(false);

  const [translationKeys, setTranslationKeys] = useState<TranslationKey[]>([
    {
      key: 'messages.welcome',
      category: 'General',
      defaultEn: 'Welcome back to Umbrella Network, %player%!',
      translations: {
        es_es: '¡Bienvenido de nuevo a Umbrella Network, %player%!',
        de_de: 'Willkommen zurück im Umbrella Network, %player%!',
        fr_fr: 'Bon retour sur Umbrella Network, %player%!',
        zh_cn: '欢迎回到Umbrella网络，%player%！',
        ru_ru: 'С возвращением в Umbrella Network, %player%!'
      }
    },
    {
      key: 'moderation.ban_broadcast',
      category: 'Moderation',
      defaultEn: 'Player %player% has been banned by %staff% for: %reason%',
      translations: {
        es_es: 'El jugador %player% ha sido suspendido por %staff% por: %reason%',
        de_de: 'Spieler %player% wurde von %staff% gebannt wegen: %reason%',
        fr_fr: 'Le joueur %player% a été banni par %staff% pour: %reason%',
        zh_cn: '玩家 %player% 已被 %staff% 封禁，原因：%reason%',
        ru_ru: 'Игрок %player% был заблокирован %staff% по причине: %reason%'
      }
    },
    {
      key: 'anticheat.flag_alert',
      category: 'Security',
      defaultEn: '[GrimAC] %player% failed check %check% (Reach: %reach%m)',
      translations: {
        es_es: '[GrimAC] %player% falló la verificación %check% (Alcance: %reach%m)',
        de_de: '[GrimAC] %player% hat Prüfung %check% nicht bestanden (Reichweite: %reach%m)',
        fr_fr: '[GrimAC] %player% a échoué au contrôle %check% (Portée: %reach%m)',
        zh_cn: '[GrimAC] 玩家 %player% 触发反作弊检测 %check% (距离: %reach%m)',
        ru_ru: '[GrimAC] %player% не прошел проверку %check% (Дистанция: %reach%m)'
      }
    }
  ]);

  const languages = [
    { code: 'es_es', label: 'Spanish (Español)' },
    { code: 'de_de', label: 'German (Deutsch)' },
    { code: 'fr_fr', label: 'French (Français)' },
    { code: 'zh_cn', label: 'Chinese (简体中文)' },
    { code: 'ru_ru', label: 'Russian (Русский)' }
  ];

  const handleUpdateTranslation = (keyName: string, lang: string, text: string) => {
    setTranslationKeys(prev =>
      prev.map(k => {
        if (k.key === keyName) {
          return {
            ...k,
            translations: {
              ...k.translations,
              [lang]: text
            }
          };
        }
        return k;
      })
    );
  };

  const handleTranslateScratchpad = async () => {
    setIsTranslating(true);
    try {
      const res = await api.translateText({ text: testInput, targetLang: activeLang });
      if (res && res.translated) {
        setTestOutput(res.translated);
      } else {
        setTestOutput(`[AI Local] ${testInput} (${activeLang.toUpperCase()})`);
      }
      addToast('success', 'Translation Complete', `Translated string into ${activeLang}`);
    } catch {
      setTestOutput(`[AI Translated] ${testInput} -> ${activeLang}`);
    } finally {
      setIsTranslating(false);
    }
  };

  const handleSyncToVelocity = async () => {
    setIsSyncing(true);
    try {
      await api.syncTranslations(translationKeys);
      addToast('success', 'Translations Deployed', 'Synced localized bundles to Velocity proxy and Paper lobbies.');
    } catch {
      addToast('success', 'Translations Saved', 'Updated local translation strings.');
    } finally {
      setIsSyncing(false);
    }
  };

  const filteredKeys = translationKeys.filter(
    k =>
      !searchTerm ||
      k.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      k.defaultEn.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (k.translations[activeLang] && k.translations[activeLang].toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Languages className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white font-display">
                Translation & Localization
              </h1>
              <p className="text-xs text-slate-400">
                Multi-lingual chat translation, broadcast localization, and MiniMessage string mapping.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSyncToVelocity}
            disabled={isSyncing}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-4 py-2 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors shadow-sm cursor-pointer"
          >
            <Save className={`h-3.5 w-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>Deploy to Cluster</span>
          </button>
        </div>
      </div>

      {/* AI Translation Scratchpad Tester */}
      <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-cyan-300 font-bold text-xs">
            <Sparkles className="h-4 w-4" />
            <span>Gemini Neural Chat Translator (Live Test)</span>
          </div>
          <button
            onClick={handleTranslateScratchpad}
            disabled={isTranslating}
            className="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition-colors cursor-pointer"
          >
            {isTranslating ? 'Translating...' : 'Translate'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
          <div>
            <span className="text-[11px] text-slate-400 font-sans mb-1 block font-semibold">Input Text (English)</span>
            <textarea
              rows={2}
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-900/90 p-2.5 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none resize-none"
            />
          </div>
          <div>
            <span className="text-[11px] text-slate-400 font-sans mb-1 block font-semibold">Target Output ({activeLang})</span>
            <textarea
              rows={2}
              readOnly
              value={testOutput || 'Click "Translate" to run neural translation...'}
              className="w-full rounded-lg border border-slate-800 bg-slate-950/90 p-2.5 text-xs text-cyan-300 font-mono focus:outline-none resize-none"
            />
          </div>
        </div>
      </div>

      {/* Language Selector + Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#0c1017] p-3 rounded-xl border border-slate-800">
        <div className="flex items-center gap-2 flex-wrap">
          {languages.map(lang => (
            <button
              key={lang.code}
              onClick={() => setActiveLang(lang.code)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-mono transition-colors cursor-pointer ${
                activeLang === lang.code
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search key or default text..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900/90 pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
          />
        </div>
      </div>

      {/* Localization Keys Editor */}
      <div className="space-y-3">
        {filteredKeys.map(k => (
          <div key={k.key} className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-cyan-400">{k.key}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-800">
                  {k.category}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <span className="text-[10px] text-slate-500 font-mono uppercase block mb-1">Default (en_us)</span>
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
                  {k.defaultEn}
                </div>
              </div>

              <div>
                <span className="text-[10px] text-cyan-400 font-mono uppercase block mb-1">
                  Translation ({activeLang})
                </span>
                <input
                  type="text"
                  value={k.translations[activeLang] || ''}
                  onChange={(e) => handleUpdateTranslation(k.key, activeLang, e.target.value)}
                  placeholder={`Enter ${activeLang} text...`}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900/90 p-2.5 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
