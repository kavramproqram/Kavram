# Kavram AI Editörü — Qt gerektirmeyen modüller için testler
# Çalıştırma:  python -m unittest test_ai_modules -v   (ai klasörü içinde)
import io
import os
import sqlite3
import tarfile
import tempfile
import unittest

from ai_archive import (ArchiveError, install_staged, pack_ai_archive,
                        stage_ai_archive)
from ai_db import KavramDB
from ai_text import normalize_text


class NormalizeTests(unittest.TestCase):
    def test_turkish_letters(self):
        self.assertEqual(normalize_text("Kışla"), "kisla")
        self.assertEqual(normalize_text("KIŞLA"), "kisla")
        self.assertEqual(normalize_text("İSTANBUL"), "istanbul")
        self.assertEqual(normalize_text("çğöşü"), "cgosu")

    def test_whitespace_and_empty(self):
        self.assertEqual(normalize_text("  a   b "), "a b")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")

    def test_non_latin_not_empty(self):
        self.assertNotEqual(normalize_text("привет"), "")


class DbTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "data.db")

    def tearDown(self):
        self.dir.cleanup()

    def test_add_search_and_duplicates(self):
        db = KavramDB(self.path)
        db.add_packet("Kışla", "tanım 1")
        self.assertEqual(db.search_definitions("kisla"), ["tanım 1"])
        self.assertTrue(db.is_duplicate_word("KIŞLA"))
        db.close()

    def test_old_files_are_renormalized(self):
        # Eski sürümün yazdığı norm_word ('kla') yeni kuralla düzeltilmeli
        con = sqlite3.connect(self.path)
        con.execute("CREATE TABLE words (id INTEGER PRIMARY KEY, norm_word TEXT, raw_word TEXT)")
        con.execute("CREATE TABLE definitions (id INTEGER PRIMARY KEY, word_id INTEGER, raw_def TEXT)")
        con.execute("INSERT INTO words VALUES (1, 'kla', 'kışla')")
        con.execute("INSERT INTO definitions VALUES (1, 1, 'eski tanım')")
        con.commit(); con.close()
        db = KavramDB(self.path)
        self.assertEqual(db.search_definitions("kışla"), ["eski tanım"])
        db.close()
        db = KavramDB(self.path)   # ikinci açılışta tekrar çalışmamalı, veri bozulmamalı
        self.assertEqual(db.search_definitions("kisla"), ["eski tanım"])
        db.close()

    def test_migrate_from_dict(self):
        db = KavramDB(self.path)
        db.migrate_from_dict({"Işık": [["parlaklık"]], "__chat_history__": []})
        self.assertEqual(db.search_definitions("isik"), ["parlaklık"])
        self.assertEqual(db.get_valid_words(), ["Işık"])
        db.close()

    def test_update_and_delete(self):
        db = KavramDB(self.path)
        did = db.add_packet("a", "x")
        db.update_packet(did, "b", "y")
        self.assertEqual(db.search_definitions("b"), ["y"])
        self.assertEqual(db.search_definitions("a"), [])
        db.delete_packet(did)
        self.assertEqual(db.get_all_packets(), [])
        db.close()

    def test_suggestions(self):
        db = KavramDB(self.path)
        for w in ("kavram", "kavramsal harita", "bilgisayar"):
            db.add_packet(w, "tanım")
        self.assertIn("kavram", db.suggest_words("kavramm"))
        self.assertIn("kavramsal harita", db.suggest_words("harita"))
        self.assertEqual(db.suggest_words("zzzzqq"), [])
        db.close()


def _make_tar(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for info, data in entries:
            tar.addfile(info, io.BytesIO(data) if data is not None else None)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.parent = os.path.join(self.root, "export")
        self.dest = os.path.join(self.parent, "ai")
        os.makedirs(self.dest)

    def tearDown(self):
        self.tmp.cleanup()

    def test_path_traversal_is_rejected_and_nothing_written(self):
        evil = os.path.join(self.root, "evil.ai")
        info = tarfile.TarInfo("../pwned.txt"); info.size = 3
        _make_tar(evil, [(info, b"bad")])
        with self.assertRaises(ArchiveError):
            stage_ai_archive(evil, self.parent)
        self.assertFalse(os.path.exists(os.path.join(self.parent, "pwned.txt")))
        self.assertEqual(os.listdir(self.parent), ["ai"])   # staging klasörü temizlendi

    def test_symlink_is_rejected(self):
        evil = os.path.join(self.root, "link.ai")
        info = tarfile.TarInfo("data.db"); info.type = tarfile.SYMTYPE; info.linkname = "/etc/passwd"
        _make_tar(evil, [(info, None)])
        with self.assertRaises(ArchiveError):
            stage_ai_archive(evil, self.parent)

    def test_pack_stage_install_roundtrip(self):
        media = os.path.join(self.root, "a.txt")
        db = os.path.join(self.root, "data.db")
        open(media, "w").write("merhaba"); open(db, "w").write("db")
        target = os.path.join(self.root, "out.ai")
        seen = []
        pack_ai_archive(target, [("data.db", db), ("a.txt", media)], seen.append)
        self.assertEqual(seen, [0, 1])
        open(os.path.join(self.dest, "eski.bin"), "w").write("x")
        staging = stage_ai_archive(target, self.parent)
        install_staged(staging, self.dest)
        self.assertEqual(sorted(os.listdir(self.dest)), ["a.txt", "data.db"])
        self.assertEqual(open(os.path.join(self.dest, "a.txt")).read(), "merhaba")

    def test_failed_pack_keeps_existing_file(self):
        target = os.path.join(self.root, "keep.ai")
        open(target, "w").write("ESKI")
        with self.assertRaises(Exception):
            pack_ai_archive(target, [("x", os.path.join(self.root, "yok.dosya"))])
        self.assertEqual(open(target).read(), "ESKI")
        self.assertFalse(os.path.exists(target + ".tmp"))

    def test_plain_json_fallback(self):
        js = os.path.join(self.root, "old.ai")
        open(js, "w", encoding="utf-8").write('{"kelime": [["tanım"]]}')
        staging = stage_ai_archive(js, self.parent)
        self.assertTrue(os.path.exists(os.path.join(staging, "data.json")))


if __name__ == "__main__":
    unittest.main()
