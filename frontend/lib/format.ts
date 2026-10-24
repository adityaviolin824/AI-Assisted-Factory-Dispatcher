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

// "1 message", "2 messages".
export function count(number: number, noun: string) {
  return `${number} ${noun}${number === 1 ? "" : "s"}`;
}

// Chat times in Singapore time, as the chat export writes them ([HH:MM]).
const CHAT_TIME = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Singapore", hour: "2-digit", minute: "2-digit" });
const CHAT_DATE_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Singapore",
  dateStyle: "medium",
  timeStyle: "short",
});

// A calendar date such as "2026-04-01", shown as "1 April 2026". It has no time of day, so it is read
// and shown in UTC, which keeps it from moving to the day before in any time zone.
const CALENDAR_DATE = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", dateStyle: "long" });

export function calendarDate(isoDate: string) {
  return CALENDAR_DATE.format(new Date(isoDate));
}

export function chatTime(utc: string) {
  return CHAT_TIME.format(new Date(utc));
}

export function chatDateTime(utc: string) {
  return `${CHAT_DATE_TIME.format(new Date(utc))} Singapore time`;
}
