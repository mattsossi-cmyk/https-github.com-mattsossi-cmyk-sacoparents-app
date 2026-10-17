import React, { useCallback, useEffect, useState } from "react";
import { Navigate, Link } from "react-router-dom";
import { toast } from "sonner";
import {
  Search,
  ShieldCheck,
  ShieldOff,
  KeyRound,
  ArrowLeft,
  Loader2,
  Filter,
  RefreshCw,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

const PAGE_SIZE = 25;

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function Badge({ children, tone = "muted", testid }) {
  const tones = {
    muted: "bg-[#F0EDF7] text-[#4B4567]",
    teal: "bg-[#D5F2F2] text-[#0E7A7A]",
    purple: "bg-[#EFE9F9] text-[#3D1A78]",
    red: "bg-[#FCE3DC] text-[#9A3A23]",
    amber: "bg-[#FFF1E2] text-[#965231]",
  };
  return (
    <span
      data-testid={testid}
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] uppercase tracking-[0.12em] font-medium ${tones[tone] || tones.muted}`}
    >
      {children}
    </span>
  );
}

export default function AdminUsers() {
  const { user, loading } = useAuth();

  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("active"); // active | suspended | all
  const [includeGuests, setIncludeGuests] = useState(false);
  const [offset, setOffset] = useState(0);

  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [fetching, setFetching] = useState(true);
  const [err, setErr] = useState(null);
  const [busyUserId, setBusyUserId] = useState(null);
  const [confirm, setConfirm] = useState(null); // { user, action }

  const fetchUsers = useCallback(async () => {
    setFetching(true);
    setErr(null);
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      if (filter === "suspended") params.set("suspended", "true");
      else if (filter === "active") params.set("suspended", "false");
      if (includeGuests) params.set("include_guests", "true");
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(offset));
      const { data } = await api.get(`/analytics/admin/users?${params.toString()}`);
      setUsers(data.users || []);
      setTotal(data.total || 0);
    } catch (e) {
      logError("admin users list failed", e);
      if (e?.response?.status === 403) setErr("forbidden");
      else setErr("Could not load users.");
    } finally {
      setFetching(false);
    }
  }, [q, filter, includeGuests, offset]);

  useEffect(() => {
    if (!user) return;
    fetchUsers();
  }, [user, fetchUsers]);

  // Reset offset when filters/search change
  useEffect(() => {
    setOffset(0);
  }, [q, filter, includeGuests]);

  const updateRow = (id, patch) => {
    setUsers((prev) => prev.map((u) => (u.user_id === id ? { ...u, ...patch } : u)));
  };

  const doSuspend = async (u) => {
    setBusyUserId(u.user_id);
    try {
      await api.post(`/analytics/admin/users/${u.user_id}/suspend`, {
        reason: confirm?.reason || null,
      });
      updateRow(u.user_id, { suspended: true });
      toast.success(`Suspended ${u.email}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not suspend user.");
    } finally {
      setBusyUserId(null);
      setConfirm(null);
    }
  };

  const doUnsuspend = async (u) => {
    setBusyUserId(u.user_id);
    try {
      await api.post(`/analytics/admin/users/${u.user_id}/unsuspend`);
      updateRow(u.user_id, { suspended: false });
      toast.success(`Restored ${u.email}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not restore user.");
    } finally {
      setBusyUserId(null);
    }
  };

  const doSendResetLink = async (u) => {
    setBusyUserId(u.user_id);
    try {
      const { data } = await api.post(`/analytics/admin/users/${u.user_id}/send-reset-link`, {
        expires_minutes: 60,
      });
      if (data.emailed) {
        toast.success(`Reset link emailed to ${u.email}`);
      } else if (data.link) {
        try {
          await navigator.clipboard.writeText(window.location.origin + data.link);
          toast.success("Email unavailable — link copied to clipboard", {
            description: data.reason || "",
          });
        } catch {
          toast.message("Email unavailable — copy this link", {
            description: window.location.origin + data.link,
            duration: 15000,
          });
        }
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not send reset link.");
    } finally {
      setBusyUserId(null);
    }
  };

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;

  if (err === "forbidden") {
    return (
      <AppShell>
        <div
          className="card-soft p-8 text-center max-w-lg mx-auto"
          data-testid="admin-users-forbidden"
        >
          <div className="w-12 h-12 mx-auto rounded-full bg-[#FFF1E2] grid place-items-center text-[#965231] mb-3">
            <ShieldCheck size={20} />
          </div>
          <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
          <p className="text-sm text-[#4B4567] mt-2">
            This page is restricted to the SA CoParents app owner.
          </p>
        </div>
      </AppShell>
    );
  }

  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + users.length, total);

  return (
    <AppShell>
      <div className="fade-up space-y-6" data-testid="admin-users-page">
        {/* Header */}
        <div className="card-soft p-6 relative overflow-hidden">
          <div className="absolute -top-16 -right-16 w-48 h-48 rounded-full bg-[#D4C5F0]/40" />
          <div className="relative flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
            <div>
              <Link
                to="/admin"
                className="inline-flex items-center gap-1 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-1"
                data-testid="admin-users-back-link"
              >
                <ArrowLeft size={12} /> Back to admin
              </Link>
              <div className="eyebrow mb-1">Admin</div>
              <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330]">User management</h1>
              <p className="text-sm text-[#4B4567] mt-1.5">
                Search, suspend, restore, and email password-reset links to any registered user.
              </p>
            </div>
            <button
              onClick={() => fetchUsers()}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-[#E5E0EE] text-sm text-[#4B4567] hover:bg-[#F7F4FC]"
              data-testid="admin-users-refresh-btn"
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="card-soft p-4 sm:p-5">
          <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
            <div className="relative flex-1">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6E6787] pointer-events-none"
              />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search by name or email…"
                className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-[#E5E0EE] bg-white text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
                data-testid="admin-users-search-input"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter size={14} className="text-[#6E6787]" />
              <div className="inline-flex rounded-lg border border-[#E5E0EE] overflow-hidden" data-testid="admin-users-filter-group">
                {["active", "suspended", "all"].map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setFilter(opt)}
                    className={`px-3 py-2 text-xs capitalize ${
                      filter === opt
                        ? "bg-[#3D1A78] text-white"
                        : "bg-white text-[#4B4567] hover:bg-[#F7F4FC]"
                    }`}
                    data-testid={`admin-users-filter-${opt}`}
                  >
                    {opt}
                  </button>
                ))}
              </div>

              <label
                className="flex items-center gap-2 text-sm text-[#4B4567] pl-2 cursor-pointer select-none"
                data-testid="admin-users-include-guests-toggle"
              >
                <input
                  type="checkbox"
                  checked={includeGuests}
                  onChange={(e) => setIncludeGuests(e.target.checked)}
                  className="rounded border-[#E5E0EE]"
                />
                <span>Include guests</span>
              </label>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="card-soft p-0 overflow-hidden">
          {fetching ? (
            <div className="p-10 text-center text-sm tracking-[0.2em] uppercase text-[#6E6787]">
              <Loader2 size={16} className="inline animate-spin mr-2" /> Loading users…
            </div>
          ) : err ? (
            <div className="p-10 text-center text-sm text-[#9A3A23]">{err}</div>
          ) : users.length === 0 ? (
            <div className="p-10 text-center text-sm text-[#6E6787]" data-testid="admin-users-empty">
              No users match the current filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="admin-users-table">
                <thead className="bg-[#F7F4FC]">
                  <tr className="text-[10px] uppercase tracking-[0.15em] text-[#6E6787]">
                    <th className="text-left py-2.5 px-4">Name</th>
                    <th className="text-left py-2.5 px-4">Email</th>
                    <th className="text-left py-2.5 px-4">Auth</th>
                    <th className="text-left py-2.5 px-4">Type</th>
                    <th className="text-left py-2.5 px-4">Joined</th>
                    <th className="text-left py-2.5 px-4">Status</th>
                    <th className="text-right py-2.5 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const busy = busyUserId === u.user_id;
                    return (
                      <tr
                        key={u.user_id}
                        className="border-t border-[#E5E0EE] hover:bg-[#FBF9FE]"
                        data-testid={`admin-user-row-${u.user_id}`}
                      >
                        <td className="py-3 px-4 text-[#1A1330] truncate max-w-[180px]">
                          {u.name || "—"}
                        </td>
                        <td className="py-3 px-4 text-[#4B4567] truncate max-w-[240px]">
                          {u.email}
                        </td>
                        <td className="py-3 px-4 text-[#4B4567] capitalize">
                          {u.auth_method || "jwt"}
                        </td>
                        <td className="py-3 px-4">
                          {u.is_guest ? (
                            <Badge tone="teal">Guest</Badge>
                          ) : (
                            <Badge tone="purple">Account</Badge>
                          )}
                        </td>
                        <td className="py-3 px-4 text-[#4B4567]">{fmtDate(u.created_at)}</td>
                        <td className="py-3 px-4">
                          {u.suspended ? (
                            <Badge tone="red" testid={`admin-user-status-${u.user_id}`}>
                              Suspended
                            </Badge>
                          ) : (
                            <Badge tone="muted" testid={`admin-user-status-${u.user_id}`}>
                              Active
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2 justify-end">
                            <button
                              disabled={busy || u.is_guest}
                              onClick={() => doSendResetLink(u)}
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[#E5E0EE] text-xs text-[#3D1A78] hover:bg-[#EFE9F9] disabled:opacity-40 disabled:cursor-not-allowed"
                              title={
                                u.is_guest
                                  ? "Guests don't have a password to reset."
                                  : "Email a magic-link the user can use to sign in or reset their password."
                              }
                              data-testid={`admin-user-reset-btn-${u.user_id}`}
                            >
                              <KeyRound size={12} /> Reset link
                            </button>
                            {u.suspended ? (
                              <button
                                disabled={busy}
                                onClick={() => doUnsuspend(u)}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[#0E7A7A]/30 text-xs text-[#0E7A7A] hover:bg-[#D5F2F2] disabled:opacity-40"
                                data-testid={`admin-user-unsuspend-btn-${u.user_id}`}
                              >
                                <ShieldCheck size={12} /> Restore
                              </button>
                            ) : (
                              <button
                                disabled={busy || u.email?.toLowerCase() === user.email?.toLowerCase()}
                                onClick={() => setConfirm({ user: u, action: "suspend", reason: "" })}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[#9A3A23]/30 text-xs text-[#9A3A23] hover:bg-[#FCE3DC] disabled:opacity-40 disabled:cursor-not-allowed"
                                title={
                                  u.email?.toLowerCase() === user.email?.toLowerCase()
                                    ? "You can't suspend your own account."
                                    : "Suspend this account."
                                }
                                data-testid={`admin-user-suspend-btn-${u.user_id}`}
                              >
                                <ShieldOff size={12} /> Suspend
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination footer */}
          {!fetching && total > 0 && (
            <div
              className="flex items-center justify-between text-xs text-[#4B4567] px-4 py-3 border-t border-[#E5E0EE] bg-white"
              data-testid="admin-users-pagination"
            >
              <span>
                Showing <span className="text-[#1A1330] font-medium">{pageStart}</span>–
                <span className="text-[#1A1330] font-medium">{pageEnd}</span> of {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  className="px-3 py-1.5 rounded-lg border border-[#E5E0EE] hover:bg-[#F7F4FC] disabled:opacity-40 disabled:cursor-not-allowed"
                  data-testid="admin-users-prev-btn"
                >
                  Previous
                </button>
                <button
                  disabled={pageEnd >= total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  className="px-3 py-1.5 rounded-lg border border-[#E5E0EE] hover:bg-[#F7F4FC] disabled:opacity-40 disabled:cursor-not-allowed"
                  data-testid="admin-users-next-btn"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Suspend confirmation modal */}
      {confirm?.action === "suspend" && (
        <div
          className="fixed inset-0 z-50 bg-[#1A1330]/50 backdrop-blur-sm grid place-items-center p-4"
          data-testid="admin-users-suspend-modal"
        >
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <h3 className="font-serif text-xl text-[#1A1330]">
              Suspend {confirm.user.email}?
            </h3>
            <p className="text-sm text-[#4B4567] mt-2">
              They'll be signed out immediately and won't be able to log in until you restore them.
            </p>
            <label className="block text-xs text-[#4B4567] uppercase tracking-[0.15em] mt-4 mb-1">
              Reason (optional, internal note)
            </label>
            <textarea
              value={confirm.reason || ""}
              onChange={(e) => setConfirm({ ...confirm, reason: e.target.value })}
              rows={3}
              placeholder="e.g. Abuse report received 2026-02-12"
              className="w-full px-3 py-2 rounded-lg border border-[#E5E0EE] text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              data-testid="admin-users-suspend-reason-input"
            />
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setConfirm(null)}
                className="px-4 py-2 rounded-lg border border-[#E5E0EE] text-sm text-[#4B4567] hover:bg-[#F7F4FC]"
                data-testid="admin-users-suspend-cancel-btn"
              >
                Cancel
              </button>
              <button
                onClick={() => doSuspend(confirm.user)}
                disabled={busyUserId === confirm.user.user_id}
                className="px-4 py-2 rounded-lg bg-[#9A3A23] text-white text-sm hover:bg-[#7E2E1B] disabled:opacity-60 inline-flex items-center gap-1.5"
                data-testid="admin-users-suspend-confirm-btn"
              >
                {busyUserId === confirm.user.user_id ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <ShieldOff size={14} />
                )}
                Suspend
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
