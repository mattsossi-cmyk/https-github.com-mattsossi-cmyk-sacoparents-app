// Anonymous count of a ready-made question tap: only the question id and where it was tapped.
// Sent without the sign-in token or cookies, so the server can't tell who tapped it.
export const countTap = (questionId, where) =>
  fetch(`${process.env.REACT_APP_BACKEND_URL}/api/guide-questions/tap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId, where }),
    credentials: 'omit',
    keepalive: true,
  }).catch(() => {});
