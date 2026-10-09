/** Deadline countdowns from the Tracker's deadline_at ("2026-10-30T15:00:00", local time). */

const DAY_MS = 24 * 60 * 60 * 1000;

function parse(deadlineAt) {
  if (!deadlineAt) return null;
  const date = new Date(deadlineAt);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/** { label, urgent, passed } or null. Urgent = due within 3 days. */
export function countdown(deadlineAt, now = new Date()) {
  const deadline = parse(deadlineAt);
  if (!deadline) return null;
  if (deadline <= now) return { label: "Deadline passed", urgent: false, passed: true };
  const days = Math.round((startOfDay(deadline) - startOfDay(now)) / DAY_MS);
  const label = days === 0 ? "Due today" : days === 1 ? "1 day left" : `${days} days left`;
  return { label, urgent: days <= 3, passed: false };
}

/** Soonest upcoming deadline first, then tenders without a date, then passed ones. */
export function sortByDeadline(tenders, now = new Date()) {
  const rank = (t) => {
    const deadline = parse(t.deadline_at);
    if (!deadline) return [1, 0];
    return deadline > now ? [0, deadline.getTime()] : [2, -deadline.getTime()];
  };
  return [...tenders].sort((a, b) => {
    const [ra, ta] = rank(a);
    const [rb, tb] = rank(b);
    return ra - rb || ta - tb;
  });
}
