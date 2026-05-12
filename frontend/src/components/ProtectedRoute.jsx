import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[#5C6B64]">
        <div className="animate-pulse text-sm tracking-[0.2em] uppercase">Loading</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
