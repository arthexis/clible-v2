"""Synthetic metadata and verse fixtures; no translation text redistribution."""

from unittest.mock import patch

from clible.db.connection import get_connection
from clible.db.repositories.book_repo import Testament
from clible.parsers.book_ids import ordered_book_ids
from clible.parsers.combined_parser import CombinedParser
from clible.services.seed_service import SeedService
from clible.services.verse_service import VerseService
from clible.utils.book_names import resolve_book_id


def test_existing_database_upgrades_without_rewriting_verses(tmp_path):
    db = tmp_path / "legacy.db"
    conn = get_connection(db)
    conn.execute("DELETE FROM books WHERE testament='DEU'")
    conn.execute(
        "INSERT INTO translations(id,name,language,format) VALUES ('old','Fixture','es','BEBLIA')"
    )
    conn.execute(
        "INSERT INTO verses(id,translation_id,book_id,chapter,verse,text) "
        "VALUES ('old-1','old','JHN',1,1,'fixture text')"
    )
    conn.commit()
    original = [tuple(r) for r in conn.execute("SELECT * FROM verses")]
    legacy = [tuple(r) for r in conn.execute("SELECT * FROM books ORDER BY position")]
    conn.close()
    for _ in range(2):
        conn = get_connection(db)
        assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 85
        rows = conn.execute("SELECT * FROM books WHERE testament!='DEU' ORDER BY position")
        assert [tuple(r) for r in rows] == legacy
        assert [tuple(r) for r in conn.execute("SELECT * FROM verses")] == original
        conn.close()


def test_explicit_usfx_import_and_translation_isolation(translation_repo, verse_repo, book_repo):
    assert len(book_repo.get_by_testament(Testament.DEU)) == 19
    service = SeedService(translation_repo, verse_repo, book_repo, CombinedParser())
    xml = (
        b'<usfx><book id="TOB"><c id="1"/><p><v id="1"/>fixture<ve/></p></book>'
        b'<book id="ZZZ"><c id="1"/><p><v id="1"/>unknown<ve/></p></book></usfx>'
    )
    with patch("clible.services.seed_service._download_xml", return_value=xml):
        result = service.seed_translation("web")
    assert result["verses_installed"] == 1
    lookup = VerseService(verse_repo, book_repo, translation_repo)
    for alias in ("TOB", "Tobit", "Tobías", "Tobias"):
        assert lookup.get_verse(alias + " 1:1", "web")["book_id"] == "TOB"
    assert lookup.get_verse("TOB 1:1", "spanishdhh") is None
    assert resolve_book_id("1 Macabeos") == "1MA"
    assert resolve_book_id("Ester griego") == "ESG"


def test_numeric_formats_keep_legacy_mapping(tmp_path):
    ids = ordered_book_ids()
    assert len(ids) == 66 and ids[39] == "MAT" and ids[65] == "REV"
    p = tmp_path / "numeric.xml"
    p.write_text(
        '<bible><testament><book number="40"><chapter number="1">'
        '<verse number="1">fixture</verse></chapter></book>'
        '<book number="67"><chapter number="1"><verse number="1">unknown'
        "</verse></chapter></book></testament></bible>"
    )
    assert [v["book_id"] for v in CombinedParser().parse_file(p)] == ["MAT"]
    p.write_text(
        '<XMLBIBLE><BIBLEBOOK bnumber="66"><CHAPTER cnumber="1">'
        '<VERS vnumber="1">fixture</VERS></CHAPTER></BIBLEBOOK>'
        '<BIBLEBOOK bnumber="67"><CHAPTER cnumber="1"><VERS vnumber="1">unknown'
        "</VERS></CHAPTER></BIBLEBOOK></XMLBIBLE>"
    )
    assert [v["book_id"] for v in CombinedParser().parse_file(p)] == ["REV"]


def test_osis_deuterocanonical_explicit_ids(tmp_path):
    p = tmp_path / "osis.xml"
    p.write_text(
        '<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">'
        '<osisText><verse osisID="Wis.1.1">fixture</verse>'
        '<verse osisID="Unknown.1.1">unknown</verse></osisText></osis>'
    )
    assert [v["book_id"] for v in CombinedParser().parse_file(p)] == ["WIS"]


def test_local_import_is_explicit_and_non_destructive(
    tmp_path, translation_repo, verse_repo, book_repo
):
    import pytest

    service = SeedService(translation_repo, verse_repo, book_repo, CombinedParser())
    p = tmp_path / "private.xml"
    p.write_text('<usfx><book id="DAG"><c id="13"/><p><v id="1"/>fixture<ve/></p></book></usfx>')
    meta = dict(name="Fixture", language="es", format="USFX")
    with patch("clible.services.seed_service._download_xml", side_effect=AssertionError("network")):
        result = service.import_local("local-fixture", p, **meta)
    assert result["books_installed"] == 1
    assert verse_repo.get_verse("local-fixture", "DAG", 13, 1) is not None
    assert verse_repo.get_verse("local-fixture", "DAN", 13, 1) is None
    with pytest.raises(ValueError, match="already installed"):
        service.import_local("local-fixture", p, **meta)
    with pytest.raises(ValueError, match="does not match"):
        service.import_local("bad", p, **{**meta, "format": "OSIS"})
    assert not translation_repo.exists("bad")
