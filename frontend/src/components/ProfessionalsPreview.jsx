import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ProfessionalCard } from "@/pages/Professionals";

export const ProfessionalsPreview = ({ userId }) => {
  const [pros, setPros] = useState(null);
  useEffect(() => { api.get("/professionals/directory").then((r) => setPros(r.data)).catch(() => setPros([])); }, []);
  if (!pros) return null;
  const others = pros.filter((p) => p.id !== userId).slice(0, 4);
  return (
    <section data-testid="professionals-section">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <h2 className="text-2xl font-semibold">Available Professionals</h2>
          <p className="text-sm text-muted-foreground">{pros.length} approved colleague{pros.length === 1 ? "" : "s"} in the SA CoParents Align directory.</p>
        </div>
        <Link to="/professionals" data-testid="professionals-view-all-link"><Button variant="outline" size="sm" className="gap-1.5" data-testid="professionals-view-all-btn">Full directory <ArrowRight className="h-4 w-4" /></Button></Link>
      </div>
      {others.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="professionals-preview-empty">No other approved professionals yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="professionals-preview-grid">
          {others.map((p) => <ProfessionalCard key={p.id} p={p} compact />)}
        </div>
      )}
    </section>
  );
};
