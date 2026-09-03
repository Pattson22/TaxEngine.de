import type { Metadata } from "next";
import { Eyebrow, PageHeading } from "@/components/ui";
import { LegalPage, LegalSection } from "@/components/legal";

export const metadata: Metadata = {
  title: "Datenschutzhinweis der Finanzverwaltung — TaxEngine.de",
};

/**
 * Verbatim reproduction of "Allgemeine Informationen zur Umsetzung der
 * datenschutzrechtlichen Vorgaben der Artikel 12 bis 14 der
 * Datenschutz-Grundverordnung in der Steuerverwaltung" (Anhang 2 of the
 * ERiC-Lizenzvereinbarung between the Bayerisches Landesamt für Steuern
 * and this project, as software manufacturer).
 *
 * This page exists because of a specific, non-negotiable obligation in
 * that license (§ 5 Abs. 1): the software manufacturer must present this
 * exact letter to end users, with the ability to review and confirm
 * having read it, before they use the software. This is the LfSt's own
 * text -- not paraphrased -- since a paraphrase would not satisfy that
 * obligation. Content and structure copied from lizenz.pdf, Anhang 2
 * (Stand: 1. Juli 2021), obtained via ELSTER Developer Area access -- see
 * docs/ELSTER_ERIC_INTEGRATION.md.
 */
export default function ElsterDatenschutzhinweisPage() {
  return (
    <LegalPage>
      <Eyebrow>Rechtliches</Eyebrow>
      <PageHeading
        title="Datenschutzhinweis der Finanzverwaltung"
        subtitle="Allgemeine Informationen zur Umsetzung der datenschutzrechtlichen Vorgaben der Artikel 12 bis 14 DSGVO in der Steuerverwaltung (Stand: 1. Juli 2021)"
      />

      <p className="mb-8 text-sm text-ink/60">
        Dieser Hinweis wird von der Finanzverwaltung (Bayerisches Landesamt für Steuern) selbst
        vorgegeben und unverändert veröffentlicht -- TaxEngine.de ist als Software­hersteller
        vertraglich verpflichtet, ihn Ihnen vor Nutzung der ELSTER-Übermittlung zur Kenntnis zu
        bringen.
      </p>

      <LegalSection title="Vorwort">
        <p>
          Nahezu alle Bürgerinnen und Bürger sowie Unternehmen treten mit der Steuerverwaltung –
          insbesondere den Finanzämtern – früher oder später in Kontakt, weil sie
          Steuererklärungen abgeben und Steuern zahlen müssen und Erstattungen oder auch
          Kindergeld beanspruchen können. Hierbei müssen personenbezogene Daten verarbeitet
          werden.
        </p>
        <p>
          Die nachfolgenden Informationen betreffen die Verarbeitung personenbezogener Daten zu
          steuerlichen Zwecken, soweit die Abgabenordnung unmittelbar oder mittelbar anzuwenden
          ist. Ausgenommen ist die Verarbeitung personenbezogener Daten durch Zollbehörden (z. B.
          Zölle, Einfuhrumsatzsteuer und Kraftfahrzeugsteuer).
        </p>
        <p>
          Im Besteuerungsverfahren sind Daten personenbezogen, wenn sie einer natürlichen Person,
          einer Körperschaft (z. B. Verein, Kapitalgesellschaft), einer Personenvereinigung oder
          einer Vermögensmasse zugeordnet werden können. Keine personenbezogenen Daten sind
          anonymisierte Daten.
        </p>
      </LegalSection>

      <LegalSection title="1. Wer sind wir?">
        <p>
          „Wir“ sind die Finanzbehörden des Bundes (Ausnahme: Zollverwaltung) und der Länder und
          für die Verarbeitung personenbezogener Daten zu steuerlichen Zwecken verantwortlich.
        </p>
      </LegalSection>

      <LegalSection title="2. Wer sind Ihre Ansprechpartner?">
        <p>
          Fragen in datenschutzrechtlichen Angelegenheiten können Sie an die verantwortliche
          Finanzbehörde, vertreten durch die Behördenleitung, richten. Im Regelfall sind die
          Finanzämter für die Verarbeitung personenbezogener Daten verantwortlich, beim
          Kindergeld die Familienkassen.
        </p>
        <p>
          Die entsprechenden Kontaktdaten für die Landesfinanzbehörden finden Sie unter{" "}
          finanzamt.de in den jeweiligen landesspezifischen Übersichten, für das
          Bundesministerium der Finanzen unter bundesfinanzministerium.de und für das
          Bundeszentralamt für Steuern und die Familienkassen unter bzst.de.
        </p>
      </LegalSection>

      <LegalSection title="3. Zu welchem Zweck verarbeiten wir Ihre personenbezogenen Daten?">
        <p>
          Um ihre Aufgabe zu erfüllen, die Steuern nach den Vorschriften der Abgabenordnung und
          der Steuergesetze gleichmäßig festzusetzen und zu erheben, benötigt die
          Finanzverwaltung personenbezogene Daten (§ 85 der Abgabenordnung). Ihre
          personenbezogenen Daten werden in dem steuerlichen Verfahren verarbeitet, für das sie
          erhoben wurden (§ 29b der Abgabenordnung).
        </p>
      </LegalSection>

      <LegalSection title="4. Welche personenbezogenen Daten verarbeiten wir?">
        <p>
          Persönliche Identifikations- und Kontaktangaben (z. B. Vor- und Nachname, Adresse,
          Geburtsdatum und -ort, Steuernummer, Identifikationsnummer, E-Mail-Adresse,
          Telefonnummer) sowie für die Festsetzung und Erhebung der Steuern erforderliche
          Informationen (Einnahmen, Ausgaben, einbehaltene Steuern, Familienstand und Kinder,
          Lohnsteuerklasse, Beruf, Bankverbindung, Angaben über abgegebene Steuererklärungen).
        </p>
        <p>
          Besondere Kategorien personenbezogener Daten („sensible Daten“) erhebt die
          Finanzverwaltung ebenfalls nur, wenn dies für das Besteuerungsverfahren erforderlich
          ist -- z. B. Angaben über die Religionszugehörigkeit für die Kirchensteuer, oder
          Angaben über Erkrankungen/Behinderungen für außergewöhnliche Belastungen.
        </p>
      </LegalSection>

      <LegalSection title="5. Wie verarbeiten wir diese Daten?">
        <p>
          Im weitgehend automationsgestützten Besteuerungsverfahren werden Ihre
          personenbezogenen Daten gespeichert und dann in zumeist maschinellen Verfahren der
          Festsetzung und Erhebung der Steuer zugrunde gelegt. Rechtsverbindliche Entscheidungen
          trifft die Finanzverwaltung nur dann auf Grundlage einer „vollautomatischen“
          Verarbeitung personenbezogener Daten, wenn dies gesetzlich zugelassen ist (z. B.
          „vollautomatischer“ Steuerbescheid nach § 155 Absatz 4 der Abgabenordnung).
        </p>
      </LegalSection>

      <LegalSection title="6. Unter welchen Voraussetzungen dürfen wir Ihre Daten an Dritte weitergeben?">
        <p>
          Alle personenbezogenen Daten, die der Finanzverwaltung in einem steuerlichen Verfahren
          bekannt geworden sind, dürfen nur dann an andere Personen oder Stellen weitergegeben
          werden, wenn Sie dem zugestimmt haben oder die Weitergabe gesetzlich zugelassen ist
          (z. B. Mitteilung an die für Grundsteuer/Gewerbesteuer zuständigen Gemeinden, an die
          gesetzliche Sozialversicherung, oder an Familienkassen).
        </p>
      </LegalSection>

      <LegalSection title="7. Wie lange speichern wir Ihre Daten?">
        <p>
          Personenbezogene Daten müssen solange gespeichert werden, wie sie für das
          Besteuerungsverfahren erforderlich sind. Maßstab hierfür sind die steuerlichen
          Verjährungsfristen (§§ 169 bis 171 sowie §§ 228 bis 232 der Abgabenordnung). Die
          Finanzverwaltung darf Sie betreffende personenbezogene Daten auch speichern, um diese
          für künftige steuerliche Verfahren zu verarbeiten (§ 88a der Abgabenordnung).
        </p>
      </LegalSection>

      <LegalSection title="8. Welche Rechte haben Sie?">
        <p>
          Sie haben nach der Datenschutz-Grundverordnung insbesondere das Recht auf Auskunft
          (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung
          (Art. 18) und Widerspruch (Art. 21) sowie das Recht auf Beschwerde bei der zuständigen
          Datenschutzaufsichtsbehörde -- im Regelfall die oder der Bundesbeauftragte für den
          Datenschutz und die Informationsfreiheit (bfdi.bund.de), bzw. die jeweilige
          Landesdatenschutzbehörde.
        </p>
        <p>
          Diese Rechte können in bestimmten, gesetzlich geregelten Fällen eingeschränkt sein
          (§§ 32c bis 32f der Abgabenordnung).
        </p>
      </LegalSection>

      <LegalSection title="9. Wo bekommen Sie weitergehende Informationen?">
        <p>
          Im BMF-Schreiben zum Datenschutz im Steuerverwaltungsverfahren vom 13. Januar 2020
          (zuletzt geändert durch das BMF-Schreiben vom 17. Juni 2021, BStBl 2020 I S. 143 und
          BStBl 2021 I S. 809) sowie in der Broschüre „Steuern von A bis Z“ auf
          bundesfinanzministerium.de.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
