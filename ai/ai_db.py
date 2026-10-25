# Kavram AI Editörü — veritabanı (Qt gerektirmez)
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import difflib
import sqlite3

from ai_text import normalize_text

# norm_word hesaplama kuralı değiştiğinde artırılır; eski dosyalar açılışta bir kez yenilenir.
NORMALIZE_VERSION = 1


class KavramDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS words
                     (id INTEGER PRIMARY KEY, norm_word TEXT, raw_word TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS definitions
                     (id INTEGER PRIMARY KEY, word_id INTEGER, raw_def TEXT)''')
        
        c.execute('DROP TABLE IF EXISTS chat_history')
        c.execute('CREATE INDEX IF NOT EXISTS idx_words_norm ON words(norm_word)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_defs_word ON definitions(word_id)')
        self.conn.commit()
        self._migrate_normalization()

    def _migrate_normalization(self):
        """Eski dosyalardaki norm_word değerlerini güncel normalize_text ile bir kez yeniler."""
        c = self.conn.cursor()
        c.execute('PRAGMA user_version')
        if c.fetchone()[0] >= NORMALIZE_VERSION:
            return
        c.execute('SELECT id, raw_word FROM words')
        updates = [(normalize_text(raw or ''), wid) for wid, raw in c.fetchall()]
        c.executemany('UPDATE words SET norm_word=? WHERE id=?', updates)
        c.execute(f'PRAGMA user_version = {NORMALIZE_VERSION}')
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def suggest_words(self, word, limit=5):
        """Cevap bulunamadığında 'Bunu mu demek istediniz' önerileri üretir."""
        norm = normalize_text(word)
        if not norm:
            return []
        c = self.conn.cursor()
        c.execute('''SELECT w.norm_word, MIN(w.raw_word) FROM words w
                     JOIN definitions d ON w.id = d.word_id
                     GROUP BY w.norm_word ORDER BY MIN(w.id)''')
        mapping = dict(c.fetchall())
        found = []
        for n, raw in mapping.items():
            if (len(norm) >= 2 and norm in n) or (len(n) >= 3 and n in norm):
                found.append(raw)
        for n in difflib.get_close_matches(norm, list(mapping), n=limit, cutoff=0.6):
            found.append(mapping[n])
        result = []
        for raw in found:
            if raw not in result and normalize_text(raw) != norm:
                result.append(raw)
        return result[:limit]

    def migrate_from_dict(self, word_dict):
        c = self.conn.cursor()
        c.execute("DELETE FROM words")
        c.execute("DELETE FROM definitions")
        
        for k, entries in word_dict.items():
            if k == "__chat_history__":
                continue 
            
            c.execute("INSERT INTO words (norm_word, raw_word) VALUES (?, ?)", (normalize_text(k), k))
            word_id = c.lastrowid
            
            for entry in entries:
                raw_def = entry[0] if isinstance(entry, list) else str(entry)
                c.execute("INSERT INTO definitions (word_id, raw_def) VALUES (?, ?)", (word_id, raw_def))
        self.conn.commit()

    def get_all_packets(self):
        c = self.conn.cursor()
        c.execute('''SELECT d.id, w.raw_word, d.raw_def FROM definitions d
                     JOIN words w ON d.word_id = w.id ORDER BY d.id DESC''')
        return c.fetchall()

    def add_packet(self, word, definition):
        norm = normalize_text(word)
        c = self.conn.cursor()
        c.execute("SELECT id FROM words WHERE norm_word=?", (norm,))
        row = c.fetchone()
        if row:
            word_id = row[0]
        else:
            c.execute("INSERT INTO words (norm_word, raw_word) VALUES (?, ?)", (norm, word))
            word_id = c.lastrowid
        c.execute("INSERT INTO definitions (word_id, raw_def) VALUES (?, ?)", (word_id, definition))
        self.conn.commit()
        return c.lastrowid

    def update_packet(self, def_id, new_word, new_def):
        c = self.conn.cursor()
        norm = normalize_text(new_word)
        c.execute("SELECT id FROM words WHERE norm_word=?", (norm,))
        row = c.fetchone()
        if row:
            new_word_id = row[0]
        else:
            c.execute("INSERT INTO words (norm_word, raw_word) VALUES (?, ?)", (norm, new_word))
            new_word_id = c.lastrowid
        c.execute("UPDATE definitions SET word_id=?, raw_def=? WHERE id=?", (new_word_id, new_def, def_id))
        
        c.execute("DELETE FROM words WHERE id NOT IN (SELECT word_id FROM definitions)")
        self.conn.commit()

    def delete_packet(self, def_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM definitions WHERE id=?", (def_id,))
        c.execute("DELETE FROM words WHERE id NOT IN (SELECT word_id FROM definitions)")
        self.conn.commit()

    def is_duplicate_word(self, word, current_def_id=None):
        norm = normalize_text(word)
        if not norm: return False
        c = self.conn.cursor()
        if current_def_id is not None:
            c.execute('''SELECT d.id FROM definitions d 
                         JOIN words w ON d.word_id = w.id 
                         WHERE w.norm_word = ? AND d.id != ?''', (norm, current_def_id))
        else:
            c.execute('''SELECT d.id FROM definitions d 
                         JOIN words w ON d.word_id = w.id 
                         WHERE w.norm_word = ?''', (norm,))
        return c.fetchone() is not None

    def search_definitions(self, word):
        norm = normalize_text(word)
        c = self.conn.cursor()
        c.execute('''SELECT d.raw_def FROM definitions d
                     JOIN words w ON d.word_id = w.id WHERE w.norm_word = ?''', (norm,))
        exact_matches = [r[0] for r in c.fetchall()]
        return exact_matches

    def get_valid_words(self):
        c = self.conn.cursor()
        c.execute("""SELECT DISTINCT w.raw_word FROM words w
                     JOIN definitions d ON w.id = d.word_id
                     ORDER BY w.id ASC""")
        return [r[0] for r in c.fetchall()]
