import { useEffect, useRef, useState } from 'react';

import GuideAvatar from '../selfJourney/GuideAvatar';
import '../selfJourney/selfJourney.css';
import './SelfJourneyGuide.css';
import GuideSheet from './GuideSheet';
import { GUIDE_LOGO } from './guideAnswers';

// Floating Journey Guide for the reading Self Journey: ready-made path answers for everyone, AI once signed in.
export default function SelfJourneyGuide({ steps, step }) {
  const [open, setOpen] = useState(false);
  const openBtn = useRef(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    if (wasOpen.current && !open) openBtn.current?.focus();
    wasOpen.current = open;
  }, [open]);

  // Room under the site footer so the floating button never sits on its last links.
  useEffect(() => {
    document.body.classList.add('has-sjr-guide');
    return () => document.body.classList.remove('has-sjr-guide');
  }, []);

  return (
    <div className="sjg">
      {!open && (
        <button type="button" ref={openBtn} className="sjg-open" onClick={() => setOpen(true)} data-testid="sjr-guide-open">
          <GuideAvatar size={30} logoSrc={GUIDE_LOGO} calm={step?.id === 'safety-first'} decorative />
          <span>Questions about the paths?</span>
        </button>
      )}
      {open && <GuideSheet steps={steps} step={step} onClose={() => setOpen(false)} />}
    </div>
  );
}
