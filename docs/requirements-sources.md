# Requirements Sources

## Scope
This document records the authoritative sources used to derive SC DMV registration
requirements for the **private-party vehicle purchase** scenario (York County, SC).

**Status as of initial scaffold: All entries are PROVISIONAL.**
They must be verified against current official SCDMV publications before the
prototype is presented as accurately reflecting real requirements.

---

## Supported Scenario
**Registering a previously-titled South Carolina vehicle purchased from a private seller
in York County, SC.**

---

## Sources Consulted

| # | Source | URL | Retrieval Date | Verified? | Notes |
|---|--------|-----|----------------|-----------|-------|
| 1 | SCDMV Official Website | https://www.scdmvonline.com | PROVISIONAL | ❌ | Primary source — must be checked |
| 2 | SCDMV Title Transfer | https://www.scdmvonline.com/Vehicle-Owners/Titles/Title-Transfer | PROVISIONAL | ❌ | Title transfer requirements |
| 3 | SCDMV Form 400 | https://www.scdmvonline.com/DMV-Forms/DMV-400 | PROVISIONAL | ❌ | Application for Certificate of Title |
| 4 | York County Treasurer | https://www.yorkcountygov.com/195/Treasurer | PROVISIONAL | ❌ | Property tax payment |
| 5 | Rock Hill SCDMV Office | https://www.scdmvonline.com/SC-DMV-Locations/Rock-Hill | PROVISIONAL | ❌ | Location and hours |

---

## Rule Mappings

### Required Documents (provisional)

| Requirement Key | Rule | Condition | Source # |
|----------------|------|-----------|----------|
| `current_title` | Seller must sign the Assignment of Title | Always required | 2 |
| `bill_of_sale` | Signed bill of sale with VIN, price, date, parties | Always required | 2 |
| `photo_id` | Valid government-issued photo ID of buyer | Always required | 2 |
| `proof_of_insurance` | Valid SC liability insurance | Always required | 2 |
| `tax_receipt` | York County property tax receipt / paid notice | Always required | 4 |
| `odometer_disclosure` | Odometer disclosure statement | Vehicles < 10 years old | 2 |
| `lien_release` | Lien release from lienholder | Only if active lien on title | 2 |

### Key Forms (provisional)

| Form Key | Form Number | Description | Source # |
|----------|-------------|-------------|----------|
| `form_400` | SCDMV Form 400 | Application for Certificate of Title | 1, 3 |

---

## Fee Estimates (provisional — NOT verified)

| Fee | Estimated Amount | Source | Notes |
|-----|-----------------|--------|-------|
| Title fee | ~$15.00 | PROVISIONAL | Must verify at scdmvonline.com |
| Registration fee | ~$40.00 | PROVISIONAL | Varies by vehicle |
| County road fee | ~$5.00 | PROVISIONAL | York County |

**These figures are placeholders for demo display only. They must be verified
against current official fee schedules before use in any public-facing capacity.**

---

## Verification TODO

Before presenting this prototype as an accurate reflection of SCDMV requirements:

- [ ] Confirm Form 400 is still the correct form for private-party title transfer
- [ ] Confirm all required supporting documents against current SCDMV website
- [ ] Confirm odometer disclosure threshold (10 years) from federal/state rules
- [ ] Verify fee amounts from current official fee schedule
- [ ] Confirm York County tax receipt is required before DMV registration
- [ ] Verify Rock Hill office address and hours
- [ ] Record exact retrieval dates for all sources

---

## Disclaimer

This prototype is an educational tool for the IBM SkillsBuild AI Experiential Learning Lab.
It is not affiliated with the SCDMV or York County. Requirements, forms, fees, and links
are based on provisional research and may not reflect current official rules.
Users must verify all requirements at scdmvonline.com before visiting a DMV office.
