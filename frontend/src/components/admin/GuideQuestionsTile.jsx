import { useEffect, useState } from 'react';
import { MessageCircleQuestion } from 'lucide-react';

import { api } from '../../lib/api';
import { logError } from '../../lib/logger';
import { READY } from '../../pages/selfJourneyGuide/guideAnswers';
import Sparkline from './Sparkline';

const LABEL = Object.fromEntries(READY.map((r) => [r.id, r.id === 'pages' ? 'What do the pages / steps cover?' : r.q]));

// Which ready-made Journey Guide questions parents tap most. Counts only, never who tapped.
export default function GuideQuestionsTile() {
  const [data, setData] = useState(null);
  useEffect(() => {
    api
      .get('/admin/guide-questions/stats')
      .then(({ data: d }) => setData(d))
      .catch((e) => logError('guide question stats load failed', e));
  }, []);
  const rows = data?.questions || [];
  const top = Math.max(1, ...rows.map((r) => r.all_time));

  return (
    <div className="card-soft p-6" data-testid="admin-guide-questions-tile">
      <div className="eyebrow flex items-center gap-2">
        <MessageCircleQuestion size={12} className="text-[#3D1A78]" />
        Journey Guide · Ready-made questions
      </div>
      <div className="font-serif text-xl text-[#1A1330] mt-1">Which questions do parents tap most?</div>
      <p className="text-xs text-[#6E6787] mt-1 mb-4">
        Counted on the open Self Journey and in the guided journey&apos;s help chat. Only the question and the day are
        counted, never who tapped it.
        {data && (
          <span data-testid="admin-guide-questions-totals">
            {' '}All time: {data.total_all_time} · Last 30 days: {data.total_last_30_days}
          </span>
        )}
      </p>
      {data && data.total_all_time === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#E5E0EE] bg-[#FAF8FD] p-6 text-center text-sm text-[#4B4567]" data-testid="admin-guide-questions-empty">
          No ready-made questions have been tapped yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs sm:text-sm" data-testid="admin-guide-questions-table">
            <thead>
              <tr className="text-[0.625rem] uppercase tracking-[0.15em] text-[#6E6787]">
                <th className="text-left pb-2 font-semibold">Question</th>
                <th className="text-left pb-2 pr-3 font-semibold">Last 8 weeks</th>
                <th className="text-right pb-2 pr-3 font-semibold">All time</th>
                <th className="text-right pb-2 font-semibold">Last 30 days</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.question_id} className="border-t border-[#F0ECF6]" data-testid={`admin-guide-questions-row-${r.question_id}`}>
                  <td className="py-2 pr-3 text-[#1A1330]">
                    <span className="font-semibold">{i + 1}. {LABEL[r.question_id]}</span>
                    <span className="block mt-1 h-1.5 rounded-full bg-[#EDE7F7]" aria-hidden="true">
                      <span className="block h-full rounded-full bg-[#3D1A78]" style={{ width: `${(r.all_time / top) * 100}%` }} />
                    </span>
                    <span className="block text-[0.6875rem] text-[#6E6787] mt-1">
                      Open pages {r.reading} · Guided chat {r.guided}
                    </span>
                  </td>
                  <td className="py-2 pr-3 align-middle">
                    <Sparkline values={r.weekly} testid={`admin-guide-questions-trend-${r.question_id}`} />
                    <span className="block text-[0.625rem] text-[#6E6787]">This week {r.weekly[r.weekly.length - 1]}</span>
                  </td>
                  <td className="py-2 pr-3 text-right font-semibold" data-testid={`admin-guide-questions-all-${r.question_id}`}>{r.all_time}</td>
                  <td className="py-2 text-right" data-testid={`admin-guide-questions-30-${r.question_id}`}>{r.last_30_days}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
