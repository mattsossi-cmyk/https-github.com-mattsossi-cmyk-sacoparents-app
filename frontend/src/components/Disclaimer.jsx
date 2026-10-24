/**
 * Disclaimer — SA CoParents
 * Put in: frontend/src/components/Disclaimer.jsx
 *
 * Use on any page:
 *   import Disclaimer from '../components/Disclaimer';
 *   <Disclaimer />
 */

export const DISCLAIMER_TEXT =
  'SA CoParents provides general information, not legal, medical or mental-health advice. ' +
  'Talk to an attorney, doctor or counselor about your situation.';

export default function Disclaimer({ style }) {
  return (
    <p
      role="note"
      data-testid="disclaimer"
      style={{
        fontSize: 13,
        lineHeight: 1.5,
        color: '#6B6480',
        background: '#F8F6FC',
        border: '1px solid #EEE9F6',
        borderRadius: 10,
        padding: '10px 12px',
        margin: '0 auto 12px',
        maxWidth: 680,
        textAlign: 'left',
        ...style,
      }}
    >
      <strong style={{ color: '#3D1A78' }}>Please note:</strong> {DISCLAIMER_TEXT} If you are in danger,
      call 911.
    </p>
  );
}
