// Shown in the header masthead. Change this to the firm's name — it's the
// one place the brand name lives, so nothing else needs touching.
export const FIRM_NAME = "Bottini & Bottini, Inc.";

// The ten practice areas, in the same order as the agent prompt's Step 1.
// Must stay in step with intake_fields.CATEGORIES in the backend — the
// backend normalizes anything it doesn't recognize to "other".
export const CATEGORIES = [
  { value: "securities_fraud", label: "Securities Fraud" },
  { value: "shareholder_derivative", label: "Shareholder Derivative" },
  { value: "merger_transaction", label: "Merger / Transaction" },
  { value: "whistleblower_sec", label: "Whistleblower — SEC / CFTC" },
  { value: "whistleblower_qui_tam", label: "Whistleblower — Qui Tam" },
  { value: "whistleblower_retaliation", label: "Whistleblower Retaliation" },
  { value: "consumer_class", label: "Consumer Class" },
  { value: "data_privacy_class", label: "Data Privacy Class" },
  { value: "employment_class", label: "Employment Class" },
  { value: "other", label: "Other" },
];

export const CATEGORY_LABELS = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]));

// Matter type within a practice area, so the dropdown offers only the choices
// that belong to the case's category. Fetched from GET /taxonomy at load
// (see Layout) — this list is the fallback used before that arrives, and
// must stay in step with MATTER_TYPES in the backend's taxonomy.py.
export const SUBCATEGORIES = {
  securities_fraud: [
    { value: "false_misleading_statements", label: "False or Misleading Statements" },
    { value: "financial_restatement", label: "Financial Restatement" },
    { value: "stock_drop_after_disclosure", label: "Stock Drop After Disclosure" },
    { value: "sec_investigation", label: "SEC Investigation" },
    { value: "short_seller_report", label: "Short Seller Report" },
    { value: "bankruptcy", label: "Bankruptcy" },
    { value: "offering_ipo_disclosures", label: "Offering or IPO Disclosures" },
  ],
  shareholder_derivative: [
    { value: "breach_fiduciary_duty", label: "Breach of Fiduciary Duty" },
    { value: "corporate_waste", label: "Corporate Waste" },
    { value: "self_dealing", label: "Self Dealing" },
    { value: "insider_trading", label: "Insider Trading" },
    { value: "excessive_executive_compensation", label: "Excessive Executive Compensation" },
    { value: "board_oversight_failure", label: "Board Oversight Failure" },
  ],
  merger_transaction: [
    { value: "merger", label: "Merger" },
    { value: "buyout", label: "Buyout" },
    { value: "take_private", label: "Take Private" },
    { value: "spac", label: "SPAC" },
    { value: "tender_offer", label: "Tender Offer" },
    { value: "appraisal_rights", label: "Appraisal Rights" },
  ],
  whistleblower_sec: [
    { value: "securities_fraud", label: "Securities Fraud" },
    { value: "accounting_fraud", label: "Accounting Fraud" },
    { value: "fcpa_violations", label: "FCPA Violations" },
    { value: "market_manipulation", label: "Market Manipulation" },
  ],
  whistleblower_qui_tam: [
    { value: "medicare_medicaid_fraud", label: "Medicare or Medicaid Fraud" },
    { value: "defense_contracting_fraud", label: "Defense Contracting Fraud" },
    { value: "grant_fraud", label: "Grant Fraud" },
    { value: "customs_fraud", label: "Customs Fraud" },
  ],
  whistleblower_retaliation: [
    { value: "termination", label: "Termination" },
    { value: "demotion", label: "Demotion" },
    { value: "suspension", label: "Suspension" },
    { value: "blacklisting", label: "Blacklisting" },
    { value: "other_adverse_action", label: "Other Adverse Action" },
  ],
  consumer_class: [
    { value: "false_advertising", label: "False Advertising" },
    { value: "mislabeled_product", label: "Mislabeled Product" },
    { value: "hidden_junk_fees", label: "Hidden or Junk Fees" },
    { value: "auto_renewal_subscription", label: "Auto Renewal or Subscription" },
    { value: "defective_product", label: "Defective Product" },
    { value: "price_fixing", label: "Price Fixing" },
  ],
  data_privacy_class: [
    { value: "data_breach", label: "Data Breach" },
    { value: "unauthorized_sharing_sale", label: "Unauthorized Sharing or Sale" },
    { value: "biometric_privacy", label: "Biometric Privacy" },
    { value: "session_recording_tracking_pixels", label: "Session Recording or Tracking Pixels" },
    { value: "call_text_practices", label: "Call or Text Practices" },
  ],
  employment_class: [
    { value: "unpaid_wages", label: "Unpaid Wages" },
    { value: "unpaid_overtime", label: "Unpaid Overtime" },
    { value: "off_clock_work", label: "Off the Clock Work" },
    { value: "missed_meal_rest_breaks", label: "Missed Meal or Rest Breaks" },
    { value: "misclassification", label: "Misclassification" },
    { value: "unreimbursed_expenses", label: "Unreimbursed Expenses" },
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

// Category values are snake_case in the database; URLs read better in kebab.
// Both directions are pure string swaps, so no lookup table can drift out of
// step with CATEGORIES above.
export const categoryToSlug = (category) => (category || "").replaceAll("_", "-");
export const slugToCategory = (slug) => (slug || "").replaceAll("-", "_");
