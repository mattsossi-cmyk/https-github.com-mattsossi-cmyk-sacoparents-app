import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, AlertTriangle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { logError } from "@/lib/logger";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

const SUPPORT_EMAIL = "mattsossi@bsossi.com";

export default function DeleteAccount() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleDelete = async () => {
    if (confirmText.trim().toUpperCase() !== "DELETE") {
      toast.error("Please type DELETE to confirm");
      return;
    }
    setSubmitting(true);
    try {
      await api.delete("/auth/account");
      try {
        await logout();
      } catch (_err) {
        // ignore — account is already gone
      }
      toast.success("Your account and all data have been permanently deleted.");
      setConfirmOpen(false);
      // small delay so the toast is visible before redirect
      setTimeout(() => navigate("/", { replace: true }), 1200);
    } catch (err) {
      logError("Account deletion failed:", err);
      toast.error("We couldn't delete your account. Please email us.");
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg" data-testid="delete-account-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#5C7A6A] hover:text-[#849D8E] mb-6"
          data-testid="delete-account-back-link"
        >
          <ArrowLeft size={14} /> Back to SA Coparents
        </Link>

        <div className="eyebrow mb-3">Account &amp; Data Deletion</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#2A3631] mb-3 leading-tight">
          Delete your account.
        </h1>
        <p className="text-[15px] text-[#5C6B64] leading-relaxed mb-8 max-w-2xl">
          You can permanently delete your SA Coparents account and every piece
          of data we hold for you at any time. There is no waiting period and
          nothing is recoverable afterwards.
        </p>

        <section className="bg-white border border-[#E8ECE9] rounded-2xl p-6 sm:p-7 mb-8">
          <h2 className="font-serif text-xl text-[#2A3631] mb-3">
            What gets deleted
          </h2>
          <ul className="text-[14px] text-[#5C6B64] space-y-2 list-disc pl-5">
            <li>Your account profile (name, email, password, picture)</li>
            <li>All five preparation modules (Child-Centered Goals, Issues &amp; Concerns, Priority Ranking, Communication Style, Readiness Check)</li>
            <li>Every AI-generated Mediation Summary, Agreement Draft and Improvement Plan</li>
            <li>Every email-to-mediator record you've created</li>
            <li>All active sessions and any registered push-notification device tokens</li>
          </ul>
          <p className="text-[13px] text-[#8A9A92] mt-4 italic">
            PDFs you previously shared via the &ldquo;Share via text&rdquo; 7-day
            link cannot be recalled once shared, but the link itself is
            invalidated within minutes of deletion.
          </p>
        </section>

        {loading ? (
          <div className="text-sm text-[#8A9A92]">Loading…</div>
        ) : user ? (
          <SignedInDeleteCard
            email={user.email}
            onConfirm={() => setConfirmOpen(true)}
          />
        ) : (
          <SignedOutDeleteCard />
        )}

        <p className="text-xs text-[#8A9A92] italic mt-10">
          SA Coparents &middot; 16607 Blanco #703, San Antonio, Texas 78232
          <br />
          This page is provided to satisfy Google Play and Apple App Store
          account-deletion requirements.
        </p>
      </div>

      <Dialog open={confirmOpen} onOpenChange={(v) => !submitting && setConfirmOpen(v)}>
        <DialogContent className="sm:max-w-md" data-testid="delete-account-confirm-dialog">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl text-[#2A3631] flex items-center gap-2">
              <AlertTriangle size={20} className="text-[#C97B63]" />
              Permanently delete?
            </DialogTitle>
            <DialogDescription className="text-[14px] text-[#5C6B64] pt-2">
              This action is immediate and irreversible. Type <strong>DELETE</strong> below to confirm.
            </DialogDescription>
          </DialogHeader>

          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Type DELETE to confirm"
            className="w-full border border-[#E8ECE9] rounded-xl px-4 py-3 text-[15px] focus:outline-none focus:ring-2 focus:ring-[#C97B63]"
            data-testid="delete-account-confirm-input"
            disabled={submitting}
            autoFocus
          />

          <DialogFooter className="flex gap-3 mt-4">
            <Button
              variant="outline"
              onClick={() => setConfirmOpen(false)}
              disabled={submitting}
              className="rounded-full px-5"
              data-testid="delete-account-cancel-button"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDelete}
              disabled={submitting || confirmText.trim().toUpperCase() !== "DELETE"}
              className="rounded-full px-5 bg-[#C97B63] hover:bg-[#B56B53] text-white"
              data-testid="delete-account-confirm-button"
            >
              {submitting ? (
                <>
                  <Loader2 size={14} className="animate-spin mr-2" />
                  Deleting…
                </>
              ) : (
                "Delete my account"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SignedInDeleteCard({ email, onConfirm }) {
  return (
    <section
      className="bg-white border border-[#E8ECE9] rounded-2xl p-6 sm:p-7"
      data-testid="delete-account-signed-in-card"
    >
      <h2 className="font-serif text-xl text-[#2A3631] mb-2">
        You're signed in as <span className="font-semibold">{email}</span>
      </h2>
      <p className="text-[14px] text-[#5C6B64] leading-relaxed mb-5">
        One tap and everything tied to this account is wiped from our servers.
        You'll be signed out and returned to the home page.
      </p>
      <Button
        onClick={onConfirm}
        className="rounded-full px-6 py-5 bg-[#C97B63] hover:bg-[#B56B53] text-white text-[14px]"
        data-testid="delete-account-trigger-button"
      >
        Delete my account permanently
      </Button>
    </section>
  );
}

function SignedOutDeleteCard() {
  return (
    <section
      className="bg-white border border-[#E8ECE9] rounded-2xl p-6 sm:p-7"
      data-testid="delete-account-signed-out-card"
    >
      <h2 className="font-serif text-xl text-[#2A3631] mb-2">
        You're not signed in
      </h2>
      <p className="text-[14px] text-[#5C6B64] leading-relaxed mb-5">
        Choose one of the options below to delete your account.
      </p>

      <div className="space-y-4">
        <div className="border border-[#E8ECE9] rounded-xl p-5">
          <div className="text-[13px] uppercase tracking-wider text-[#8A9A92] mb-2">
            Option 1 &mdash; Fastest
          </div>
          <p className="text-[14px] text-[#2A3631] mb-3">
            Sign in, then the delete button will appear here.
          </p>
          <Link
            to="/login?next=/delete-account"
            className="inline-flex items-center justify-center rounded-full px-5 py-2.5 bg-[#5C7A6A] hover:bg-[#849D8E] text-white text-[14px]"
            data-testid="delete-account-signin-link"
          >
            Sign in to delete my account
          </Link>
        </div>

        <div className="border border-[#E8ECE9] rounded-xl p-5">
          <div className="text-[13px] uppercase tracking-wider text-[#8A9A92] mb-2">
            Option 2 &mdash; Email request
          </div>
          <p className="text-[14px] text-[#2A3631] mb-1">
            If you can't sign in, email us from the address on your account:
          </p>
          <a
            href={`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
              "Delete my SA Coparents account"
            )}&body=${encodeURIComponent(
              "Please delete my SA Coparents account and all associated data.\n\nAccount email: \n"
            )}`}
            className="text-[#5C7A6A] underline text-[14px]"
            data-testid="delete-account-email-link"
          >
            {SUPPORT_EMAIL}
          </a>
          <p className="text-[12px] text-[#8A9A92] mt-2">
            Manual requests are processed within 7 days. We'll reply once your
            data is gone.
          </p>
        </div>
      </div>
    </section>
  );
}
