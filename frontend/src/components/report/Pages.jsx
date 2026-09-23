import { CheckCircle2, ArrowDown } from "lucide-react";
import { Paper, SectionHeading, PullQuote, StatusDot, Snapshot } from "./Paper";

function Page1({ r }) {
  return (
    <Paper pageNum={1} pageTitle={r.page_titles[0]}>
      <div className="text-center mb-10">
        <p className="text-xs uppercase tracking-[0.3em] text-brand-purple font-bold mb-2">SA CoParents</p>
        <h1 className={`text-4xl sm:text-5xl font-semibold ${r.assessment_type === "ipv" ? "text-red-700" : "text-primary"}`} data-testid="report-title">{r.report_title}</h1>
        <p className="mt-3 text-lg text-muted-foreground" data-testid="report-subtitle">{r.subtitle}</p>
        {r.child_name && <p className="mt-1 text-sm text-muted-foreground" data-testid="report-child-name">Prepared with {r.child_name} at the center</p>}
        {r.is_demo && (
          <span className="inline-block mt-3 text-xs bg-secondary text-secondary-foreground px-3 py-1 rounded" data-testid="demo-badge">
            Sample report — generated from demo data
          </span>
        )}
      </div>

      <div className="grid sm:grid-cols-2 gap-4 mb-10">
        <div className="border border-border rounded-lg p-5 text-center" data-testid="parent-a-status">
          <p className="font-semibold">{r.parent_a_name}</p>
          <p className="text-sm text-align-green mt-1 flex items-center justify-center gap-1.5">
            <CheckCircle2 className="h-4 w-4" /> {r.parent_a_status}
          </p>
        </div>
        <div className="border border-border rounded-lg p-5 text-center" data-testid="parent-b-status">
          <p className="font-semibold">{r.parent_b_name}</p>
          <p className="text-sm text-align-green mt-1 flex items-center justify-center gap-1.5">
            <CheckCircle2 className="h-4 w-4" /> {r.parent_b_status}
          </p>
        </div>
      </div>

      <SectionHeading testId="purpose-heading">Purpose of This Report</SectionHeading>
      <p className="text-muted-foreground mb-4">This report combines two parents' perspectives to help identify:</p>
      <ul className="grid sm:grid-cols-2 gap-2 mb-8" data-testid="purpose-list">
        {r.purpose_items.map((item) => (
          <li key={item} className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-primary shrink-0" /> {item}
          </li>
        ))}
      </ul>

      <PullQuote testId="report-disclaimer">{r.disclaimer}</PullQuote>

      <div className="mt-10">
        <Snapshot snapshot={r.snapshot} note={r.snapshot_note} />
      </div>
    </Paper>
  );
}

function Page2({ r }) {
  return (
    <Paper pageNum={2} pageTitle={r.page_titles[1]}>
      <SectionHeading testId="child-center-heading">What Both Parents Told Us About Their Child</SectionHeading>
      <p className="text-muted-foreground mb-8">
        Before looking at any differences, here is what you already share: why you completed this assessment.
      </p>

      <h3 className="font-display text-2xl font-semibold mb-4">Shared Goals</h3>
      <ul className="grid sm:grid-cols-2 gap-3 mb-10" data-testid="shared-goals-list">
        {r.shared_goals.map((g) => (
          <li key={g} className="flex items-center gap-2.5 text-sm bg-muted/50 rounded-md px-4 py-3">
            <CheckCircle2 className="h-4 w-4 text-align-green shrink-0" /> {g}
          </li>
        ))}
      </ul>

      <div className="grid sm:grid-cols-2 gap-4 mb-10">
        <div className="border border-border rounded-lg p-6" data-testid="parent-a-concern">
          <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-3">{r.parent_a_name}'s Primary Concern</p>
          <p className="font-display text-xl italic leading-relaxed">"{r.parent_a_concern || "Not provided."}"</p>
        </div>
        <div className="border border-border rounded-lg p-6" data-testid="parent-b-concern">
          <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-3">{r.parent_b_name}'s Primary Concern</p>
          <p className="font-display text-xl italic leading-relaxed">"{r.parent_b_concern || "Not provided."}"</p>
        </div>
      </div>

      <h3 className="font-display text-2xl font-semibold mb-3">Shared Child-Focused Question</h3>
      <PullQuote testId="central-question">{r.central_question}</PullQuote>
    </Paper>
  );
}

function Page3({ r }) {
  return (
    <Paper pageNum={3} pageTitle={r.page_titles[2]}>
      <SectionHeading testId="alignment-heading">Areas of Alignment</SectionHeading>
      <div className="flex items-center gap-2.5 mb-6">
        <StatusDot color="green" />
        <p className="font-semibold" data-testid="alignment-count">Strong Alignment — {r.alignments.length} area{r.alignments.length === 1 ? "" : "s"} identified</p>
      </div>
      <p className="text-muted-foreground mb-8">Both parents identified these issues similarly:</p>

      {r.alignments.length === 0 ? (
        <p className="text-muted-foreground italic" data-testid="no-alignments">
          No areas of strong alignment were identified in this assessment. The differences identified on the next page are the starting point for conversation.
        </p>
      ) : (
        <div className="space-y-4 mb-10" data-testid="alignments-list">
          {r.alignments.map((a) => (
            <div key={a.topic} className="flex gap-4 border border-border rounded-lg p-5">
              <StatusDot color="green" />
              <div>
                <p className="font-semibold">{a.topic}</p>
                <p className="text-sm text-muted-foreground mt-1">{a.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <h3 className="font-display text-2xl font-semibold mb-3">Build From What Already Works</h3>
      <PullQuote testId="alignment-foundation-note">{r.alignment_foundation_note}</PullQuote>
    </Paper>
  );
}

function Page4({ r }) {
  return (
    <Paper pageNum={4} pageTitle={r.page_titles[3]}>
      <SectionHeading testId="differences-heading">Differences in Perspective</SectionHeading>
      {r.differences.length === 0 ? (
        <p className="text-muted-foreground italic" data-testid="no-differences">
          No significant differences in perspective were identified. Both parents responded similarly across all topics.
        </p>
      ) : (
        <div className="overflow-x-auto mb-8" data-testid="differences-table-wrapper">
          <table className="w-full text-sm border border-border rounded-lg overflow-hidden" data-testid="differences-table">
            <thead>
              <tr className="bg-brand-purple/10 text-left text-brand-purple">
                <th className="px-4 py-3 font-semibold">Child Issue</th>
                <th className="px-4 py-3 font-semibold">{r.parent_a_name}</th>
                <th className="px-4 py-3 font-semibold">{r.parent_b_name}</th>
              </tr>
            </thead>
            <tbody>
              {r.differences.map((d) => (
                <tr key={d.topic} className="border-t border-border" data-testid={`difference-row-${d.topic.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
                  <td className="px-4 py-3 font-medium">{d.topic}</td>
                  <td className="px-4 py-3 text-muted-foreground">{d.parent_a}</td>
                  <td className="px-4 py-3 text-muted-foreground">{d.parent_b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <PullQuote testId="differences-note">{r.differences_note}</PullQuote>
    </Paper>
  );
}

function Page5({ r }) {
  return (
    <Paper pageNum={5} pageTitle={r.page_titles[4]}>
      <SectionHeading testId="child-needs-heading">Child Needs Identified</SectionHeading>
      <p className="text-muted-foreground mb-8">
        Based on the parents' responses, the following areas may benefit from additional attention:
      </p>
      <div className="grid sm:grid-cols-2 gap-4 mb-10" data-testid="child-needs-list">
        {r.child_needs.map((n) => (
          <div key={n.title} className="border border-border rounded-lg p-6 bg-muted/40" data-testid={`child-need-${n.title.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
            <p className="font-display text-xl font-semibold mb-2">{n.title}</p>
            <p className="text-sm text-muted-foreground leading-relaxed">{n.text}</p>
          </div>
        ))}
      </div>
      <div className="border-t border-border pt-6">
        <p className="text-sm text-muted-foreground italic" data-testid="child-needs-note">
          Notice what this page does not say: "one parent needs to…" Everything stays centered on the child.
        </p>
      </div>
    </Paper>
  );
}

function Page6({ r }) {
  return (
    <Paper pageNum={6} pageTitle={r.page_titles[5]}>
      <SectionHeading testId="options-heading">Options to Consider</SectionHeading>
      <p className="text-muted-foreground mb-8">Parents could consider:</p>
      <div className="grid sm:grid-cols-2 gap-3 mb-10" data-testid="options-list">
        {r.options.map((o) => (
          <div key={o} className="flex items-center gap-3 border border-border rounded-md px-4 py-3" data-testid={`option-${o.toLowerCase().replace(/[^a-z]+/g, "-").slice(0, 40)}`}>
            <span className="h-4 w-4 border-2 border-primary rounded-sm shrink-0" />
            <span className="text-sm">{o}</span>
          </div>
        ))}
      </div>
      <PullQuote testId="options-note">
        {r.options_note} This distinction preserves the educational and resource nature of this report.
      </PullQuote>
    </Paper>
  );
}

function Page7({ r }) {
  return (
    <Paper pageNum={7} pageTitle={r.page_titles[6]}>
      <SectionHeading testId="questions-heading">Questions Worth Discussing</SectionHeading>
      <p className="text-muted-foreground mb-8">
        This report converts positions into questions. Instead of "Why won't the other parent agree?",
        the following questions prepare both parents for a child-focused conversation:
      </p>
      <div className="space-y-4 mb-10" data-testid="questions-list">
        {r.conversation_questions.map((q, i) => (
          <div key={i} className="border-l-4 border-align-blue rounded-r-lg bg-muted/40 p-5" data-testid={`conversation-question-${i}`}>
            <p className="font-display text-lg italic leading-relaxed">{q}</p>
          </div>
        ))}
      </div>
      <PullQuote testId="questions-central">{r.central_question}</PullQuote>
    </Paper>
  );
}

function Page8({ r }) {
  const m = r.professional_map;
  const stats = [
    { label: "Areas of Alignment", value: m.alignment_count, color: "green" },
    { label: "Areas Needing Conversation", value: m.conversation_count, color: "blue" },
    { label: "Possible Professional Input", value: m.professional_input_count, color: "yellow" },
    { label: "Potential Child Needs", value: m.child_needs_count, color: "purple" },
  ];
  return (
    <Paper pageNum={8} pageTitle={r.page_titles[7]}>
      <SectionHeading testId="professional-heading">Professional Discussion Map</SectionHeading>
      <p className="text-muted-foreground mb-8">
        Designed for a mediator, attorney, therapist, parenting coordinator or facilitator, child specialist,
        or other appropriate professional.
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-12" data-testid="professional-stats">
        {stats.map((s) => (
          <div key={s.label} className="border border-border rounded-lg p-5 text-center" data-testid={`stat-${s.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
            <StatusDot color={s.color} />
            <p className="font-display text-4xl font-semibold mt-2" data-testid={`stat-count-${s.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>{s.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <h3 className="font-display text-2xl font-semibold mb-6">Suggested Discussion Sequence</h3>
      <div className="space-y-0" data-testid="discussion-sequence">
        {m.sequence.map((s, i) => (
          <div key={s.step}>
            <div className="flex items-start gap-4 border border-border rounded-lg p-5 bg-muted/30" data-testid={`sequence-step-${i}`}>
              <span className="font-display text-2xl font-semibold text-accent w-8 shrink-0">{i + 1}</span>
              <div>
                <p className="font-semibold">{s.step}</p>
                <p className="text-sm text-muted-foreground italic mt-1">"{s.question}"</p>
              </div>
            </div>
            {i < m.sequence.length - 1 && (
              <div className="flex justify-start pl-9 py-1">
                <ArrowDown className="h-4 w-4 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}
      </div>
    </Paper>
  );
}

function PlanBlock({ item, index }) {
  const fields = [
    { label: "What we already agree about:", value: item.already_agree },
    { label: "Information we need:", value: "" },
    { label: "Options we will consider:", value: "" },
    { label: "Professional we may consult:", value: "" },
    { label: "Next step:", value: "" },
    { label: "Date to revisit:", value: "" },
  ];
  return (
    <div className="border border-border rounded-lg p-6 mb-8" data-testid={`action-plan-${index}`}>
      <p className="text-xs uppercase tracking-widest text-accent font-semibold">Issue #{index + 1}</p>
      <h3 className="font-display text-2xl font-semibold mt-1 mb-4">{item.issue}</h3>
      <div className="space-y-4">
        <div>
          <p className="text-sm font-medium">Child's Need:</p>
          <p className="text-sm text-muted-foreground mt-1">{item.child_need}</p>
        </div>
        {fields.map((f) => (
          <div key={f.label}>
            <p className="text-sm font-medium">{f.label}</p>
            {f.value ? (
              <p className="text-sm text-muted-foreground mt-1">{f.value}</p>
            ) : (
              <div className="worksheet-line mt-1" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Page9({ r }) {
  return (
    <Paper pageNum={9} pageTitle={r.page_titles[8]}>
      <SectionHeading testId="action-plan-heading">Our Next Steps</SectionHeading>
      <p className="text-muted-foreground mb-8">
        A working plan for the top issues identified in this report. Complete this together, in mediation,
        or with a professional.
      </p>
      {r.action_plan.length === 0 ? (
        <p className="text-muted-foreground italic" data-testid="no-action-plan">
          No issues requiring discussion were identified. Use this page to plan how to maintain your current alignment as your child grows.
        </p>
      ) : (
        r.action_plan.map((item, i) => <PlanBlock key={item.issue} item={item} index={i} />)
      )}
    </Paper>
  );
}

function SummaryList({ color, title, items, testId }) {
  return (
    <div className="mb-8" data-testid={testId}>
      <div className="flex items-center gap-2.5 mb-4">
        <StatusDot color={color} />
        <h3 className="font-display text-2xl font-semibold">{title}</h3>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground italic ml-6">None identified in this assessment.</p>
      ) : (
        <ul className="space-y-2 ml-1">
          {items.map((item, i) => (
            <li key={i} className="flex gap-3 text-sm leading-relaxed" data-testid={`${testId}-item-${i}`}>
              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-foreground/40 shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Page10({ r }) {
  const s = r.summary;
  const cm = r.court_map;
  return (
    <Paper pageNum={10} pageTitle={r.page_titles[9]}>
      <SectionHeading testId="summary-heading">Your Alignment Map</SectionHeading>

      {cm ? (
        <>
          <SummaryList color="green" title="Agreed Parenting Terms" items={cm.agreed} testId="summary-agreed" />
          <SummaryList color="yellow" title="Terms Close to Agreement" items={cm.close} testId="summary-close" />
          <SummaryList color="blue" title="Terms Requiring Discussion" items={cm.discussion} testId="summary-discussion" />
          <SummaryList color="purple" title="Issues Where Additional Information May Help" items={cm.info} testId="summary-info" />
        </>
      ) : (
        <>
          <SummaryList color="green" title="Where You Align" items={s.aligned} testId="summary-aligned" />
          <SummaryList color="yellow" title="Where More Information May Help" items={s.info} testId="summary-more-info" />
          <SummaryList color="blue" title="Where Conversation May Help" items={s.conversation} testId="summary-conversation" />
          <SummaryList color="purple" title="Options to Explore" items={s.options} testId="summary-options" />
        </>
      )}

      <div className="border border-border rounded-lg p-6 bg-muted/40 mb-10" data-testid="priority-statement">
        <p className="text-xs uppercase tracking-widest text-accent font-semibold mb-3">Child-Focused Priority</p>
        <p className="font-display text-lg leading-relaxed">{s.priority}</p>
      </div>

      <div className="text-center border-t border-border pt-10">
        <h3 className="font-display text-4xl sm:text-5xl font-bold text-align-purple" data-testid="philosophy-heading">{r.philosophy_heading}</h3>
        <p className="mt-3 text-muted-foreground max-w-xl mx-auto" data-testid="philosophy-note">{r.philosophy_note}</p>
        <p className="mt-6 text-sm italic text-muted-foreground max-w-xl mx-auto" data-testid="philosophy-line">
          "{r.philosophy}"
        </p>
      </div>
    </Paper>
  );
}

export const REPORT_PAGES = [Page1, Page2, Page3, Page4, Page5, Page6, Page7, Page8, Page9, Page10];
