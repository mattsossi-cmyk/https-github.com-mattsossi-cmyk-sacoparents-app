import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { SAFE_ND } from '../data/safeNdContent';

/**
 * SafeNdReview — SACOparentsAlign (STAFF ONLY)
 * Put in: frontend/src/pages/SafeNdReview.jsx
 * Routes (inside the app's existing staff sign-in protection):
 *   <Route path="/staff/safe-nd" element={<SafeNdReview />} />
 *   <Route path="/staff/safe-nd/:id" element={<SafeNdReview />} />     (id "new" starts a review)
 *
 * Trained reviewers complete the SAFE-ND™ Functional Map here.
 * Content comes from src/data/safeNdContent.js (licensed; © Trisha Wright, used with permission).
 *
 * Backend (SACOparentsAlign server; every call requires a signed-in staff reviewer):
 *   GET  /api/safe-nd/reviews                → [{ id, child, reviewDate, status, updatedAt }]
 *   GET  /api/safe-nd/reviews/:id            → { id, status, data, updatedAt }
 *   POST /api/safe-nd/reviews        {data}  → { id }
 *   PUT  /api/safe-nd/reviews/:id    {data}  → { ok: true }          (drafts only)
 *   POST /api/safe-nd/reviews/:id/finalize   → { ok: true }          (locks the review)
 * Reviews are never visible to parents.
 */

const BACKEND = (typeof process !== 'undefined' && process.env && process.env.REACT_APP_BACKEND_URL) || '';
const API = `${BACKEND}/api/safe-nd/reviews`;
const BASE = '/staff/safe-nd';

const NAVY = '#1F2A44';
const TEAL_LIGHT = '#E3F4F1';
const RED = '#B42318';
const RED_LIGHT = '#FBE1DC';
const SAND = '#F5E8D6';
const GRAY_LIGHT = '#E9EEF3';
const GREEN = '#1E6B45';
const GREEN_LIGHT = '#ECF8F1';
const GRAY = '#5F6B7A';
const LINE = '#D5DCE4';

async function api(path = '', options = {}) {
  const res = await fetch(`${API}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 401 || res.status === 403) throw new Error('auth');
  if (!res.ok) throw new Error(String(res.status));
  const text = await res.text();
  return text ? JSON.parse(text) : {};
}

export function emptyReview() {
  const data = {};
  SAFE_ND.sections.forEach((s) => {
    data[s.id] = {};
    s.fields.forEach((f) => {
      if (f.type === 'checks') data[s.id][f.id] = { selected: [], other: '' };
      else if (f.type === 'domains') data[s.id][f.id] = Object.fromEntries(f.rows.map((r) => [r.id, { priority: '', notes: '' }]));
      else if (f.type === 'homes') data[s.id][f.id] = Object.fromEntries(f.rows.map((r) => [r.id, { a: '', b: '', plan: '' }]));
      else if (f.type !== 'heading') data[s.id][f.id] = '';
    });
  });
  return data;
}

// Fill in anything missing (e.g. a domain added to the content file after a review was saved)
function withDefaults(saved) {
  const base = emptyReview();
  Object.keys(base).forEach((sid) => {
    Object.keys(base[sid]).forEach((fid) => {
      const v = saved && saved[sid] ? saved[sid][fid] : undefined;
      if (v === undefined) return;
      base[sid][fid] = typeof base[sid][fid] === 'object' && !Array.isArray(base[sid][fid]) ? { ...base[sid][fid], ...v } : v;
    });
  });
  return base;
}

export default function SafeNdReview() {
  const { id } = useParams();
  return (
    <div style={st.page}>
      <style>{PRINT_CSS}</style>
      <header style={st.header} className="no-print">
        <Link to={BASE} style={st.brand}>SACOparentsAlign · Staff</Link>
        <span style={st.staffTag}>Reviewers only</span>
      </header>
      {id ? <Editor key={id} id={id} /> : <ReviewList />}
    </div>
  );
}

// ───────────────────────────── LIST ─────────────────────────────
function ReviewList() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api()
      .then((r) => setRows(Array.isArray(r) ? r : []))
      .catch((e) => setError(e.message === 'auth' ? 'auth' : 'load'));
  }, []);

  return (
    <main style={st.main}>
      <h1 style={st.h1}>{SAFE_ND.title} reviews</h1>
      <p style={st.lead}>{SAFE_ND.subtitle}</p>
      <Link to={`${BASE}/new`} style={st.primaryLink}>+ Start a new review</Link>
      {error === 'auth' && <AuthNotice />}
      {error === 'load' && <p style={st.warn}>Reviews couldn't be loaded. Please refresh.</p>}
      {rows === null && !error && <p style={st.muted}>Loading…</p>}
      {rows && rows.length === 0 && <p style={st.muted}>No reviews yet.</p>}
      {rows && rows.length > 0 && (
        <ul style={st.list}>
          {rows.map((r) => (
            <li key={r.id}>
              <Link to={`${BASE}/${r.id}`} style={st.row}>
                <span>
                  <strong style={{ color: NAVY }}>{r.child || 'Untitled review'}</strong>
                  <span style={st.rowMeta}>
                    {r.reviewDate ? `Review date ${r.reviewDate}` : 'No review date'}
                    {r.updatedAt ? ` · updated ${String(r.updatedAt).slice(0, 10)}` : ''}
                  </span>
                </span>
                <StatusTag status={r.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p style={st.credit}>{SAFE_ND.credit}</p>
    </main>
  );
}

function StatusTag({ status }) {
  const final = status === 'final';
  return (
    <span style={{ ...st.tag, background: final ? GREEN_LIGHT : SAND, color: final ? GREEN : '#7A4B00' }}>
      {final ? 'Final' : 'Draft'}
    </span>
  );
}

function AuthNotice() {
  return <p style={st.warn}>Staff sign-in required. Please sign in with your reviewer account.</p>;
}

// ───────────────────────────── EDITOR ─────────────────────────────
function Editor({ id }) {
  const navigate = useNavigate();
  const isNew = id === 'new';
  const [data, setData] = useState(isNew ? emptyReview() : null);
  const [status, setStatus] = useState('draft');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState('');
  const [error, setError] = useState('');
  const [savedAt, setSavedAt] = useState('');
  const locked = status === 'final';

  useEffect(() => {
    if (isNew) return;
    api(`/${encodeURIComponent(id)}`)
      .then((r) => {
        setData(withDefaults(r.data));
        setStatus(r.status || 'draft');
      })
      .catch((e) => setError(e.message === 'auth' ? 'auth' : 'load'));
  }, [id, isNew]);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const set = useCallback(
    (sid, fid, value) => {
      if (locked) return;
      setData((d) => ({ ...d, [sid]: { ...d[sid], [fid]: value } }));
      setDirty(true);
    },
    [locked]
  );

  const save = async () => {
    setSaving('saving');
    setError('');
    try {
      if (isNew) {
        const r = await api('', { method: 'POST', body: JSON.stringify({ data }) });
        setDirty(false);
        navigate(`${BASE}/${r.id}`, { replace: true });
        return true;
      }
      await api(`/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify({ data }) });
      setDirty(false);
      setSavedAt(new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }));
      return true;
    } catch (e) {
      setError(e.message === 'auth' ? 'auth' : 'save');
      return false;
    } finally {
      setSaving('');
    }
  };

  const finalize = async () => {
    const sig = data.disposition && data.disposition.signature && data.disposition.signature.trim();
    const date = data.disposition && data.disposition.signedDate;
    if (!sig || !date) {
      setError('sign');
      document.getElementById('sec-disposition')?.scrollIntoView({ behavior: 'smooth' });
      return;
    }
    if (!window.confirm('Finalize this review? It will be locked and can no longer be edited.')) return;
    if (dirty && !(await save())) return;
    try {
      await api(`/${encodeURIComponent(id)}/finalize`, { method: 'POST' });
      setStatus('final');
    } catch (e) {
      setError(e.message === 'auth' ? 'auth' : 'save');
    }
  };

  if (error === 'auth') return <main style={st.main}><AuthNotice /></main>;
  if (error === 'load') return <main style={st.main}><p style={st.warn}>This review couldn't be loaded.</p><Link to={BASE} style={st.backLink}>← All reviews</Link></main>;
  if (!data) return <main style={st.main}><p style={st.muted}>Loading…</p></main>;

  return (
    <>
      <nav style={st.sectionNav} className="no-print" aria-label="Sections">
        {SAFE_ND.sections.map((s) => (
          <a key={s.id} href={`#sec-${s.id}`} style={st.navChip}>
            {s.number ? `${s.number}. ` : ''}
            {s.title.replace('SAFE-ND™ ', '')}
          </a>
        ))}
      </nav>

      <main style={st.main}>
        <div className="no-print">
          <Link to={BASE} style={st.backLink}>← All reviews</Link>
        </div>
        <div style={st.titleRow}>
          <div>
            <h1 style={st.h1}>{SAFE_ND.title}</h1>
            <p style={st.subtitle}>{SAFE_ND.subtitle}</p>
          </div>
          <StatusTag status={status} />
        </div>
        <p style={st.lead}>{SAFE_ND.description}</p>
        {locked && <p style={st.lockedNote}>🔒 This review is final and locked. You can still print it.</p>}

        {SAFE_ND.sections.map((s) => (
          <section key={s.id} id={`sec-${s.id}`} style={st.section}>
            <h2 style={st.h2}>
              {s.number && <span style={{ color: RED }}>{s.number}. </span>}
              {s.title}
            </h2>
            {(s.notes || []).map((n) => <Note key={n.title} note={n} />)}
            {s.fields.map((f) => (
              <Field key={f.id} field={f} value={data[s.id][f.id]} onChange={(v) => set(s.id, f.id, v)} locked={locked} />
            ))}
            {(s.notesAfter || []).map((n) => <Note key={n.title} note={n} />)}
            {s.id === 'disposition' && error === 'sign' && (
              <p style={st.warn} role="alert">Add the reviewer signature and date before finalizing.</p>
            )}
          </section>
        ))}

        <Note note={{ type: 'scope', title: 'Final scope note', text: SAFE_ND.finalScope }} />
        <p style={st.credit}>{SAFE_ND.credit}</p>
      </main>

      <div style={st.actionBar} className="no-print">
        <span style={st.saveState} aria-live="polite">
          {saving === 'saving'
            ? 'Saving…'
            : error === 'save'
            ? '⚠ Not saved. Try again.'
            : dirty
            ? 'Unsaved changes'
            : savedAt
            ? `Saved ${savedAt}`
            : locked
            ? 'Final'
            : isNew
            ? 'Not saved yet'
            : 'All changes saved'}
        </span>
        <div style={st.actionBtns}>
          <button type="button" onClick={() => window.print()} style={st.ghostBtn}>Print / PDF</button>
          {!locked && (
            <>
              <button type="button" onClick={save} disabled={saving === 'saving' || (!dirty && !isNew)} style={{ ...st.ghostBtn, ...(dirty || isNew ? null : st.disabled) }}>
                Save draft
              </button>
              {!isNew && (
                <button type="button" onClick={finalize} style={st.primaryBtn}>Finalize</button>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

// ───────────────────────────── PIECES ─────────────────────────────
function Note({ note }) {
  const look = {
    info: { background: TEAL_LIGHT },
    warn: { background: RED_LIGHT },
    scope: { background: SAND },
    plain: { background: GRAY_LIGHT },
  }[note.type] || { background: GRAY_LIGHT };
  return (
    <div style={{ ...st.note, ...look }}>
      <strong style={st.noteTitle}>{note.title}</strong>
      <span>{note.text}</span>
    </div>
  );
}

function Field({ field, value, onChange, locked }) {
  const f = field;
  if (f.type === 'heading') return <h3 style={st.h3}>{f.label}</h3>;

  if (f.type === 'text' || f.type === 'date') {
    return (
      <label style={st.label}>
        {f.label}
        <input type={f.type} value={value} onChange={(e) => onChange(e.target.value)} readOnly={locked} style={st.input} />
      </label>
    );
  }

  if (f.type === 'textarea') {
    return (
      <label style={st.label}>
        {f.label}
        <textarea value={value} onChange={(e) => onChange(e.target.value)} readOnly={locked} rows={f.rows || 3} style={st.textarea} />
      </label>
    );
  }

  if (f.type === 'checks') {
    const toggle = (o) =>
      onChange({ ...value, selected: value.selected.includes(o) ? value.selected.filter((x) => x !== o) : [...value.selected, o] });
    const safetyOn = f.safetyOption && value.selected.includes(f.safetyOption);
    return (
      <fieldset style={st.fieldset}>
        <legend style={st.legend}>{f.label}</legend>
        <div style={st.checkGrid}>
          {f.options.map((o) => (
            <label key={o} style={{ ...st.check, ...(value.selected.includes(o) ? st.checkOn : null) }}>
              <input type="checkbox" checked={value.selected.includes(o)} onChange={() => toggle(o)} disabled={locked} style={st.box} />
              {o}
            </label>
          ))}
        </div>
        {f.other && (
          <label style={{ ...st.label, marginTop: 10 }}>
            Other
            <input value={value.other} onChange={(e) => onChange({ ...value, other: e.target.value })} readOnly={locked} style={st.input} />
          </label>
        )}
        {safetyOn && (
          <p style={st.safety} role="alert">
            Follow your mandatory-reporting and agency safety procedures. If a child is in immediate danger, call 911.
          </p>
        )}
      </fieldset>
    );
  }

  if (f.type === 'domains') {
    return (
      <div>
        {f.rows.map((r) => {
          const v = value[r.id];
          const setRow = (patch) => onChange({ ...value, [r.id]: { ...v, ...patch } });
          return (
            <div key={r.id} style={st.card}>
              <div style={st.cardHead}>{r.name}</div>
              <p style={st.identify}><span style={st.small}>What to identify: </span>{r.identify}</p>
              <div style={st.priorityRow} role="radiogroup" aria-label={`${r.name} priority`}>
                <span style={st.small}>Priority</span>
                {[['L', 'Low'], ['M', 'Medium'], ['H', 'High']].map(([k, label]) => (
                  <label key={k} style={{ ...st.pill, ...(v.priority === k ? st.pillOn : null) }}>
                    <input type="radio" name={`p-${r.id}`} checked={v.priority === k} onChange={() => setRow({ priority: k })} disabled={locked} style={st.srOnly} />
                    {label}
                  </label>
                ))}
              </div>
              <label style={st.label}>
                Family-specific observations / supports
                <textarea value={v.notes} onChange={(e) => setRow({ notes: e.target.value })} readOnly={locked} rows={3} style={st.textarea} />
              </label>
            </div>
          );
        })}
      </div>
    );
  }

  if (f.type === 'homes') {
    return (
      <div>
        {f.rows.map((r) => {
          const v = value[r.id];
          const setRow = (patch) => onChange({ ...value, [r.id]: { ...v, ...patch } });
          return (
            <div key={r.id} style={st.card}>
              <div style={st.cardHead}>{r.name}</div>
              <p style={st.identify}>{r.detail}</p>
              <div style={st.homeGrid}>
                {[['a', 'Home A'], ['b', 'Home B'], ['plan', 'Planning implication']].map(([k, label]) => (
                  <label key={k} style={st.label}>
                    {label}
                    <textarea value={v[k]} onChange={(e) => setRow({ [k]: e.target.value })} readOnly={locked} rows={3} style={st.textarea} />
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    );
  }
  return null;
}

// ───────────────────────────── STYLES ─────────────────────────────
const PRINT_CSS = `
@media print {
  .no-print { display: none !important; }
  body { background: #fff !important; }
  textarea, input { border: 1px solid #bbb !important; }
  section { break-inside: auto; }
}`;

const st = {
  page: { minHeight: '100vh', background: '#F8FAFC', color: '#1B2330', fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif', lineHeight: 1.5, paddingBottom: 90 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '12px 16px', background: NAVY },
  brand: { color: '#FFFFFF', fontWeight: 700, fontSize: 16, textDecoration: 'none' },
  staffTag: { background: '#FFFFFF22', color: '#FFFFFF', borderRadius: 99, padding: '4px 10px', fontSize: 13 },
  sectionNav: { display: 'flex', gap: 8, overflowX: 'auto', padding: '10px 16px', background: '#FFFFFF', borderBottom: `1px solid ${LINE}`, position: 'sticky', top: 0, zIndex: 5 },
  navChip: { flexShrink: 0, borderRadius: 99, border: `1px solid ${LINE}`, padding: '6px 12px', fontSize: 14, color: NAVY, textDecoration: 'none', background: '#FFFFFF', whiteSpace: 'nowrap' },
  main: { maxWidth: 860, margin: '0 auto', padding: '20px 16px 24px' },
  titleRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 },
  h1: { color: NAVY, fontSize: 28, lineHeight: 1.2, margin: '6px 0 4px', fontWeight: 800 },
  subtitle: { fontWeight: 700, margin: '0 0 8px', fontSize: 17 },
  lead: { color: GRAY, margin: '0 0 16px' },
  h2: { color: NAVY, fontSize: 22, margin: '0 0 12px' },
  h3: { color: NAVY, fontSize: 18, margin: '18px 0 10px' },
  section: { background: '#FFFFFF', border: `1px solid ${LINE}`, borderRadius: 12, padding: 16, marginBottom: 16, scrollMarginTop: 60 },
  note: { display: 'block', borderRadius: 8, padding: 12, fontSize: 14, margin: '0 0 14px' },
  noteTitle: { display: 'block', textTransform: 'uppercase', fontSize: 13, letterSpacing: '0.03em', marginBottom: 4 },
  label: { display: 'block', fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#2A3442' },
  input: { display: 'block', width: '100%', boxSizing: 'border-box', minHeight: 42, marginTop: 4, borderRadius: 8, border: `1px solid ${LINE}`, padding: '8px 10px', fontSize: 16, fontFamily: 'inherit', background: '#FFFFFF' },
  textarea: { display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 4, borderRadius: 8, border: `1px solid ${LINE}`, padding: '8px 10px', fontSize: 16, fontFamily: 'inherit', resize: 'vertical', background: '#FFFFFF' },
  fieldset: { border: 'none', padding: 0, margin: '0 0 14px' },
  legend: { fontWeight: 700, fontSize: 16, color: NAVY, marginBottom: 8, padding: 0 },
  checkGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 },
  check: { display: 'flex', gap: 10, alignItems: 'flex-start', borderWidth: 1, borderStyle: 'solid', borderColor: LINE, borderRadius: 8, padding: '9px 10px', fontSize: 15, cursor: 'pointer', background: '#FFFFFF' },
  checkOn: { borderColor: NAVY, background: '#EEF2F8' },
  box: { width: 18, height: 18, margin: '2px 0 0', flexShrink: 0, accentColor: NAVY },
  card: { border: `1px solid ${LINE}`, borderRadius: 10, padding: 12, marginBottom: 12 },
  cardHead: { fontWeight: 800, color: NAVY, fontSize: 16 },
  identify: { fontSize: 14, margin: '4px 0 10px' },
  small: { fontSize: 13, color: GRAY },
  priorityRow: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 10 },
  pill: { borderWidth: 1, borderStyle: 'solid', borderColor: LINE, borderRadius: 99, padding: '6px 14px', fontSize: 14, cursor: 'pointer', minHeight: 36, display: 'inline-flex', alignItems: 'center' },
  pillOn: { borderColor: NAVY, background: NAVY, color: '#FFFFFF', fontWeight: 700 },
  srOnly: { position: 'absolute', width: 1, height: 1, opacity: 0, overflow: 'hidden' },
  homeGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 },
  safety: { background: RED_LIGHT, color: RED, fontWeight: 600, borderRadius: 8, padding: 10, marginTop: 10 },
  warn: { background: SAND, color: '#5C3A00', borderRadius: 8, padding: '10px 12px' },
  lockedNote: { background: GREEN_LIGHT, color: GREEN, borderRadius: 8, padding: '10px 12px', fontWeight: 600 },
  muted: { color: GRAY },
  credit: { fontSize: 13, color: GRAY, textAlign: 'center', marginTop: 16 },
  backLink: { color: NAVY, fontWeight: 600, textDecoration: 'none', display: 'inline-flex', minHeight: 40, alignItems: 'center' },
  primaryLink: { display: 'inline-block', background: NAVY, color: '#FFFFFF', borderRadius: 8, padding: '12px 18px', fontWeight: 700, textDecoration: 'none', margin: '4px 0 18px' },
  list: { listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, background: '#FFFFFF', border: `1px solid ${LINE}`, borderRadius: 10, padding: 14, textDecoration: 'none', color: 'inherit' },
  rowMeta: { display: 'block', fontSize: 13, color: GRAY },
  tag: { borderRadius: 99, padding: '4px 10px', fontSize: 13, fontWeight: 700, flexShrink: 0 },
  actionBar: { position: 'fixed', left: 0, right: 0, bottom: 0, background: '#FFFFFF', borderTop: `1px solid ${LINE}`, padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap', zIndex: 10 },
  saveState: { fontSize: 14, color: GRAY },
  actionBtns: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  ghostBtn: { minHeight: 44, borderRadius: 8, border: `1px solid ${NAVY}`, background: '#FFFFFF', color: NAVY, fontWeight: 700, fontSize: 15, padding: '8px 14px', cursor: 'pointer' },
  primaryBtn: { minHeight: 44, borderRadius: 8, border: 'none', background: NAVY, color: '#FFFFFF', fontWeight: 700, fontSize: 15, padding: '8px 16px', cursor: 'pointer' },
  disabled: { opacity: 0.45, cursor: 'not-allowed' },
};
