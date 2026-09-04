// Single source of truth for the business identity shown on the
// legally required Impressum and Datenschutzerklärung pages. Replace
// every bracketed placeholder with the real, verified details before
// this goes live -- an incomplete or inaccurate Impressum is a real
// Abmahnung risk under § 5 DDG, and getting the controller's identity
// wrong on the privacy policy undermines it as a valid Art. 13 DSGVO
// notice.
//
// This file intentionally holds ONLY the identity/contact facts that
// are the operator's to supply. It is not a substitute for review by
// a lawyer (Fachanwalt für IT-Recht / Datenschutzrecht) -- especially
// for a product that processes taxpayers' full financial and tax
// data and transmits it to the Finanzamt.

// STATUS: the operator's identity and contact details below are real and
// supplied by the operator. Two things are still outstanding before this
// product should be taking money from real filers:
//   1. legalForm is empty because NO Gewerbe has been registered yet, and
//      the site charges EUR 34,90 live. A paid service is commercial
//      trading; the Impressum must not imply a business that does not
//      exist, so the line is omitted rather than guessed (see
//      impressum/page.tsx's hasLegalForm).
//   2. Neither this page nor datenschutz/page.tsx has been reviewed by a
//      lawyer, which matters more than usual here -- see the note above.
export const LEGAL_INFO = {
  operatorName: "Patrick Thompson",
  legalForm: "[z. B. Einzelunternehmen / Kleingewerbe / GmbH]",
  representedBy: "[Vertretungsberechtigte Person -- nur bei juristischer Person nötig]",
  street: "Sewanstraße 179",
  postalCode: "10319",
  city: "Berlin",
  country: "Deutschland",
  email: "pattson22@gmail.com",
  phone: "+49 15563170243",
  registerCourt: "[Registergericht -- nur bei Handelsregistereintrag]",
  registerNumber: "[Registernummer -- nur bei Handelsregistereintrag]",
  vatId: "[USt-IdNr. -- falls vorhanden]",
  supervisoryAuthority: "Berliner Beauftragte für Datenschutz und Informationsfreiheit",
  // Real, verified technical facts (Railway project configuration) --
  // unlike the placeholders above, these are not the operator's to fill
  // in, so they're filled in here directly.
  //
  // Hosting and the database moved from Railway's San Francisco region to
  // EU West (Amsterdam, europe-west4-drams3a) on 2026-09-04, verified by
  // reading each service's deployed region back afterwards; the Postgres
  // volume was migrated with it. Compute, database and object storage are
  // therefore all in the EU now.
  //
  // That does NOT make section 9's Drittland/EU-SCC sentence in
  // datenschutz/page.tsx removable, and it was deliberately left in place:
  // Stripe remains a US-headquartered payment processor, so a third-country
  // transfer still occurs on that path. What changed is that hosting is no
  // longer one of the reasons -- which is a narrowing, not an elimination,
  // and whether the wording should change at all is a lawyer's call, not an
  // inference from this file. Section 9 is phrased conditionally
  // ("nur, soweit einer der genannten Anbieter dort verarbeitet"), so it
  // stays accurate either way.
  documentStorageProvider: "Railway (Object Storage, Region: Amsterdam/EU)",
  hostingProvider: "Railway (Region: Amsterdam/EU)",
  // See app/config.py's data_retention_years docstring (backend) for the
  // legal basis and the caveat that this figure itself still needs a
  // lawyer's confirmation, same as every placeholder above.
  dataRetentionYears: 10,
} as const;
