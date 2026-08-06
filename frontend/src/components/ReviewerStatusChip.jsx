/**
 * ReviewerStatusChip — Compact "review pending / reviewed by N experts"
 * pill for surfaces (like the Safety Screen intro) where users should
 * see the current review status at a glance without needing to visit
 * the full Methodology page.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Clock } from "lucide-react";
import { api } from "../lib/api";

export default function ReviewerStatusChip() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api
      .get("/reviewer-panel")
      .then((r) => setData(r.data))
      .catch(() => setData({ status: "pending", count: 0 }));
  }, []);

  if (!data) return null;
  const isReviewed = data.status === "reviewed";
  return (
    <Link
      to="/methodology#reviewer-panel-title"
      data-testid="reviewer-status-chip"
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold transition hover:opacity-90 ${
        isReviewed
          ? "bg-[#E6F4EC] text-[#1F5C3B] ring-1 ring-[#1F5C3B]/25"
          : "bg-[#F0EAFB] text-[#3D1A78] ring-1 ring-[#3D1A78]/25"
      }`}
    >
      {isReviewed ? <ShieldCheck size={11} /> : <Clock size={11} />}
      {isReviewed
        ? `Reviewed by ${data.count} independent expert${data.count === 1 ? "" : "s"}`
        : "Independent expert review pending"}
    </Link>
  );
}
