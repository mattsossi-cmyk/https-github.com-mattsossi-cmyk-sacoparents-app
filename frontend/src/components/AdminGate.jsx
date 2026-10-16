import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";

import AppShell from "./AppShell";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

export function AdminForbidden({ tp }) {
  return (
    <AppShell>
      <div className="card-soft p-8 text-center max-w-lg mx-auto" data-testid={`${tp}-forbidden`}>
        <ShieldCheck size={20} className="mx-auto text-[#B6663B] mb-3" />
        <h2 className="font-serif text-2xl text-[#1A1330]">Admin only</h2>
        <p className="text-sm text-[#4B4567] mt-2">This page is restricted to the SA CoParents app owner.</p>
      </div>
    </AppShell>
  );
}

// Loads an admin-only endpoint; the server decides who is an admin (403 otherwise).
export function useAdminGet(path) {
  const { user } = useAuth();
  const [state, setState] = useState({ data: null, err: "" });
  const reload = () =>
    api.get(path).then((r) => setState({ data: r.data, err: "" }))
      .catch((e) => setState({ data: null, err: e?.response?.status === 403 ? "forbidden" : "error" }));
  useEffect(() => {
    if (user) reload();
  }, [user, path]); // eslint-disable-line react-hooks/exhaustive-deps
  return { ...state, reload };
}

export function AdminGate({ tp, err, children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (err === "forbidden") return <AdminForbidden tp={tp} />;
  return children;
}
