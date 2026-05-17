from pathlib import Path

from scripts.import_contacts_from_notion import parse_csv_with_warnings


def test_parse_csv_skips_invalid_email_and_infers_language(tmp_path: Path) -> None:
    csv_path = tmp_path / "contacts.csv"
    csv_path.write_text(
        "\n".join(
            [
                "full_name,email,country,institution,outreach_language",
                "Bad Address,not-an-email,USA,Clinic,",
                "Nino Example,nino@example.com,Georgia,Clinic,",
                "Marie Example,marie@chu.fr,France,CHU,",
                "John Example,john@example.com,USA,Clinic,",
                "Explicit KA,eka@example.com,USA,Clinic,ka",
            ]
        ),
        encoding="utf-8",
    )

    rows, warnings = parse_csv_with_warnings(csv_path)

    assert len(rows) == 4
    assert len(warnings) == 1
    assert "invalid email" in warnings[0]
    assert [r.email for r in rows] == [
        "nino@example.com",
        "marie@chu.fr",
        "john@example.com",
        "eka@example.com",
    ]
    assert [r.outreach_language for r in rows] == ["ka", "fr", "en", "ka"]
