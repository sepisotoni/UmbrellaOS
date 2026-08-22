import React, { useState, useRef } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import {
  Package,
  X,
  Upload,
  Server,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Zap,
  ShieldCheck,
  Cpu
} from 'lucide-react';

interface UploadPluginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UploadPluginModal: React.FC<UploadPluginModalProps> = ({ isOpen, onClose }) => {
  const { servers, uploadPluginJar, addToast } = useDashboard();
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetServerId, setTargetServerId] = useState<string>('ALL');
  const [autoReload, setAutoReload] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.jar') || file.name.endsWith('.zip')) {
        setSelectedFile(file);
      } else {
        addToast('warning', 'Invalid File Format', 'Please upload a compiled Minecraft .jar or .zip plugin bundle.');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.endsWith('.jar') || file.name.endsWith('.zip')) {
        setSelectedFile(file);
      } else {
        addToast('warning', 'Invalid File Format', 'Please upload a compiled Minecraft .jar or .zip plugin bundle.');
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      addToast('warning', 'File Required', 'Please drag & drop or select a .jar plugin file.');
      return;
    }

    setIsUploading(true);
    try {
      await uploadPluginJar(selectedFile, targetServerId, autoReload);
      onClose();
      setSelectedFile(null);
    } catch (err: any) {
      addToast('warning', 'Upload Error', err?.message || 'Failed to upload plugin payload.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-sans animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-[#0d1117] shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Package className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-display">Deploy Plugin .JAR File</h2>
              <p className="text-xs text-slate-400 font-sans">Upload Java bytecode plugins to Paper, Purpur, or Velocity nodes</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 font-sans text-xs">
          {/* Drag & Drop File Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
              isDragging
                ? 'border-cyan-400 bg-cyan-950/30 text-white scale-[1.01]'
                : selectedFile
                ? 'border-emerald-500/50 bg-emerald-950/20 text-slate-200'
                : 'border-slate-700 bg-slate-900/40 text-slate-400 hover:border-slate-600 hover:bg-slate-900/70'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".jar,.zip"
              onChange={handleFileSelect}
              className="hidden"
            />

            {selectedFile ? (
              <div className="flex flex-col items-center gap-2">
                <div className="h-10 w-10 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div className="font-mono font-bold text-white text-xs truncate max-w-sm">
                  {selectedFile.name}
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Java Archive
                </div>
                <span className="text-[10px] text-cyan-400 font-semibold underline mt-1">
                  Click to change file
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <div className="h-10 w-10 rounded-full bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center">
                  <Upload className="h-5 w-5" />
                </div>
                <div className="font-semibold text-white text-xs">
                  Drag and drop plugin <span className="text-cyan-400 font-mono">.jar</span> here, or click to browse
                </div>
                <div className="text-[11px] text-slate-500">
                  Compatible with Paper 1.20+, Purpur, Spigot, Folia, and Velocity Proxy
                </div>
              </div>
            )}
          </div>

          {/* Target Server Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Server className="h-3.5 w-3.5 text-cyan-400" />
              <span>Target Server Node</span>
            </label>
            <select
              value={targetServerId}
              onChange={(e) => setTargetServerId(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none font-mono cursor-pointer"
            >
              <option value="ALL">🌐 All Server Nodes (Global Rollout)</option>
              {servers.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.status.toUpperCase()} • {s.tps} TPS)
                </option>
              ))}
            </select>
          </div>

          {/* Hot Reload Toggle */}
          <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 space-y-2">
            <label className="flex items-center justify-between cursor-pointer select-none">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" />
                <span className="text-xs font-semibold text-white">Hot-Reload Bytecode</span>
              </div>
              <input
                type="checkbox"
                checked={autoReload}
                onChange={(e) => setAutoReload(e.target.checked)}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-cyan-500 cursor-pointer"
              />
            </label>
            <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
              If enabled, issues live <code className="font-mono text-cyan-300">/plugman reload</code> over the Bridge without restarting the entire server process.
            </p>
          </div>

          {/* Architecture Note */}
          <div className="p-3 rounded-lg bg-cyan-950/20 border border-cyan-500/20 text-[11px] text-slate-400 font-mono flex items-start gap-2">
            <ShieldCheck className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
            <span>
              <strong>Bytecode Sandbox:</strong> UmbrellaBridge verifies classloader integrity and validates package signatures prior to mounting.
            </span>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-xs font-semibold text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-md cursor-pointer disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Uploading & Staging...</span>
                </>
              ) : (
                <>
                  <Upload className="h-3.5 w-3.5" />
                  <span>Deploy Plugin .JAR</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
