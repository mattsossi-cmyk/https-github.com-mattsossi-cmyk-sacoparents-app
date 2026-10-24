// Shared "general education, not advice" line for Self Journey pages.
export default function Disclaimer({ style }) {
  return (
    <p data-testid="disclaimer" style={{ fontSize: 13, color: '#6B6480', lineHeight: 1.5, margin: '0 0 10px', ...style }}>
      SA CoParents shares general education to help you think things through. It is not legal, medical or
      mental-health advice, and it does not replace a lawyer, doctor, counselor or family violence advocate.
      If you are in danger, call 911.
    </p>
  );
}
