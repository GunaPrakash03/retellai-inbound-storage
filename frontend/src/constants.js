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
