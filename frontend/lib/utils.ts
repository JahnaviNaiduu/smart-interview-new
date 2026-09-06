import { format, formatDistanceToNow } from "date-fns";

export const TIMEZONES = [
  "UTC", "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
  "America/Toronto", "Europe/London", "Europe/Paris", "Europe/Berlin", "Asia/Kolkata",
  "Asia/Singapore", "Asia/Tokyo", "Asia/Dubai", "Australia/Sydney", "Pacific/Auckland",
];

export const ROUND_TYPES = [
  { value: "screening", label: "Screening" },
  { value: "technical", label: "Technical" },
  { value: "managerial", label: "Managerial" },
  { value: "hr", label: "HR" },
];

export const DURATIONS = [
  { value: 30, label: "30 minutes" },
  { value: 45, label: "45 minutes" },
  { value: 60, label: "60 minutes" },
  { value: 90, label: "90 minutes" },
];

export function formatDateTime(dt: string | Date, tz?: string): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return format(d, "EEE, MMM d yyyy 'at' h:mm a") + " UTC";
}

export function formatDateShort(dt: string | Date): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return format(d, "EEE MMM d, h:mm a");
}

export function formatRelative(dt: string | Date): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return formatDistanceToNow(d, { addSuffix: true });
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: "Pending",
    slots_found: "Slots Found",
    candidate_notified: "Awaiting Candidate",
    booked: "Booked",
    cancelled: "Cancelled",
    rescheduling: "Rescheduling",
  };
  return map[status] || status;
}

export function statusClass(status: string): string {
  const map: Record<string, string> = {
    pending: "badge-pending",
    slots_found: "badge-notified",
    candidate_notified: "badge-notified",
    booked: "badge-booked",
    cancelled: "badge-cancelled",
    rescheduling: "badge-rescheduling",
  };
  return `badge ${map[status] || "badge-pending"}`;
}

export function roundLabel(rt: string): string {
  return rt.charAt(0).toUpperCase() + rt.slice(1);
}

export function scoreBar(score: number | null): string {
  if (score === null) return "";
  const filled = Math.round(score * 5);
  return "●".repeat(filled) + "○".repeat(5 - filled);
}
