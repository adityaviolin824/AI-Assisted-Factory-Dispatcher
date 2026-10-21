// Display formats only; the backend values themselves are never rounded or changed.
// A missing value (null or undefined) is shown as "-", never as 0.

export function days(value: number | null | undefined) {
  return value == null ? "-" : value.toFixed(2);
}

export function percent(probability: number | null | undefined) {
  return probability == null ? "-" : `${(probability * 100).toFixed(1)}%`;
}

export function amount(value: number | null | undefined) {
  return value == null ? "-" : value.toFixed(2);
}

export function listText(values: string[]) {
  return values.length ? values.join(", ") : "none";
}

// Chat times in Singapore time, as the chat export writes them ([HH:MM]).
const CHAT_TIME = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Singapore", hour: "2-digit", minute: "2-digit" });
const CHAT_DATE_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Singapore",
  dateStyle: "medium",
  timeStyle: "short",
});

export function chatTime(utc: string) {
  return CHAT_TIME.format(new Date(utc));
}

export function chatDateTime(utc: string) {
  return `${CHAT_DATE_TIME.format(new Date(utc))} Singapore time`;
}
