import type { Metadata } from "next";
import { Eyebrow, PageHeading } from "@/components/ui";
import { LegalDraftNotice, LegalPage, LegalSection } from "@/components/legal";
import { LEGAL_INFO } from "@/lib/legal-info";

export const metadata: Metadata = { title: "Impressum — TaxEngine.de" };

export default function ImpressumPage() {
  const info = LEGAL_INFO;
  const hasRegisterEntry = !info.registerCourt.startsWith("[");
  const hasVatId = !info.vatId.startsWith("[");
  const hasRepresentative = !info.representedBy.startsWith("[");
  const hasPhone = !info.phone.startsWith("[");
  // A natural person trading under their own name has no Rechtsform to
  // state -- § 5 DDG wants the name and a summonable address, and a legal
  // form only exists once there is a registered business behind it. So
  // this line is omitted rather than filled with a guess: printing
  // "Einzelunternehmen" for someone who has not filed a Gewerbeanmeldung
  // would be an inaccurate Impressum, which is the exact risk this file
  // exists to avoid.
  const hasLegalForm = !info.legalForm.startsWith("[");

  return (
    <LegalPage>
      <Eyebrow>Rechtliches</Eyebrow>
      <PageHeading title="Impressum" />
      <LegalDraftNotice />

      <LegalSection title="Angaben gemäß § 5 DDG">
        <p>
          {info.operatorName}
          <br />
          {hasLegalForm && (
            <>
              {info.legalForm}
              <br />
            </>
          )}
          {info.street}
          <br />
          {info.postalCode} {info.city}
          <br />
          {info.country}
        </p>
        {hasRepresentative && <p>Vertreten durch: {info.representedBy}</p>}
      </LegalSection>

      <LegalSection title="Kontakt">
        <p>
          E-Mail: {info.email}
          {hasPhone && (
            <>
              <br />
              Telefon: {info.phone}
            </>
          )}
        </p>
      </LegalSection>

      {hasRegisterEntry && (
        <LegalSection title="Registereintrag">
          <p>
            Eingetragen im Handelsregister.
            <br />
            Registergericht: {info.registerCourt}
            <br />
            Registernummer: {info.registerNumber}
          </p>
        </LegalSection>
      )}

      {hasVatId && (
        <LegalSection title="Umsatzsteuer-ID">
          <p>
            Umsatzsteuer-Identifikationsnummer gemäß § 27 a Umsatzsteuergesetz: {info.vatId}
          </p>
        </LegalSection>
      )}

      <LegalSection title="Verantwortlich für den Inhalt">
        <p>
          {info.operatorName}, Anschrift wie oben.
        </p>
      </LegalSection>

      <LegalSection title="Streitschlichtung">
        <p>
          Wir sind nicht verpflichtet und nicht bereit, an Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen. Angaben zur Zuständigkeit einer solchen
          Stelle und zur EU-Streitbeilegungsplattform sind vor dem Livegang auf ihre aktuelle
          Gültigkeit zu prüfen, da sich die Rechtslage hierzu geändert hat.
        </p>
      </LegalSection>

      <LegalSection title="Haftung für Inhalte">
        <p>
          TaxEngine.de berechnet und bereitet Steuererklärungen anhand der von Ihnen
          eingegebenen Daten vor. Trotz sorgfältiger inhaltlicher Kontrolle übernehmen wir keine
          Haftung für die Richtigkeit, Vollständigkeit und Aktualität der Berechnung -- prüfen
          Sie die berechneten Werte vor der Übermittlung an das Finanzamt.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
