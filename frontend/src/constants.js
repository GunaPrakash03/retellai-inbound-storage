export const CATEGORIES = [
  { value: "personal_injury", label: "Personal Injury" },
  { value: "workplace_employment", label: "Workplace & Employment" },
  { value: "medical_product", label: "Medical & Product" },
  { value: "family_law", label: "Family Law" },
  { value: "criminal_defense", label: "Criminal Defense" },
  { value: "immigration", label: "Immigration" },
  { value: "real_estate_housing", label: "Real Estate & Housing" },
  { value: "business_contract", label: "Business & Contract" },
  { value: "estate_disability", label: "Estate & Disability" },
  { value: "other", label: "Other" },
];

export const CATEGORY_LABELS = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]));

export const STATUSES = ["new", "reviewed", "contacted", "closed"];

export const STATUS_LABELS = {
  new: "New",
  reviewed: "Reviewed",
  contacted: "Contacted",
  closed: "Closed",
};

// `table` maps the URL-friendly bucket key to the backend table name that
// /counts reports under.
export const BUCKETS = [
  { key: "cases", table: "cases", label: "Cases", description: "Callers who completed intake" },
  { key: "emergency-flags", table: "emergency_flags", label: "Emergency", description: "The 911/safety branch fired — review first", urgent: true },
  { key: "partial-calls", table: "partial_calls", label: "Partial", description: "Dropped before intake finished" },
  { key: "out-of-scope-calls", table: "out_of_scope_calls", label: "Out of Scope", description: "Reached the wrong business" },
  { key: "unwanted-calls", table: "unwanted_calls", label: "Unwanted", description: "Nonsensical or prank calls" },
  { key: "spam-calls", table: "spam_calls", label: "Spam", description: "Wouldn't answer the questions" },
];

// Non-bucket destinations in the sidebar.
export const VIEWS = {
  MESSAGES: "messages",
  STAFF: "staff",
};
