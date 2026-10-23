"""Quantity/title safeguards preserve identifiers in the same sentence."""

import unittest
from types import SimpleNamespace

from detect.combined import CombinedDetector
from detect.context_rules import business_spans, filter_context_spans
from redact import redact


def span(text, value, kind):
    start = text.index(value)
    return SimpleNamespace(start=start, end=start + len(value), entity_type=kind, score=0.9)


class ContextRulesTests(unittest.TestCase):
    def test_compositional_standard_codes_correct_numeric_recognizers(self):
        for code in ("SFS-EN 12000-3-4:2021", "ISO/IEC 25010:2023", "IEC 60529-2",
                     "ASTM C150-01", "ASTM A36/A36M-24", "ASTM F1234-17a(2022)"):
            for kind in ("DATE_TIME", "US_DRIVER_LICENSE"):
                text = f"Technical standard {code}; approved by Nessa Sample on 2023-06-21."
                candidates = [span(text, code, kind), span(text, "Nessa Sample", "PERSON"),
                              span(text, "2023-06-21", "DATE_TIME")]
                with self.subTest(code=code, kind=kind):
                    self.assertEqual(candidates[1:], filter_context_spans(text, candidates))

    def test_standard_corrections_never_exempt_names_or_other_identifier_types(self):
        text = "Standard ASTM E123-24 and permit E123-24; contact Nessa Sample."
        for kind in ("PERSON", "ORGANIZATION", "FI_BUSINESS_ID", "FI_VAT_NUMBER",
                     "FI_PERSONAL_IDENTITY_CODE", "EMAIL_ADDRESS"):
            candidate = span(text, "ASTM E123-24", kind)
            self.assertEqual([candidate], filter_context_spans(text, [candidate]))
        start = text.rindex("E123-24")
        outside = SimpleNamespace(start=start, end=start + len("E123-24"),
                                  entity_type="US_DRIVER_LICENSE", score=0.9)
        mixed = span(text, "ASTM E123-24 and permit E123-24", "DATE_TIME")
        self.assertEqual([outside, mixed], filter_context_spans(text, [outside, mixed]))
        for code in ("ASTM H123-24", "ASTM C123-24extra", "EN 1234567-2", "ISO 1234/name"):
            candidate = span(code, code, "DATE_TIME")
            self.assertEqual([candidate], filter_context_spans(code, [candidate]))

    def test_language_markers_and_birth_dates_are_not_technical_citations(self):
        for text in ("Birth date (EN 2003-7-9).", "Born on EN 2003-7-9.",
                     "Date EN 2003-7-9.", "Syntymäaika EN 2003-7-9.",
                     "Certificate issued (EN 2003-7-9).",
                     "Certification expires on EN 2003-7-9.",
                     "The patient record cites standard EN 2003-7-9."):
            candidate = span(text, "2003-7-9", "DATE_TIME")
            with self.subTest(text=text):
                self.assertEqual([candidate], filter_context_spans(text, [candidate]))

    def test_year_month_dates_need_explicit_technical_evidence(self):
        for date in ("2024-11", "2019-6", "2031-02", "2024-11-07"):
            for label in ("Date of admission", "Date of graduation", "Alkamisaika"):
                text = f"{label} (EN {date})."
                for value in (f"EN {date}", date, date.split("-")[0]):
                    for kind in ("DATE_TIME", "US_DRIVER_LICENSE"):
                        with self.subTest(text=text, value=value, kind=kind):
                            candidate = span(text, value, kind)
                            self.assertEqual([candidate], filter_context_spans(text, [candidate]))
        # A year-month shape is ambiguous even for other standard prefixes.
        # Explicit technical context, rather than particular numbers, resolves it.
        for code in ("EN 2024-11", "ISO 1234-12", "SFS-EN 2019-6"):
            for kind in ("DATE_TIME", "US_DRIVER_LICENSE"):
                text = f"Technical standard {code}; contact Nessa Sample."
                candidates = [span(text, code, kind), span(text, "Nessa Sample", "PERSON")]
                self.assertEqual(candidates[1:], filter_context_spans(text, candidates))

    def test_local_inanimate_duration_keeps_reporting_person_masked(self):
        for text, value in (
            ("Nessa Sample confirmed that the warranty remains valid for 19 months.", "19 months"),
            ("Nessa Sample vahvisti, että takuu on voimassa 19 kuukautta.", "19 kuukautta"),
            ("She confirmed that the software runs for 19 months.", "19 months"),
        ):
            candidates = [span(text, value, "DATE_TIME")]
            if "Nessa Sample" in text:
                candidates.append(span(text, "Nessa Sample", "PERSON"))
            self.assertEqual(candidates[1:], filter_context_spans(text, candidates))
        for text in ("Her service lasted 19 years.", "Her Service lasted 19 years.",
                     "Her military service lasted 19 years.",
                     "Her employment duration is 19 years.", "Her prison term is 19 years."):
            candidate = span(text, "19 years", "DATE_TIME")
            self.assertEqual([candidate], filter_context_spans(text, [candidate]))

    def test_personal_contracts_and_service_agreements_keep_duration_masked(self):
        for owner in ("Her", "His", "My", "Your", "Our", "Their"):
            for subject in ("employment contract", "employment agreement", "military service",
                            "military service agreement", "lease", "service"):
                for years in (7, 19, 32):
                    text = f"{owner} {subject} lasted {years} years."
                    for value in (f"{years} years", str(years)):
                        with self.subTest(text=text, value=value):
                            candidate = span(text, value, "DATE_TIME")
                            self.assertEqual([candidate], filter_context_spans(text, [candidate]))
        for owner in ("Minun", "Sinun", "Hänen", "Meidän", "Teidän", "Heidän"):
            text = f"{owner} sopimus kesti 13 vuotta."
            candidate = span(text, "13 vuotta", "DATE_TIME")
            self.assertEqual([candidate], filter_context_spans(text, [candidate]))
        text = "Nessa Sample confirmed that the employment contract lasted 8 years."
        candidates = [span(text, "8 years", "DATE_TIME"), span(text, "Nessa Sample", "PERSON")]
        self.assertEqual(candidates, filter_context_spans(text, candidates))
        # A possessive can establish personal context even when the upstream
        # name detector supplied no PERSON candidate. Do not depend on a name list.
        for owner in ("A recruit's", "Someone's", "The operator’s", "Nessa’s"):
            text = f"{owner} service agreement lasted three years."
            candidate = span(text, "three years", "DATE_TIME")
            self.assertEqual([candidate], filter_context_spans(text, [candidate]))
        # Impersonal operational durations remain eligible for correction.
        for text, value in (("The contract lasted 8 months.", "8 months"),
                            ("Sopimus on voimassa 13 kuukautta.", "13 kuukautta")):
            self.assertEqual([], filter_context_spans(text, [span(text, value, "DATE_TIME")]))

    def test_finnish_age_inflections_and_birthdays_are_never_business_durations(self):
        for age in (9, 24, 53):
            for text, value in (
                (f"Hakija on {age} vuotta vanha.", f"{age} vuotta"),
                (f"Potilas on {age} vuoden ikäinen.", f"{age} vuoden"),
                (f"Hän täyttää {age} vuotta.", f"{age} vuotta"),
                (f"Sopimuksen hakija on {age} vuoden ikäiselle lapselle.", f"{age} vuoden"),
                (f"The review concerns a {age}-years-old applicant.", f"{age}-years"),
            ):
                with self.subTest(text=text):
                    candidate = span(text, value, "DATE_TIME")
                    self.assertEqual([candidate], filter_context_spans(text, [candidate]))

    def test_temporal_uncertainty_is_retained_without_positive_operational_context(self):
        for text in ("She is 31 years.", "Hän on 31 vuotta.", "31 years.", "31 vuotta.",
                     "The project manager is 31 years.", "The system records that she is 31 years.",
                     "Projekti kertoo, että hän on 31 vuotta.", "The contractor's daughter is 31 years."):
            candidate = span(text, "31", "DATE_TIME")
            self.assertEqual([candidate], filter_context_spans(text, [candidate]))

    def test_age_words_do_not_confuse_old_systems_with_personal_ages(self):
        for text, value in (("The old system remains active for three weeks.", "three weeks"),
                            ("Vanha järjestelmä on käytössä kolme viikkoa.", "kolme viikkoa")):
            self.assertEqual([], filter_context_spans(text, [span(text, value, "DATE_TIME")]))

    def test_unrelated_operational_words_cannot_exempt_a_personal_quantity(self):
        for text, value in (
            ("The review concerns a newborn of 2 weeks.", "2 weeks"),
            ("The review concerns a toddler of 18 months.", "18 months"),
            ("The contractor, 28 years, signed the agreement.", "28 years"),
            ("Tarkastus koskee 17 vuoden nuorukaista.", "17 vuoden"),
            ("Her employment duration is 18 years.", "18 years"),
            ("Her prison term: 4 years.", "4 years"),
        ):
            with self.subTest(text=text):
                candidate = span(text, value, "DATE_TIME")
                self.assertEqual([candidate], filter_context_spans(text, [candidate]))

    def test_only_unnamed_impersonal_logistics_facilities_are_exempted(self):
        for text, value in (("Stock is stored in a regional depot.", "regional depot"),
                            ("Incoming goods are kept in the storage area.", "storage area"),
                            ("Tavarat siirretään keskusvarastoon.", "keskusvarastoon")):
            with self.subTest(text=text):
                self.assertEqual([], filter_context_spans(text, [span(text, value, "LOCATION")]))

    def test_named_personal_or_uncertain_facilities_remain_masked(self):
        for text, value in (
            ("Goods arrive at North Example warehouse.", "warehouse"),
            ("Goods arrive at north example warehouse.", "warehouse"),
            ("Goods arrive at the warehouse at Dock Road 41.", "warehouse"),
            ("Goods arrive at her warehouse.", "warehouse"),
            ("Goods arrive at warehouse SITE-B.", "warehouse"),
            ("The only supervisor receives goods at the warehouse.", "warehouse"),
            ("Goods arrive at the warehouse named northpoint.", "warehouse"),
            ("Goods arrive at the warehouse northpoint.", "warehouse"),
            ("Goods arrive at the warehouse (northpoint).", "warehouse"),
            ("Goods arrive at the warehouse — northpoint.", "warehouse"),
            ("Goods arrive at the warehouse along dock road.", "warehouse"),
            ("Goods arrive at Main Warehouse.", "Main Warehouse"),
            ("Toimitukset tulevat Turun päävarastolle.", "päävarastolle"),
            ("Toimitukset tulevat heidän päävarastolle.", "päävarastolle"),
            ("The warehouse is described here.", "warehouse"),
            ("Goods are stored in Finland.", "Finland"),
            ("Tavarat säilytetään Suomessa.", "Suomessa"),
        ):
            with self.subTest(text=text):
                candidate = span(text, value, "LOCATION")
                self.assertEqual([candidate], filter_context_spans(text, [candidate]))

    def test_quantities_and_standards_are_retained_but_calendar_dates_are_masked(self):
        for quantity in ("hours 37", "hours: 4.5", "18 months", "2 years", "14 days",
                         "18 kuukautta", "7 tuntia", "three weeks", "kahden kuukauden",
                         "ISO 9001", "ISO/IEC 27001:2022"):
            with self.subTest(quantity=quantity):
                text = f"Allocation {quantity}; signed on 2024-03-19 by Alice Example."
                candidates = [span(text, quantity, "DATE_TIME"),
                              span(text, "2024-03-19", "DATE_TIME"),
                              span(text, "Alice Example", "PERSON")]
                clean = redact(text, filter_context_spans(text, candidates))
                self.assertIn(quantity, clean)
                self.assertNotIn("2024-03-19", clean)
                self.assertNotIn("Alice Example", clean)

    def test_numbers_inside_explicit_quantity_context_are_also_preserved(self):
        text = "Allocated hours 29, on 2024-03-19."
        self.assertEqual([], filter_context_spans(text, [span(text, "29", "DATE_TIME")]))

    def test_ambiguous_dates_and_mixed_spans_are_kept(self):
        for value in ("May 18", "18/12/2024", "18 months from 2024-01-02", "age 18 years"):
            candidates = [span(value, value, "DATE_TIME")]
            self.assertEqual(candidates, filter_context_spans(value, candidates))
        text = "Born three weeks ago."
        candidate = span(text, "three weeks", "DATE_TIME")
        self.assertEqual([candidate], filter_context_spans(text, [candidate]))

    def test_only_complete_job_title_person_spans_are_removed(self):
        for title in ("finance director", "project manager", "Programme Manager",
                      "research coordinator", "tuotepäällikkö", "ympäristöasiantuntija"):
            text = f"The {title} Alice Example approved."
            candidates = [span(text, title, "PERSON"), span(text, "Alice Example", "PERSON")]
            clean = redact(text, filter_context_spans(text, candidates))
            self.assertIn(title, clean)
            self.assertNotIn("Alice Example", clean)
            mixed = span(text, f"{title} Alice Example", "PERSON")
            self.assertEqual([mixed], filter_context_spans(text, [mixed]))

    def test_finnish_business_and_vat_shapes_are_not_arbitrary_numbers(self):
        text = "Y-tunnus 1234567-8; VAT FI12345678; 18 months; ISO 9001; 12345678."
        found = business_spans(text)
        self.assertEqual([(text[s.start:s.end], s.entity_type) for s in found],
                         [("1234567-8", "FI_BUSINESS_ID"), ("FI12345678", "FI_VAT_NUMBER")])
        for value in ("A1234567-8", "1234567-89", "FI123456789", "XFI12345678", "FI12345678EX"):
            self.assertEqual([], business_spans(value))

    def test_optional_company_glossary_is_literal_bounded_and_case_insensitive(self):
        text = "North Example met north example, not North Examples."
        self.assertEqual([], business_spans(text))
        found = business_spans(text, ["North Example"])
        self.assertEqual(2, len(found))
        self.assertTrue(all(s.entity_type == "ORGANIZATION" for s in found))
        for invalid in ("", " ", None):
            with self.assertRaises(ValueError):
                business_spans(text, [invalid])

    def test_combined_applies_filters_to_both_families_and_adds_ids(self):
        text = "hours 23, finance director Alice Example, VAT FI12345678"
        presidio = SimpleNamespace(detect=lambda *args: [span(text, "hours 23", "DATE_TIME")])
        model = SimpleNamespace(detect=lambda *args: [span(text, "finance director", "PERSON"),
                                                    span(text, "Alice Example", "PERSON")])
        clean = redact(text, CombinedDetector(presidio, model).detect(text))
        self.assertIn("hours 23, finance director", clean)
        self.assertNotIn("Alice Example", clean)
        self.assertNotIn("FI12345678", clean)


if __name__ == "__main__":
    unittest.main()
