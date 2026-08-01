"""The case taxonomy — practice area -> case type -> subtype.

Fully specified for Workplace & Employment (the pilot area). Labels are the
source of truth; the machine value (slug) for each is derived from the label by
`slugify`, so the display label and the stored value can never drift apart.

Kept dependency-free (only `re`) so `validators` can import it without a cycle —
`validators` and `db` import from here, never the other way around.
"""
import re

# Dropped when slugifying so a human label and a stored value collapse to the
# same thing: "Wage & Hour" and "wage_hour" both become "wage_hour".
_SLUG_STOPWORDS = {"and", "or", "of", "the", "a", "an"}


def slugify(value: str) -> str:
    """Collapse a label to snake_case, dropping filler words and punctuation:
    "Employee Benefits (ERISA)" -> "employee_benefits_erisa"."""
    tokens = re.split(r"[^a-z0-9]+", value.lower())
    kept = [t for t in tokens if t and t not in _SLUG_STOPWORDS]
    return "_".join(kept)


EMPLOYMENT_CATEGORY = "workplace_employment"

# case-type label -> list of subtype labels. See CASE-TAXONOMY.md. Slugs for
# both levels are derived from these labels by slugify().
_EMPLOYMENT: dict[str, list[str]] = {
    "Hiring & Recruitment": [
        "Hiring Discrimination", "Failure to Hire",
        "Background Check (FCRA) Violations", "Ban-the-Box Violations",
        "Criminal History Discrimination", "Credit Report Violations",
        "Drug Testing Disputes", "Pre-Employment Medical Examinations",
        "Immigration/I-9 Discrimination", "Job Offer Rescission",
        "Nepotism or Favoritism Claims", "Veteran Hiring Discrimination",
    ],
    "Wrongful Termination": [
        "Wrongful Termination", "Unlawful Discharge", "Constructive Discharge",
        "Public Policy Wrongful Termination", "Termination After Protected Leave",
        "Termination After Reporting Misconduct", "Retaliatory Termination",
        "Discriminatory Termination", "Termination for Whistleblowing",
        "Breach of Employment Contract", "At-Will Employment Disputes",
        "Severance Agreement Disputes",
    ],
    "Employment Discrimination": [
        "Race Discrimination", "Color Discrimination",
        "National Origin Discrimination", "Citizenship Discrimination",
        "Accent Discrimination", "Religious Discrimination",
        "Failure to Provide Religious Accommodation", "Sex Discrimination",
        "Pregnancy Discrimination", "Sexual Orientation Discrimination",
        "Gender Identity Discrimination", "Gender Expression Discrimination",
        "LGBTQ+ Discrimination", "Disability Discrimination",
        "Failure to Accommodate Disability", "Medical Condition Discrimination",
        "Perceived Disability Discrimination", "Age Discrimination",
        "Genetic Information Discrimination (GINA)",
        "Marital Status Discrimination", "Family Status Discrimination",
        "Military Service Discrimination (USERRA)",
        "Political Affiliation Discrimination", "Victim Status Discrimination",
        "Off-Duty Conduct Discrimination", "Hairstyle Discrimination (CROWN Act)",
        "Caregiver Discrimination",
    ],
    "Workplace Harassment": [
        "Sexual Harassment", "Quid Pro Quo Harassment",
        "Hostile Work Environment", "Racial Harassment", "Religious Harassment",
        "Disability Harassment", "Age Harassment", "National Origin Harassment",
        "LGBTQ+ Harassment", "Workplace Bullying", "Cyber Harassment",
        "Supervisor Harassment", "Coworker Harassment", "Third-Party Harassment",
    ],
    "Retaliation": [
        "EEOC Retaliation", "OSHA Retaliation", "FMLA Retaliation",
        "ADA Retaliation", "Wage Complaint Retaliation",
        "Workers' Compensation Retaliation", "Union Retaliation",
        "Whistleblower Retaliation", "Internal Complaint Retaliation",
        "Jury Duty Retaliation", "Military Leave Retaliation",
        "Voting Leave Retaliation",
    ],
    "Wage & Hour": [
        "Unpaid Wages", "Unpaid Overtime", "Minimum Wage Violations",
        "Off-the-Clock Work", "Time Rounding Violations", "Meal Break Violations",
        "Rest Break Violations", "Tip Pooling Disputes", "Tip Theft",
        "Payroll Deduction Disputes", "Final Paycheck Disputes",
        "Commission Disputes", "Bonus Disputes",
        "Employee Misclassification (Exempt/Non-Exempt)",
        "Independent Contractor Misclassification", "Payroll Record Violations",
        "Wage Theft", "Child Labor Violations",
    ],
    "Employee Benefits (ERISA)": [
        "Pension Disputes", "401(k) Disputes", "Health Insurance Denial",
        "COBRA Violations", "Disability Benefit Denial",
        "Retirement Benefit Disputes", "Fiduciary Breach",
        "Life Insurance Benefit Disputes", "Stock Option Disputes",
        "Employee Stock Ownership Plan (ESOP) Disputes",
    ],
    "Leave Rights": [
        "FMLA Violations", "Family Leave Denial", "Medical Leave Denial",
        "Pregnancy Leave Disputes", "Military Leave", "Jury Duty Leave",
        "Voting Leave", "Paid Sick Leave Violations", "State Family Leave Claims",
        "Bereavement Leave Disputes",
    ],
    "Disability & Accommodation": [
        "ADA Violations", "Failure to Accommodate", "Interactive Process Failure",
        "Mental Health Accommodation", "Religious Accommodation",
        "Pregnancy Accommodation", "Remote Work Accommodation",
        "Medical Leave Accommodation",
    ],
    "Workplace Safety": [
        "OSHA Violations", "Unsafe Workplace", "Chemical Exposure",
        "Toxic Exposure", "Construction Safety", "Workplace Violence",
        "Workplace Injury", "Fatal Workplace Accidents", "Heat Illness Claims",
        "COVID-19 Workplace Issues",
        "Personal Protective Equipment (PPE) Violations",
    ],
    "Workers' Compensation": [
        "Workplace Injury Claims", "Occupational Disease",
        "Repetitive Stress Injury", "Temporary Disability",
        "Permanent Disability", "Workers' Compensation Retaliation",
        "Benefit Denial", "Medical Treatment Disputes", "Death Benefits",
    ],
    "Whistleblower": [
        "False Claims Act", "SEC Whistleblower", "OSHA Whistleblower",
        "Healthcare Fraud Reporting", "Medicare Fraud", "Medicaid Fraud",
        "Financial Fraud", "Environmental Violations", "Tax Fraud",
        "Government Contractor Fraud", "Sarbanes-Oxley Claims",
        "Dodd-Frank Claims", "Corporate Misconduct Reporting",
    ],
    "Employment Contracts": [
        "Employment Agreement Disputes", "Executive Employment Contracts",
        "Offer Letter Disputes", "Breach of Employment Contract",
        "Severance Agreement Disputes", "Arbitration Agreement Disputes",
        "Confidentiality Agreement Disputes", "Employment Handbook Disputes",
        "Implied Employment Contract",
    ],
    "Restrictive Covenants": [
        "Non-Compete Agreements", "Non-Solicitation Agreements",
        "Non-Disclosure Agreements (NDA)", "Trade Secret Misappropriation",
        "Confidential Information Theft", "Customer Solicitation",
        "Employee Solicitation",
    ],
    "Labor Union": [
        "Collective Bargaining Disputes", "Union Elections", "Union Organizing",
        "Unfair Labor Practices", "Duty of Fair Representation",
        "Union Discipline", "Strike Disputes", "Lockout Disputes",
        "Grievance Arbitration",
    ],
    "Privacy & Technology": [
        "Employee Monitoring", "Email Monitoring", "GPS Tracking",
        "Biometric Privacy (BIPA)", "Workplace Surveillance", "Data Privacy",
        "Social Media Discipline", "Recording in the Workplace", "AI Monitoring",
        "Electronic Communications Privacy",
    ],
    "Immigration Employment": [
        "Work Visa Disputes", "H-1B Employment Issues", "H-2A Employment Issues",
        "H-2B Employment Issues", "Green Card Sponsorship Disputes",
        "I-9 Compliance", "E-Verify Disputes", "Immigration Retaliation",
        "Document Abuse",
    ],
    "Equal Pay": [
        "Equal Pay Act Claims", "Gender Pay Discrimination",
        "Salary Transparency Violations", "Compensation Discrimination",
        "Wage Discrimination",
    ],
    "Workplace Torts": [
        "Defamation", "Assault", "Battery", "False Imprisonment",
        "Intentional Infliction of Emotional Distress", "Negligent Hiring",
        "Negligent Supervision", "Negligent Retention", "Invasion of Privacy",
        "Fraud", "Misrepresentation",
    ],
    "Layoffs & Reductions": [
        "WARN Act Violations", "Mass Layoffs", "Plant Closures",
        "Reduction in Force (RIF) Discrimination", "Recall Rights",
        "Seniority Disputes",
    ],
    "Executive Employment": [
        "Executive Compensation", "Golden Parachutes", "Deferred Compensation",
        "Equity Compensation", "Stock Options", "Change-in-Control Agreements",
    ],
    "Gig Economy & Independent Contractors": [
        "Gig Worker Classification", "Independent Contractor Classification",
        "Freelancer Pay Disputes", "Joint Employer Liability",
    ],
    "Public Sector Employment": [
        "Civil Service Disputes", "Government Employee Discipline",
        "First Amendment Retaliation", "Public Employee Due Process",
        "Police Employment Disputes", "Teacher Employment Disputes",
    ],
    "Industry-Specific Employment": [
        "Healthcare Employment", "Construction Employment",
        "Restaurant Employment", "Hospitality Employment", "Retail Employment",
        "Manufacturing Employment", "Transportation Employment",
        "Technology Employment", "Agricultural Employment",
    ],
    "Miscellaneous Employment Claims": [
        "Blacklisting", "Personnel File Disputes", "Employment References",
        "Background Investigation Disputes", "Workplace Bullying",
        "Workplace Romance Disputes", "Moonlighting Disputes",
        "Dress Code Disputes", "Grooming Policy Disputes",
        "Attendance Policy Disputes", "Remote Work Disputes",
        "Return-to-Office Disputes", "AI-Related Employment Disputes",
    ],
}

# Built lookups (slug-keyed) derived once at import.
# case_type slug -> label
EMPLOYMENT_TYPE_LABELS: dict[str, str] = {
    slugify(t): t for t in _EMPLOYMENT
}
# case_type slug -> list of (subtype_slug, subtype_label)
EMPLOYMENT_SUBTYPES: dict[str, list[tuple[str, str]]] = {
    slugify(t): [(slugify(s), s) for s in subs] for t, subs in _EMPLOYMENT.items()
}
# ordered [(type_slug, type_label)] for the UI, in the taxonomy's own order
EMPLOYMENT_TYPES: list[tuple[str, str]] = [
    (slugify(t), t) for t in _EMPLOYMENT
]
# flat subtype_slug -> label, for display where the type isn't handy
SUBTYPE_LABELS: dict[str, str] = {
    slug: label
    for subs in EMPLOYMENT_SUBTYPES.values()
    for slug, label in subs
}


def subtypes_for(category: str | None, case_type: str | None) -> list[tuple[str, str]]:
    """(subtype_slug, label) pairs valid under a category + case type."""
    if category != EMPLOYMENT_CATEGORY:
        return []
    return EMPLOYMENT_SUBTYPES.get(case_type or "", [])


# Matter types (case_subcategory) for the nine non-employment areas, as
# (slug, label). Slugs match validators.VALID_SUBCATEGORIES exactly — some
# keep stopwords (breach_of_contract, slip_and_fall), so they're written out
# here rather than derived from the label. These already drive the dashboard
# and Retell extraction; the classifier reuses them to fill the matter type
# from the transcript when Retell didn't. Employment's 25 types are separate
# (EMPLOYMENT_TYPES). No subtypes for these areas yet — see CASE-TAXONOMY.md.
NON_EMPLOYMENT_SUBCATEGORIES: dict[str, list[tuple[str, str]]] = {
    "personal_injury": [
        ("car_accident", "Car Accident"),
        ("motorcycle_accident", "Motorcycle Accident"),
        ("truck_accident", "Truck Accident"),
        ("pedestrian_bicycle_accident", "Pedestrian / Bicycle Accident"),
        ("slip_and_fall", "Slip and Fall"),
        ("dog_bite", "Dog Bite"),
        ("wrongful_death", "Wrongful Death"),
        ("boating_accident", "Boating Accident"),
    ],
    "medical_product": [
        ("medical_malpractice", "Medical Malpractice"),
        ("defective_product", "Defective Product"),
        ("dangerous_drug_device", "Dangerous Drug / Device"),
    ],
    "family_law": [
        ("divorce", "Divorce"),
        ("child_custody_visitation", "Child Custody and Visitation"),
        ("child_support", "Child Support"),
        ("paternity", "Paternity"),
        ("adoption_guardianship", "Adoption and Guardianship"),
        ("domestic_violence_protection", "Domestic Violence Protection"),
        ("emancipation_name_changes", "Emancipation and Name Changes"),
    ],
    "criminal_defense": [
        ("dui_dwi", "DUI / DWI"),
        ("misdemeanor", "Misdemeanor"),
        ("felony", "Felony"),
        ("traffic_violation", "Traffic Violation"),
        ("juvenile", "Juvenile"),
    ],
    "immigration": [
        ("visa", "Visa"),
        ("green_card", "Green Card"),
        ("deportation_removal", "Deportation / Removal"),
        ("asylum", "Asylum"),
        ("citizenship_naturalization", "Citizenship / Naturalization"),
    ],
    "real_estate_housing": [
        ("landlord_tenant", "Landlord–Tenant"),
        ("eviction", "Eviction"),
        ("purchase_sale_dispute", "Purchase / Sale Dispute"),
        ("foreclosure", "Foreclosure"),
    ],
    "business_contract": [
        ("breach_of_contract", "Breach of Contract"),
        ("partnership_dispute", "Partnership Dispute"),
        ("debt_collection", "Debt Collection"),
    ],
    "estate_disability": [
        ("estate_planning", "Estate Planning"),
        ("probate", "Probate"),
        ("social_security_disability", "Social Security Disability"),
        ("veterans_benefits", "Veterans Benefits"),
    ],
}


def subcategory_choices(category: str | None) -> list[tuple[str, str]]:
    """(slug, label) matter-type options for a category — employment's 25
    types or a non-employment area's list. Empty for 'other' / unknown."""
    if category == EMPLOYMENT_CATEGORY:
        return list(EMPLOYMENT_TYPES)
    return NON_EMPLOYMENT_SUBCATEGORIES.get(category or "", [])
