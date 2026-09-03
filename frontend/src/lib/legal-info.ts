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
  // in, so they're filled in here directly. hostingProvider being a
  // US region is the reason section 9's Drittland/SCC clause in
  // datenschutz/page.tsx is not merely hypothetical -- flagged, not
  // silently left implicit.
  documentStorageProvider: "Railway (Object Storage, Region: Amsterdam/EU)",
  hostingProvider: "Railway (Region: San Francisco/USA)",
  // See app/config.py's data_retention_years docstring (backend) for the
  // legal basis and the caveat that this figure itself still needs a
  // lawyer's confirmation, same as every placeholder above.
  dataRetentionYears: 10,
} as const;
