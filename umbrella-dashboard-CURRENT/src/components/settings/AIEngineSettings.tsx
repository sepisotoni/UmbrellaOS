/**
 * AIEngineSettings Subcomponent
 * Manages Gemini model selection, inference temperature, and AI diagnostic pipeline tests.
 */

import React from 'react';
import { Sparkles } from 'lucide-react';

interface AIEngineSettingsProps {
  aiModel: string;
  setAiModel: (model: string) => void;
  aiTemperature: number;
  setAiTemperature: (temp: number) => void;
  isTestingAI: boolean;
  onTestAI: () => void;
}

export const AIEngineSettings: React.FC<AIEngineSettingsProps> = ({
  aiModel,
  setAiModel,
  aiTemperature,
  setAiTemperature,
  isTestingAI,
  onTestAI,
}) => {
  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[#141d3d] pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <h2 className="font-bold text-white uppercase text-sm font-sans">
            AI Model & Heuristics Engine
          </h2>
        </div>

        <button
          type="button"
          onClick={onTestAI}
          disabled={isTestingAI}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-indigo-500/40 bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-300 text-xs font-bold transition cursor-pointer disabled:opacity-50"
        >
          <Sparkles className={`h-3 w-3 ${isTestingAI ? 'animate-spin' : ''}`} />
          <span>{isTestingAI ? 'Testing API...' : 'Test AI Connection'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-slate-300 mb-1 font-sans font-medium">Gemini Model Selector</label>
          <select
            value={aiModel}
            onChange={(e) => setAiModel(e.target.value)}
            className="w-full rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 text-white focus:border-indigo-500 focus:outline-none cursor-pointer"
          >
            <option value="gemini-1.5-pro">Gemini 1.5 Pro (Recommended for Complex Appeals)</option>
            <option value="gemini-1.5-flash">Gemini 1.5 Flash (Fast Heuristic Triage)</option>
            <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (Experimental)</option>
          </select>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="text-slate-300 font-sans font-medium">Inference Temperature</label>
            <span className="text-indigo-300 font-bold">{aiTemperature}</span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={aiTemperature}
            onChange={(e) => setAiTemperature(Number(e.target.value))}
            className="w-full mt-2 accent-indigo-500 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>Deterministic (0.0)</span>
            <span>Balanced (0.2)</span>
            <span>Creative (1.0)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
