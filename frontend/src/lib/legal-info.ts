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

export const LEGAL_INFO = {
  operatorName: "[Vollständiger Name / Firma]",
  legalForm: "[z. B. Einzelunternehmen / Kleingewerbe / GmbH]",
  representedBy: "[Vertretungsberechtigte Person -- nur bei juristischer Person nötig]",
  street: "[Straße und Hausnummer]",
  postalCode: "[PLZ]",
  city: "[Ort]",
  country: "Deutschland",
  email: "[kontakt@taxengine.de]",
  phone: "[Telefonnummer -- optional]",
  registerCourt: "[Registergericht -- nur bei Handelsregistereintrag]",
  registerNumber: "[Registernummer -- nur bei Handelsregistereintrag]",
  vatId: "[USt-IdNr. -- falls vorhanden]",
  supervisoryAuthority: "[Zuständige Landesdatenschutzbehörde am Firmensitz]",
  documentStorageProvider: "[S3-kompatibler Anbieter, z. B. Cloudflare R2 / AWS S3 -- Region angeben]",
  hostingProvider: "[Hosting-/Datenbankanbieter -- Region angeben]",
} as const;
