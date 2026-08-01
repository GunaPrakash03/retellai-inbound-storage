// Shown in the header masthead. Change this to the firm's name — it's the
// one place the brand name lives, so nothing else needs touching.
export const FIRM_NAME = "Law Office of [Your Firm]";

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

// Finer-grained matter type within a category. Keyed by category value, so
// the subcategory dropdown can offer only the choices that belong to the
// case's category. Must stay in step with VALID_SUBCATEGORIES in the
// backend's validators.py — the backend rejects any value not on its list.
export const SUBCATEGORIES = {
  personal_injury: [
    { value: "car_accident", label: "Car Accident" },
    { value: "motorcycle_accident", label: "Motorcycle Accident" },
    { value: "truck_accident", label: "Truck Accident" },
    { value: "pedestrian_bicycle_accident", label: "Pedestrian / Bicycle Accident" },
    { value: "slip_and_fall", label: "Slip and Fall" },
    { value: "dog_bite", label: "Dog Bite" },
    { value: "wrongful_death", label: "Wrongful Death" },
    { value: "boating_accident", label: "Boating Accident" },
  ],
  // The 25 employment case types (full taxonomy). Their subtypes (third level)
  // are fetched from GET /taxonomy rather than duplicated here — see api.getTaxonomy.
  workplace_employment: [
    { value: "hiring_recruitment", label: "Hiring & Recruitment" },
    { value: "wrongful_termination", label: "Wrongful Termination" },
    { value: "employment_discrimination", label: "Employment Discrimination" },
    { value: "workplace_harassment", label: "Workplace Harassment" },
    { value: "retaliation", label: "Retaliation" },
    { value: "wage_hour", label: "Wage & Hour" },
    { value: "employee_benefits_erisa", label: "Employee Benefits (ERISA)" },
    { value: "leave_rights", label: "Leave Rights" },
    { value: "disability_accommodation", label: "Disability & Accommodation" },
    { value: "workplace_safety", label: "Workplace Safety" },
    { value: "workers_compensation", label: "Workers' Compensation" },
    { value: "whistleblower", label: "Whistleblower" },
    { value: "employment_contracts", label: "Employment Contracts" },
    { value: "restrictive_covenants", label: "Restrictive Covenants" },
    { value: "labor_union", label: "Labor Union" },
    { value: "privacy_technology", label: "Privacy & Technology" },
    { value: "immigration_employment", label: "Immigration Employment" },
    { value: "equal_pay", label: "Equal Pay" },
    { value: "workplace_torts", label: "Workplace Torts" },
    { value: "layoffs_reductions", label: "Layoffs & Reductions" },
    { value: "executive_employment", label: "Executive Employment" },
    { value: "gig_economy_independent_contractors", label: "Gig Economy & Independent Contractors" },
    { value: "public_sector_employment", label: "Public Sector Employment" },
    { value: "industry_specific_employment", label: "Industry-Specific Employment" },
    { value: "miscellaneous_employment_claims", label: "Miscellaneous Employment Claims" },
  ],
  medical_product: [
    { value: "medical_malpractice", label: "Medical Malpractice" },
    { value: "defective_product", label: "Defective Product" },
    { value: "dangerous_drug_device", label: "Dangerous Drug / Device" },
  ],
  family_law: [
    { value: "divorce", label: "Divorce" },
    { value: "child_custody_visitation", label: "Child Custody and Visitation" },
    { value: "child_support", label: "Child Support" },
    { value: "paternity", label: "Paternity" },
    { value: "adoption_guardianship", label: "Adoption and Guardianship" },
    { value: "domestic_violence_protection", label: "Domestic Violence Protection" },
    { value: "emancipation_name_changes", label: "Emancipation and Name Changes" },
  ],
  criminal_defense: [
    { value: "dui_dwi", label: "DUI / DWI" },
    { value: "misdemeanor", label: "Misdemeanor" },
    { value: "felony", label: "Felony" },
    { value: "traffic_violation", label: "Traffic Violation" },
    { value: "juvenile", label: "Juvenile" },
  ],
  immigration: [
    { value: "visa", label: "Visa" },
    { value: "green_card", label: "Green Card" },
    { value: "deportation_removal", label: "Deportation / Removal" },
    { value: "asylum", label: "Asylum" },
    { value: "citizenship_naturalization", label: "Citizenship / Naturalization" },
  ],
  real_estate_housing: [
    { value: "landlord_tenant", label: "Landlord–Tenant" },
    { value: "eviction", label: "Eviction" },
    { value: "purchase_sale_dispute", label: "Purchase / Sale Dispute" },
    { value: "foreclosure", label: "Foreclosure" },
  ],
  business_contract: [
    { value: "breach_of_contract", label: "Breach of Contract" },
    { value: "partnership_dispute", label: "Partnership Dispute" },
    { value: "debt_collection", label: "Debt Collection" },
  ],
  estate_disability: [
    { value: "estate_planning", label: "Estate Planning" },
    { value: "probate", label: "Probate" },
    { value: "social_security_disability", label: "Social Security Disability" },
    { value: "veterans_benefits", label: "Veterans Benefits" },
  ],
};

// Flat value -> label across every category, for read-only display where the
// category context isn't handy.
export const SUBCATEGORY_LABELS = Object.fromEntries(
  Object.values(SUBCATEGORIES).flat().map((s) => [s.value, s.label]),
);

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
