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

export const BUCKETS = [
  { key: "cases", label: "Full Cases", description: "Calls where the caller completed intake" },
  { key: "partial-calls", label: "Partial Calls", description: "Calls that disconnected before intake finished" },
  { key: "unwanted-calls", label: "Unwanted Calls", description: "Nonsensical, prank, or unusable calls" },
  { key: "spam-calls", label: "Spam Calls", description: "Caller wouldn't answer the actual intake questions" },
  { key: "emergency-flags", label: "Emergency Flags", description: "Calls where the 911/safety branch fired" },
];
