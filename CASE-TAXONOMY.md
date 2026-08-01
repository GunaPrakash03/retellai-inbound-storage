# Case Taxonomy & LLM Classification

Design for a **three-level** case taxonomy — practice area → case type → subtype
— and an LLM step that classifies each completed call to its most precise match.
Workplace & Employment is fully specified below as the first area; the other
nine practice areas follow the same shape.

Status: **spec only.** Nothing here is wired into the app yet. See "What this
changes" and "Open decisions" at the end before implementing.

---

## The three levels

| Level | Column | Example | Who sets it |
|---|---|---|---|
| Practice area | `case_category` | `workplace_employment` | Retell extraction (exists today) |
| Case type | `case_subcategory` | `wrongful_termination` | Retell extraction (exists today, one level) |
| Subtype | `case_subtype` *(new)* | `constructive_discharge` | **LLM classification step (new)** |

The first two levels already exist in the system (`case_category` and
`case_subcategory`). This taxonomy adds a **third** level — `case_subtype` — and
an LLM pass that fills all three from the call transcript, because a Retell
Selector can't reliably choose from ~300 leaf values in one shot.

---

## Why an LLM step (not just a Retell Selector)

The employment area alone has **25 case types** and **~290 subtypes**. Retell's
post-call Selector extraction works well up to a few dozen options; past that,
accuracy falls off and it starts inventing or truncating values. So:

1. **Retell extraction** picks the *practice area* (10 options) reliably — keep this.
2. A **backend LLM classification step** reads the transcript + the practice area
   and returns the best `case_type` **and** `case_subtype` from the fixed list
   for that area, or `null` when nothing fits well.

### Recommended model & shape

- **Model: Claude Haiku 4.5** (`claude-haiku-4-5`) — $1 / $5 per MTok. This is a
  fixed-taxonomy classification task, the exact use case Haiku is built for.
- **Structured outputs with an enum schema** so the model can only return a
  valid `case_type` / `case_subtype` for the chosen area (no free text, no
  invented values). The enum is generated from the tables below.
- **Batch API** (50% cost) — classification runs on the `call_analyzed` webhook,
  after the call ends, so it is not latency-sensitive. Batches typically finish
  within an hour; for near-real-time, a plain single call is fine and still cheap.
- Cost at Haiku rates for a ~2k-token transcript + ~1k-token taxonomy prompt is a
  fraction of a cent per call; with prompt caching on the (fixed) taxonomy block
  and the Batch API, less still.

The classifier is a single Anthropic API call per completed case. It never
touches the mid-call flow — it runs after the webhook fires, so a slow or failed
classification never affects a live caller. On failure it leaves `case_subtype`
`null` and the case still lands correctly by practice area.

---

## Workplace & Employment — full taxonomy

Practice area value: **`workplace_employment`**

Each case type below is a `case_subcategory` value; each subtype is a
`case_subtype` value. Slugs are derived from the labels by the existing
`_clean_slug` normalizer (lowercase, filler words dropped, spaces → `_`), so the
display label and the stored value stay in sync.

### Hiring & Recruitment — `hiring_recruitment`
- Hiring Discrimination
- Failure to Hire
- Background Check (FCRA) Violations
- Ban-the-Box Violations
- Criminal History Discrimination
- Credit Report Violations
- Drug Testing Disputes
- Pre-Employment Medical Examinations
- Immigration/I-9 Discrimination
- Job Offer Rescission
- Nepotism or Favoritism Claims
- Veteran Hiring Discrimination

### Wrongful Termination — `wrongful_termination`
- Wrongful Termination
- Unlawful Discharge
- Constructive Discharge
- Public Policy Wrongful Termination
- Termination After Protected Leave
- Termination After Reporting Misconduct
- Retaliatory Termination
- Discriminatory Termination
- Termination for Whistleblowing
- Breach of Employment Contract
- At-Will Employment Disputes
- Severance Agreement Disputes

### Employment Discrimination — `employment_discrimination`
- Race Discrimination
- Color Discrimination
- National Origin Discrimination
- Citizenship Discrimination
- Accent Discrimination
- Religious Discrimination
- Failure to Provide Religious Accommodation
- Sex Discrimination
- Pregnancy Discrimination
- Sexual Orientation Discrimination
- Gender Identity Discrimination
- Gender Expression Discrimination
- LGBTQ+ Discrimination
- Disability Discrimination
- Failure to Accommodate Disability
- Medical Condition Discrimination
- Perceived Disability Discrimination
- Age Discrimination
- Genetic Information Discrimination (GINA)
- Marital Status Discrimination
- Family Status Discrimination
- Military Service Discrimination (USERRA)
- Political Affiliation Discrimination
- Victim Status Discrimination
- Off-Duty Conduct Discrimination
- Hairstyle Discrimination (CROWN Act)
- Caregiver Discrimination

### Workplace Harassment — `workplace_harassment`
- Sexual Harassment
- Quid Pro Quo Harassment
- Hostile Work Environment
- Racial Harassment
- Religious Harassment
- Disability Harassment
- Age Harassment
- National Origin Harassment
- LGBTQ+ Harassment
- Workplace Bullying
- Cyber Harassment
- Supervisor Harassment
- Coworker Harassment
- Third-Party Harassment

### Retaliation — `retaliation`
- EEOC Retaliation
- OSHA Retaliation
- FMLA Retaliation
- ADA Retaliation
- Wage Complaint Retaliation
- Workers' Compensation Retaliation
- Union Retaliation
- Whistleblower Retaliation
- Internal Complaint Retaliation
- Jury Duty Retaliation
- Military Leave Retaliation
- Voting Leave Retaliation

### Wage & Hour — `wage_hour`
- Unpaid Wages
- Unpaid Overtime
- Minimum Wage Violations
- Off-the-Clock Work
- Time Rounding Violations
- Meal Break Violations
- Rest Break Violations
- Tip Pooling Disputes
- Tip Theft
- Payroll Deduction Disputes
- Final Paycheck Disputes
- Commission Disputes
- Bonus Disputes
- Employee Misclassification (Exempt/Non-Exempt)
- Independent Contractor Misclassification
- Payroll Record Violations
- Wage Theft
- Child Labor Violations

### Employee Benefits (ERISA) — `employee_benefits_erisa`
- Pension Disputes
- 401(k) Disputes
- Health Insurance Denial
- COBRA Violations
- Disability Benefit Denial
- Retirement Benefit Disputes
- Fiduciary Breach
- Life Insurance Benefit Disputes
- Stock Option Disputes
- Employee Stock Ownership Plan (ESOP) Disputes

### Leave Rights — `leave_rights`
- FMLA Violations
- Family Leave Denial
- Medical Leave Denial
- Pregnancy Leave Disputes
- Military Leave
- Jury Duty Leave
- Voting Leave
- Paid Sick Leave Violations
- State Family Leave Claims
- Bereavement Leave Disputes

### Disability & Accommodation — `disability_accommodation`
- ADA Violations
- Failure to Accommodate
- Interactive Process Failure
- Mental Health Accommodation
- Religious Accommodation
- Pregnancy Accommodation
- Remote Work Accommodation
- Medical Leave Accommodation

### Workplace Safety — `workplace_safety`
- OSHA Violations
- Unsafe Workplace
- Chemical Exposure
- Toxic Exposure
- Construction Safety
- Workplace Violence
- Workplace Injury
- Fatal Workplace Accidents
- Heat Illness Claims
- COVID-19 Workplace Issues
- Personal Protective Equipment (PPE) Violations

### Workers' Compensation — `workers_compensation`
- Workplace Injury Claims
- Occupational Disease
- Repetitive Stress Injury
- Temporary Disability
- Permanent Disability
- Workers' Compensation Retaliation
- Benefit Denial
- Medical Treatment Disputes
- Death Benefits

### Whistleblower — `whistleblower`
- False Claims Act
- SEC Whistleblower
- OSHA Whistleblower
- Healthcare Fraud Reporting
- Medicare Fraud
- Medicaid Fraud
- Financial Fraud
- Environmental Violations
- Tax Fraud
- Government Contractor Fraud
- Sarbanes-Oxley Claims
- Dodd-Frank Claims
- Corporate Misconduct Reporting

### Employment Contracts — `employment_contracts`
- Employment Agreement Disputes
- Executive Employment Contracts
- Offer Letter Disputes
- Breach of Employment Contract
- Severance Agreement Disputes
- Arbitration Agreement Disputes
- Confidentiality Agreement Disputes
- Employment Handbook Disputes
- Implied Employment Contract

### Restrictive Covenants — `restrictive_covenants`
- Non-Compete Agreements
- Non-Solicitation Agreements
- Non-Disclosure Agreements (NDA)
- Trade Secret Misappropriation
- Confidential Information Theft
- Customer Solicitation
- Employee Solicitation

### Labor Union — `labor_union`
- Collective Bargaining Disputes
- Union Elections
- Union Organizing
- Unfair Labor Practices
- Duty of Fair Representation
- Union Discipline
- Strike Disputes
- Lockout Disputes
- Grievance Arbitration

### Privacy & Technology — `privacy_technology`
- Employee Monitoring
- Email Monitoring
- GPS Tracking
- Biometric Privacy (BIPA)
- Workplace Surveillance
- Data Privacy
- Social Media Discipline
- Recording in the Workplace
- AI Monitoring
- Electronic Communications Privacy

### Immigration Employment — `immigration_employment`
- Work Visa Disputes
- H-1B Employment Issues
- H-2A Employment Issues
- H-2B Employment Issues
- Green Card Sponsorship Disputes
- I-9 Compliance
- E-Verify Disputes
- Immigration Retaliation
- Document Abuse

### Equal Pay — `equal_pay`
- Equal Pay Act Claims
- Gender Pay Discrimination
- Salary Transparency Violations
- Compensation Discrimination
- Wage Discrimination

### Workplace Torts — `workplace_torts`
- Defamation
- Assault
- Battery
- False Imprisonment
- Intentional Infliction of Emotional Distress
- Negligent Hiring
- Negligent Supervision
- Negligent Retention
- Invasion of Privacy
- Fraud
- Misrepresentation

### Layoffs & Reductions — `layoffs_reductions`
- WARN Act Violations
- Mass Layoffs
- Plant Closures
- Reduction in Force (RIF) Discrimination
- Recall Rights
- Seniority Disputes

### Executive Employment — `executive_employment`
- Executive Compensation
- Golden Parachutes
- Deferred Compensation
- Equity Compensation
- Stock Options
- Change-in-Control Agreements

### Gig Economy & Independent Contractors — `gig_economy_independent_contractors`
- Gig Worker Classification
- Independent Contractor Classification
- Freelancer Pay Disputes
- Joint Employer Liability

### Public Sector Employment — `public_sector_employment`
- Civil Service Disputes
- Government Employee Discipline
- First Amendment Retaliation
- Public Employee Due Process
- Police Employment Disputes
- Teacher Employment Disputes

### Industry-Specific Employment — `industry_specific_employment`
- Healthcare Employment
- Construction Employment
- Restaurant Employment
- Hospitality Employment
- Retail Employment
- Manufacturing Employment
- Transportation Employment
- Technology Employment
- Agricultural Employment

### Miscellaneous Employment Claims — `miscellaneous_employment_claims`
- Blacklisting
- Personnel File Disputes
- Employment References
- Background Investigation Disputes
- Workplace Bullying
- Workplace Romance Disputes
- Moonlighting Disputes
- Dress Code Disputes
- Grooming Policy Disputes
- Attendance Policy Disputes
- Remote Work Disputes
- Return-to-Office Disputes
- AI-Related Employment Disputes

---

## Classification prompt (sketch)

Per completed case, one call to `claude-haiku-4-5` with structured output:

- **System / cached prefix:** "You classify a US legal intake call into a fixed
  taxonomy. Given the transcript and the practice area, choose the single best
  `case_type` and `case_subtype`. If none fits well, return null for that field.
  Do not invent values." + the taxonomy for the given practice area.
- **User:** the call transcript + `case_category`.
- **Output schema (enum-constrained):**
  ```json
  {
    "type": "object",
    "properties": {
      "case_type":    { "type": ["string", "null"], "enum": [ ...types for area..., null ] },
      "case_subtype": { "type": ["string", "null"], "enum": [ ...subtypes for area..., null ] },
      "confidence":   { "type": "number" }
    },
    "required": ["case_type", "case_subtype", "confidence"]
  }
  ```
- Validate on return: the chosen `case_subtype` must belong to the chosen
  `case_type`; drop it if not. Store `null` below a confidence threshold so a
  weak guess doesn't mislabel a case.

---

## What this changes (implementation checklist)

Backend:
- [ ] Add `case_subtype` column (nullable) to every bucket table via the existing
      `_NEW_COLUMNS` migration.
- [ ] Add `VALID_SUBTYPES` to `validators.py` keyed by `(category, case_type)`,
      plus a `normalize_subtype()` that validates against the chosen type.
- [ ] Add the classifier (`app/classify.py`): one `claude-haiku-4-5` call with an
      enum schema built from the taxonomy; called from the `call_analyzed` webhook
      after `upsert_record`. Needs `ANTHROPIC_API_KEY` in the backend env.
- [ ] Make `case_subtype` staff-editable in `update_record_fields` (same pattern
      as `case_subcategory`), and protected from webhook overwrite once corrected.

Frontend:
- [ ] `SUBTYPES` map in `constants.js` keyed by `(category, subcategory)`.
- [ ] Show subtype under the matter type in the case detail + the practice-area
      list; add a subtype filter column.

Retell:
- [ ] No new Selector field needed for subtype — the LLM step fills it. Keep the
      existing `case_category` and (optionally) `case_subcategory` Selectors as a
      cheap first pass the classifier can refine.

---

## Open decisions

1. **The other nine practice areas.** This file specifies employment only. Each
   other area (personal injury, family law, criminal defense, immigration, real
   estate, business, medical, estate, other) needs the same case-type/subtype
   breakdown before its classification is meaningful. Provide those lists, or I
   can draft them for review — they should be attorney-checked before shipping.
2. **Anthropic API key on the backend.** The classifier needs `ANTHROPIC_API_KEY`
   set in the Railway backend env. Batch vs. single call is a cost/latency choice
   (batch = 50% cheaper, up to ~1h; single = instant, still cheap).
3. **Re-classify existing cases?** A one-off backfill can classify the cases
   already in the database, or we can classify new calls only.
4. **Confidence threshold** for storing a subtype vs. leaving it null.
