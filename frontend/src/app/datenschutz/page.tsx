import type { Metadata } from "next";
import Link from "next/link";
import { Eyebrow, PageHeading } from "@/components/ui";
import { LegalDraftNotice, LegalPage, LegalSection } from "@/components/legal";
import { LEGAL_INFO } from "@/lib/legal-info";

export const metadata: Metadata = { title: "Datenschutzerklärung — TaxEngine.de" };

export default function DatenschutzPage() {
  const info = LEGAL_INFO;

  return (
    <LegalPage>
      <Eyebrow>Rechtliches</Eyebrow>
      <PageHeading title="Datenschutzerklärung" />
      <LegalDraftNotice />

      <LegalSection title="1. Verantwortlicher">
        <p>
          {info.operatorName}
          <br />
          {info.street}
          <br />
          {info.postalCode} {info.city}
          <br />
          E-Mail: {info.email}
        </p>
        <p>
          Diese Erklärung beschreibt, welche personenbezogenen Daten TaxEngine.de verarbeitet,
          zu welchem Zweck und auf welcher Rechtsgrundlage -- entsprechend der tatsächlichen
          technischen Funktionsweise der Anwendung.
        </p>
      </LegalSection>

      <LegalSection title="2. Kontodaten">
        <p>
          Bei der Registrierung erheben wir E-Mail-Adresse, Passwort (gehasht mit Argon2id --
          wir speichern und sehen Ihr Klartext-Passwort nie), Vor- und Nachname sowie
          Bundesland. Für die Steuererklärung ergänzen Sie Geburtsdatum, Anschrift,
          Steuer-Identifikationsnummer, Steuernummer, Steuerklasse, Konfession
          (Kirchensteuer) und ggf. Angaben zur Zusammenveranlagung.
        </p>
        <p>
          Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO (Erfüllung des Nutzungsvertrags) sowie
          Art. 6 Abs. 1 lit. c DSGVO, soweit die Angaben für die Steuererklärung selbst
          gesetzlich erforderlich sind.
        </p>
      </LegalSection>

      <LegalSection title="3. Steuerdaten">
        <p>
          Um Ihre Steuererklärung zu berechnen, verarbeiten wir die von Ihnen eingegebenen
          Einkommens- und Abzugsdaten -- u. a. Lohnsteuerbescheinigungen, Kapitalerträge,
          Miet- und Selbstständigeneinkünfte, Vorsorgeaufwendungen, außergewöhnliche
          Belastungen und Angaben zu Kindern. Diese Daten sind besonders sensibel; wir
          behandeln sie entsprechend vertraulich und geben sie ausschließlich an das für Sie
          zuständige Finanzamt weiter (siehe Abschnitt 6).
        </p>
        <p>Rechtsgrundlage: Art. 6 Abs. 1 lit. b und lit. c DSGVO.</p>
      </LegalSection>

      <LegalSection title="4. Hochgeladene Dokumente">
        <p>
          Belege wie Ihre Lohnsteuerbescheinigung können Sie als Datei hochladen. Diese Dateien
          werden ausschließlich als Referenz zu Ihrer eigenen Ablage bei{" "}
          {info.documentStorageProvider} gespeichert -- wir lesen oder verarbeiten ihren Inhalt
          nicht automatisiert (kein OCR, keine KI-Auswertung); die für die Berechnung
          relevanten Werte tragen Sie selbst in die Formularfelder ein.
        </p>
      </LegalSection>

      <LegalSection title="5. Zahlungsdaten">
        <p>
          Die Bearbeitungsgebühr wird über unseren Zahlungsdienstleister Stripe abgewickelt.
          Ihre Zahlungsdaten (z. B. Kartennummer) laufen ausschließlich über Stripe und werden
          von uns weder gespeichert noch eingesehen. Es gilt ergänzend die Datenschutzerklärung
          von Stripe.
        </p>
        <p>Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO.</p>
      </LegalSection>

      <LegalSection title="6. Übermittlung an das Finanzamt (ELSTER)">
        <p>
          Wenn Sie Ihre Steuererklärung einreichen, übermitteln wir die Daten über die
          offizielle ELSTER-Schnittstelle (ERiC) des Bayerischen Landesamts für Steuern direkt
          an das für Sie zuständige Finanzamt. Diese Übermittlung ist der eigentliche Zweck der
          Anwendung und erfolgt erst, nachdem Sie die berechneten Werte geprüft und die
          Einreichung ausdrücklich bestätigt haben.
        </p>
        <p>Rechtsgrundlage: Art. 6 Abs. 1 lit. c DSGVO (steuerliche Erklärungspflicht).</p>
        <p>
          Datenschutzhinweis der Finanzverwaltung (vorgegebener Wortlaut): „Mit dieser Software
          werden personenbezogene Daten im Sinne des Art. 4 Nr. 1 Datenschutzgrundverordnung
          (DSGVO) und Art. 9 Abs. 1 DSGVO zum Zwecke der Verarbeitung erhoben. Neben den reinen
          Daten, die zur Steuerveranlagung benötigt werden, erhebt die Software Daten über die
          Art des Betriebssystems des Nutzers und übermittelt diese an die Finanzverwaltung.
          Diese Daten werden benötigt, um die ordnungsgemäße Verarbeitung der Daten
          sicherzustellen und Fehlern im Verarbeitungsprozess vorzubeugen. Die Nutzung der Daten
          erfolgt im Rahmen des Art. 6 Abs. 1 UAbs. 1 Buchst. e i.V.m. Abs. 3 UAbs. 1 Buchst. b
          DSGVO i.V.m. bundes- bzw. landesgesetzlicher Steuergesetze durch die Finanzverwaltung
          und nur für den genannten Zweck.“
        </p>
        <p>
          Zusätzlich informiert Sie die Finanzverwaltung selbst ausführlich über die
          Datenverarbeitung im Besteuerungsverfahren -- den vollständigen, von ihr vorgegebenen{" "}
          <Link href="/elster-datenschutzhinweis" className="underline hover:text-ink">
            Datenschutzhinweis der Finanzverwaltung
          </Link>{" "}
          bringen wir Ihnen hiermit zur Kenntnis, wie es die ERiC-Lizenzvereinbarung mit dem
          Bayerischen Landesamt für Steuern vorschreibt.
        </p>
        <p>
          Da ERiC bei uns serverseitig läuft (nicht lokal bei Ihnen), werden die dabei
          entstehenden ERiC-Protokolldateien standardmäßig auf unserem Server gespeichert; sie
          werden nur im Supportfall und nur mit Ihrer ausdrücklichen Erlaubnis an das Bayerische
          Landesamt für Steuern weitergeleitet.
        </p>
      </LegalSection>

      <LegalSection title="7. Anmeldung und lokale Speicherung">
        <p>
          Nach dem Login speichern wir ein Sitzungstoken (JWT) im localStorage Ihres Browsers,
          um Sie eingeloggt zu halten. Dies ist technisch notwendig und erfordert keine
          Einwilligung. Wir setzen keine Analyse-, Marketing- oder Tracking-Cookies und keine
          Drittanbieter-Analysewerkzeuge ein.
        </p>
      </LegalSection>

      <LegalSection title="8. Server-Logs">
        <p>
          Beim Aufruf unserer Server werden technisch bedingt IP-Adresse, Zeitpunkt und
          aufgerufene Ressource protokolliert, um den Betrieb abzusichern und Missbrauch zu
          erkennen.
        </p>
        <p>Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse).</p>
      </LegalSection>

      <LegalSection title="9. Empfänger">
        <p>
          Stripe (Zahlungsabwicklung), {info.documentStorageProvider} (Dokumentenspeicherung),{" "}
          {info.hostingProvider} (Hosting/Datenbank) sowie das zuständige Finanzamt über die
          ELSTER-Schnittstelle. Eine Übermittlung an Drittländer außerhalb der EU/des EWR
          erfolgt nur, soweit einer der genannten Anbieter dort verarbeitet -- in diesem Fall
          auf Grundlage von EU-Standardvertragsklauseln.
        </p>
      </LegalSection>

      <LegalSection title="10. Speicherdauer">
        <p>
          Kontodaten speichern wir, solange Ihr Konto besteht. Steuerrelevante Daten (Ihre
          Steuererklärung sowie die zugehörigen Belege, Einkünfte und Abzüge eines Steuerjahres)
          löschen wir automatisiert {info.dataRetentionYears} volle Kalenderjahre nach Ablauf des
          jeweiligen Steuerjahres -- orientiert an den steuerlichen Verjährungsfristen
          (§§ 169-171 sowie §§ 228-232 AO), bewusst am oberen Ende dieser Fristen, um Daten
          nicht vorzeitig zu löschen, die das Finanzamt noch benötigen könnte.
        </p>
      </LegalSection>

      <LegalSection title="11. Ihre Rechte">
        <p>
          Sie haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung
          (Art. 17), Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20)
          und Widerspruch (Art. 21) sowie das Recht, sich bei einer Aufsichtsbehörde zu
          beschweren -- zuständig ist {info.supervisoryAuthority}.
        </p>
      </LegalSection>

      <LegalSection title="12. Automatisierte Entscheidungsfindung">
        <p>
          Die Steuerberechnung erfolgt automatisiert anhand der von Ihnen eingegebenen Daten,
          ist jedoch ein reiner Rechenvorgang ohne rechtliche Wirkung, bis Sie die Übermittlung
          selbst bestätigen. Eine automatisierte Entscheidung im Sinne von Art. 22 DSGVO findet
          nicht statt.
        </p>
      </LegalSection>

      <LegalSection title="13. Änderungen dieser Erklärung">
        <p>
          Wir passen diese Datenschutzerklärung an, sobald sich die Datenverarbeitung oder die
          Rechtslage ändert. Es gilt die jeweils auf dieser Seite veröffentlichte Fassung.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
