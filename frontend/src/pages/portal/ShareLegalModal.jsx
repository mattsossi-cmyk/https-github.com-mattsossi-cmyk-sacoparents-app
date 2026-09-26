import React, { useState } from "react";

/**
 * ShareLegalModal — mint a share link for the Legal Report PDF with
 * an optional passphrase and a TTL toggle (7 days / 30 days). Legal
 * reports carry signatures, so we let parents lock the link behind a
 * passphrase they share with the recipient separately.
 */
export function ShareLegalModal({ open, onClose, onMint, loading, lastUrl }) {
  const [passphrase, setPassphrase] = useState("");
  const [ttlDays, setTtlDays] = useState(30);

  if (!open) return null;

  const handleMint = () => {
    onMint({
      passphrase: passphrase.trim() || null,
      ttl_days: ttlDays,
    });
  };

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 no-print"
      data-testid="modal-share-legal"
    >
      <div className="bg-white w-full max-w-sm rounded-2xl shadow-xl space-y-3 p-5">
        <div className="flex justify-between items-center border-b border-slate-100 pb-2">
          <h3 className="font-bold text-slate-800 text-sm">
            Share Legal Report Link
          </h3>
          <button
            data-testid="close-share-legal-modal"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600"
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        <p className="text-[11px] text-slate-500">
          Legal Reports carry signatures. A passphrase locks the link so only
          the person you text or email the passphrase to can open it.
        </p>

        <div className="space-y-2 text-xs">
          <div>
            <label className="font-semibold text-slate-700 block mb-1">
              Optional passphrase
            </label>
            <input
              data-testid="share-legal-passphrase"
              type="text"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              className="w-full p-2 border border-slate-300 rounded-lg font-mono tracking-wider"
              placeholder="Leave empty for no passphrase"
              maxLength={40}
            />
            <p className="text-[10px] text-slate-400 mt-1">
              Recipient will be asked to enter this before the PDF loads.
            </p>
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">
              Link duration
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                data-testid="share-legal-ttl-7"
                onClick={() => setTtlDays(7)}
                className={
                  ttlDays === 7
                    ? "flex-1 py-2 rounded-lg text-xs font-bold bg-purple-800 text-white"
                    : "flex-1 py-2 rounded-lg text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200"
                }
              >
                7 days (short)
              </button>
              <button
                type="button"
                data-testid="share-legal-ttl-30"
                onClick={() => setTtlDays(30)}
                className={
                  ttlDays === 30
                    ? "flex-1 py-2 rounded-lg text-xs font-bold bg-purple-800 text-white"
                    : "flex-1 py-2 rounded-lg text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200"
                }
              >
                30 days (default)
              </button>
            </div>
          </div>
        </div>

        {lastUrl && (
          <div
            data-testid="share-legal-result"
            className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-[10px] text-emerald-900 break-all"
          >
            <div className="font-bold mb-1">Link copied — share separately:</div>
            <div>{lastUrl}</div>
            {passphrase && (
              <div className="mt-1 pt-1 border-t border-emerald-200">
                <span className="font-bold">Passphrase (share separately):</span>{" "}
                <span className="font-mono">{passphrase}</span>
              </div>
            )}
          </div>
        )}

        <div className="pt-1 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 border border-slate-300 rounded-lg font-semibold text-slate-600 text-xs"
          >
            Cancel
          </button>
          <button
            type="button"
            data-testid="mint-share-legal-btn"
            onClick={handleMint}
            disabled={loading}
            className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-60 text-white rounded-lg font-semibold text-xs"
          >
            {loading ? "Creating…" : "Create link & copy"}
          </button>
        </div>
      </div>
    </div>
  );
}
