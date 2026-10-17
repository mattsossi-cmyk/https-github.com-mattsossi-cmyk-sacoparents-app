import { Link } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const COPY = {
  never: "Complete the safety screening training acknowledgment before opening any parent's private check-in.",
  version: "The safety screening training has been updated. Please review what changed and re-acknowledge.",
  yearly: "It has been a year since you acknowledged the safety screening training. Please re-acknowledge to keep access to private check-in information.",
};

export const TrainingRefresherBanner = () => {
  const { user } = useAuth();
  const reason = user?.safety_training_due;
  if (!reason) return null;
  return (
    <div className="mb-6 flex flex-col gap-3 rounded-lg border-2 border-[#3D1A78]/30 bg-[#ece6f7] p-4 sm:flex-row sm:items-center sm:justify-between" data-testid="training-refresher-banner">
      <div className="flex items-start gap-3 text-sm">
        <GraduationCap className="mt-0.5 h-5 w-5 shrink-0 text-[#3D1A78]" />
        <div><p className="font-semibold text-[#3D1A78]">{reason === "never" ? "Training acknowledgment required" : "Training re-acknowledgment due"}</p><p className="text-slate-700">{COPY[reason]}</p></div>
      </div>
      <Link to="/professional-training" className="inline-flex h-9 shrink-0 items-center justify-center rounded-md bg-[#3D1A78] px-4 text-sm font-medium text-white hover:bg-[#2d1259]" data-testid="training-refresher-link">{reason === "never" ? "Start" : "Review and re-acknowledge"}</Link>
    </div>
  );
};
