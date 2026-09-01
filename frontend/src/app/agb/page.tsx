import type { Metadata } from "next";
import { Eyebrow, PageHeading } from "@/components/ui";
import { LegalDraftNotice, LegalPage, LegalSection } from "@/components/legal";
import { LEGAL_INFO } from "@/lib/legal-info";

export const metadata: Metadata = { title: "AGB — TaxEngine.de" };

export default function AgbPage() {
  const info = LEGAL_INFO;

  return (
    <LegalPage>
      <Eyebrow>Rechtliches</Eyebrow>
      <PageHeading title="Allgemeine Geschäftsbedingungen" />
      <LegalDraftNotice />

      <div className="mb-10 border-l-2 border-clay bg-clay-soft/40 px-4 py-3 text-sm text-clay">
        § 5 (Widerrufsrecht) setzt voraus, dass Nutzer vor Zahlung der Bearbeitungsgebühr
        ausdrücklich zustimmen, dass die Übermittlung sofort beginnt, und bestätigen, dass sie
        dadurch ihr Widerrufsrecht verlieren (§ 356 Abs. 4 BGB). Diese Einwilligung wird auf der
        Bezahlseite aktuell noch nicht eingeholt -- vor dem Livegang technisch umsetzen, sonst
        ist die vorzeitige Erlöschung des Widerrufsrechts unwirksam.
      </div>

      <LegalSection title="§ 1 Geltungsbereich">
        <p>
          Diese Allgemeinen Geschäftsbedingungen gelten für die Nutzung von TaxEngine.de,
          angeboten von {info.operatorName}, {info.street}, {info.postalCode} {info.city}{" "}
          ("wir", "TaxEngine.de"), durch registrierte Nutzerinnen und Nutzer ("Sie").
          Abweichende Bedingungen des Nutzers werden nicht anerkannt, es sei denn, wir stimmen
          ihrer Geltung ausdrücklich schriftlich zu.
        </p>
      </LegalSection>

      <LegalSection title="§ 2 Leistungsbeschreibung">
        <p>
          TaxEngine.de ist ein Online-Werkzeug zur Erfassung und Berechnung einer
          Einkommensteuererklärung. Die Erfassung Ihrer Daten und die Berechnung der
          voraussichtlichen Erstattung sind kostenlos. Kostenpflichtig ist ausschließlich die
          Übermittlung Ihrer Steuererklärung an das zuständige Finanzamt über die offizielle
          ELSTER-Schnittstelle (ERiC).
        </p>
        <p>
          Je nach technischem Stand erfolgt die Übermittlung entweder authentifiziert oder als
          unauthentifizierte (komprimierte) Übermittlung, bei der Sie zusätzlich das erzeugte
          Mantelbogen-Dokument unterschrieben an Ihr Finanzamt senden müssen, damit die
          Erklärung rechtlich wirksam wird.
        </p>
      </LegalSection>

      <LegalSection title="§ 3 Preise und Zahlung">
        <p>
          Die Bearbeitungsgebühr beträgt pauschal 34,90 € brutto je übermittelter
          Steuererklärung und wird über unseren Zahlungsdienstleister Stripe erhoben. Die
          Gebühr fällt erst an, wenn Sie die Übermittlung an das Finanzamt auslösen, nicht für
          die reine Berechnung.
        </p>
      </LegalSection>

      <LegalSection title="§ 4 Keine Steuerberatung">
        <p>
          TaxEngine.de ist ein Berechnungs- und Übermittlungswerkzeug und leistet keine
          individuelle steuerliche Beratung im Sinne des Steuerberatungsgesetzes (StBerG). Die
          Berechnung erfolgt ausschließlich anhand der von Ihnen eingegebenen Daten; wir prüfen
          diese nicht auf inhaltliche Richtigkeit oder Vollständigkeit. Sie sind verpflichtet,
          die berechneten Werte vor der Übermittlung selbst zu prüfen. Für eine verbindliche
          steuerliche Beratung wenden Sie sich an eine Steuerberaterin, einen Steuerberater oder
          einen Lohnsteuerhilfeverein.
        </p>
      </LegalSection>

      <LegalSection title="§ 5 Widerrufsrecht für Verbraucher">
        <p>
          Verbraucherinnen und Verbrauchern steht grundsätzlich ein 14-tägiges Widerrufsrecht
          gemäß §§ 355, 356 BGB zu. Bei Dienstleistungen erlischt das Widerrufsrecht vorzeitig,
          wenn wir die Leistung vollständig erbracht haben und erst begonnen haben, nachdem Sie
          ausdrücklich zugestimmt haben, dass wir vor Ablauf der Widerrufsfrist mit der
          Ausführung beginnen, und Sie zur Kenntnis genommen haben, dass Sie dadurch Ihr
          Widerrufsrecht verlieren (§ 356 Abs. 4 BGB).
        </p>
        <p className="rounded-sm bg-paper-dim p-4 text-sm">
          Muster-Widerrufsformular (an {info.operatorName}, {info.street}, {info.postalCode}{" "}
          {info.city}, {info.email}): "Hiermit widerrufe(n) ich/wir den von mir/uns
          abgeschlossenen Vertrag über die Erbringung der folgenden Dienstleistung: Übermittlung
          meiner/unserer Steuererklärung -- Bestellt am / erhalten am -- Name des/der
          Verbraucher(s) -- Anschrift des/der Verbraucher(s) -- Datum."
        </p>
      </LegalSection>

      <LegalSection title="§ 6 Pflichten des Nutzers">
        <p>
          Sie sind für die Richtigkeit und Vollständigkeit der von Ihnen eingegebenen Daten
          verantwortlich. Zugangsdaten sind vertraulich zu behandeln; verdächtige Aktivitäten
          melden Sie uns bitte unverzüglich.
        </p>
      </LegalSection>

      <LegalSection title="§ 7 Haftung">
        <p>
          Wir haften unbeschränkt für Vorsatz und grobe Fahrlässigkeit sowie nach den
          Vorschriften des Produkthaftungsgesetzes. Bei leicht fahrlässiger Verletzung
          wesentlicher Vertragspflichten (Kardinalpflichten) ist die Haftung auf den
          vertragstypisch vorhersehbaren Schaden begrenzt. Im Übrigen ist die Haftung
          ausgeschlossen. Für die inhaltliche Richtigkeit der von Ihnen eingegebenen Daten und
          die daraus berechneten Werte übernehmen wir keine Gewähr.
        </p>
      </LegalSection>

      <LegalSection title="§ 8 Vertragsdauer und Kündigung">
        <p>
          Der Nutzungsvertrag läuft auf unbestimmte Zeit und kann von Ihnen jederzeit durch
          Löschung Ihres Kontos beendet werden. Bereits übermittelte Steuererklärungen bleiben
          davon unberührt.
        </p>
      </LegalSection>

      <LegalSection title="§ 9 Änderungen dieser AGB">
        <p>
          Wir können diese AGB mit Wirkung für die Zukunft ändern, etwa bei Änderungen der
          Rechtslage oder des Leistungsumfangs. Über wesentliche Änderungen informieren wir Sie
          in Textform; widersprechen Sie nicht innerhalb von vier Wochen, gilt die Änderung als
          angenommen.
        </p>
      </LegalSection>

      <LegalSection title="§ 10 Schlussbestimmungen">
        <p>
          Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des UN-Kaufrechts.
          Sollte eine Bestimmung dieser AGB unwirksam sein, bleibt die Wirksamkeit der übrigen
          Bestimmungen unberührt.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
