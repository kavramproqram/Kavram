#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yapilandir.py — işletim sistemine özel program dosyalarını üretir
=================================================================

Her program klasöründe üç sürüm bulunur:

    rec/rec.py        Linux  (varsayılan; en kapsamlı ve her yerde yedek olarak kullanılır)
    rec/rec_win.py    Windows
    rec/rec_mac.py    macOS

Çekirdek (kavram.py) çalıştığı sistemin dosyasını seçer, yoksa varsayılana döner.  Paketleme (kavram.spec) da yalnızca
o sistemin dosyalarını pakete koyar.  Sonekler kavram_platform.SONEKLER tablosundadır.

Bu araç, varsayılan dosyadan sistem dosyalarını ÜRETİR ve o sisteme göre yapılandırır:
  * kp.IS_WIN / kp.IS_MAC / kp.IS_LINUX / kp.IS_POSIX / kp.NATIVE_RECORDING  -> sabit değerler,
    sabit koşullu `if` blokları budanır (o sistemde hiç çalışmayacak dallar dosyadan çıkar);
  * kp.lib_file("x") / kp.exe_file("x")  -> o sistemin gerçek dosya adı ("x.dll", "x.dylib" ...);
  * file_manager yedek yükleme yolu  -> file_manager_win.py / _mac.py;
  * dosya başına "bu dosya hangi sistem için" başlığı eklenir.

KULLANIM
    python3 yapilandir.py                 # eksik sistem dosyalarını üretir (var olanlara DOKUNMAZ)
    python3 yapilandir.py --zorla         # hepsini varsayılandan yeniden üretir (elle yapılan değişiklikleri SİLER!)
                                          # (rec/media için eklenen Windows/macOS kayıt altyapısı korunur; --cok-zorla ile ezilir)
    python3 yapilandir.py --sadece rec    # yalnızca bir program klasörü
    python3 yapilandir.py --denetle       # üretmeden, eksik ve eskimiş dosyaları listeler

Sistem dosyalarını artık elle düzenleyebilirsiniz; --zorla kullanmadıkça bu araç onların üzerine yazmaz.
"""
import ast
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
os.environ.pop("KAVRAM_OS", None)
import kavram_platform as kp   # noqa: E402

PROGRAMLAR = ("sphere", "terminal", "text", "drawing", "sound", "ai", "media",
              "rec", "copy", "filter", "converter", "file_manager")
SISTEMLER = {"win": "Windows", "mac": "macOS"}
LIB_UZANTI = {"win": ".dll", "mac": ".dylib"}


def sabitle(kaynak, sistem):
    """Platform sabitlerini ve dosya adı yardımcılarını o sistemin değerlerine çevirir."""
    deger = {
        "IS_WIN": sistem == "win", "IS_MAC": sistem == "mac", "IS_LINUX": sistem == "linux",
        "IS_POSIX": sistem != "win", "NATIVE_RECORDING": sistem == "linux",
    }
    for ad, v in deger.items():
        kaynak = re.sub(r"\bkp\.%s\b" % ad, str(v), kaynak)
    uz = LIB_UZANTI.get(sistem, ".so")
    kaynak = re.sub(r"kp\.lib_file\((['\"])([^'\"]+?)\1\)", lambda m: '"%s%s"' % (m.group(2), uz), kaynak)
    exe = ".exe" if sistem == "win" else ""
    kaynak = re.sub(r"kp\.exe_file\((['\"])([^'\"]+?)\1\)", lambda m: '"%s%s"' % (m.group(2), exe), kaynak)
    return kaynak


def _sabit_deger(test):
    """Test ifadesi sabitse True/False, değilse None."""
    if isinstance(test, ast.Constant) and isinstance(test.value, bool):
        return test.value
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        v = _sabit_deger(test.operand)
        return None if v is None else (not v)
    if isinstance(test, ast.BoolOp):
        vals = [_sabit_deger(x) for x in test.values]
        if isinstance(test.op, ast.And):
            if any(v is False for v in vals):
                return False
            if all(v is True for v in vals):
                return True
        else:
            if any(v is True for v in vals):
                return True
            if all(v is False for v in vals):
                return False
    return None


def _girinti(satir):
    return len(satir) - len(satir.lstrip(" "))


def buda(kaynak):
    """Sabit koşullu `if` bloklarını budar (yalnızca hep-doğru / hep-yanlış olanlar)."""
    for _ in range(500):
        try:
            agac = ast.parse(kaynak)
        except SyntaxError:
            return kaynak
        satirlar = kaynak.split("\n")
        hedef = None
        for n in ast.walk(agac):
            if isinstance(n, ast.If) and _sabit_deger(n.test) is not None:
                if satirlar[n.lineno - 1].lstrip().startswith("elif"):
                    continue                      # elif zincirine dokunma
                hedef = n
                break
        if hedef is None:
            return kaynak
        n = hedef
        deger = _sabit_deger(n.test)
        bas, son = n.lineno - 1, n.end_lineno
        ind = _girinti(satirlar[bas])
        if deger:
            govde = satirlar[n.body[0].lineno - 1: n.body[-1].end_lineno]
            yeni = [l[4:] if l.startswith(" " * (ind + 4)) else l for l in govde]
        elif n.orelse:
            ilk = n.orelse[0]
            if isinstance(ilk, ast.If) and len(n.orelse) == 1 and satirlar[ilk.lineno - 1].lstrip().startswith("elif"):
                parca = satirlar[ilk.lineno - 1: ilk.end_lineno]
                parca[0] = parca[0].replace("elif", "if", 1)
                yeni = parca
            else:
                govde = satirlar[ilk.lineno - 1: n.orelse[-1].end_lineno]
                yeni = [l[4:] if l.startswith(" " * (ind + 4)) else l for l in govde]
        else:
            yeni = []
        if not yeni:
            yeni = [" " * ind + "pass"]            # bloğun tek içeriği buydu; sözdizimi bozulmasın
        satirlar[bas:son] = yeni
        kaynak = "\n".join(satirlar)
    return kaynak


def baslik(sistem, ad, varsayilan):
    s = SISTEMLER[sistem]
    ek = kp.SONEKLER
    return (f"# ===================================================================================\n"
            f"# KAVRAM — {s} için yapılandırılmış sürüm  ({ad}{ek[sistem]}.py)\n"
            f"# Varsayılan (Linux): {varsayilan}   |   Windows: {ad}{ek['win']}.py   |   macOS: {ad}{ek['mac']}.py\n"
            f"# Bu dosyayı elle düzenleyebilirsiniz; yapilandir.py --zorla kullanmadıkça üzerine yazılmaz.\n"
            f"# ===================================================================================\n")


def uret(kaynak, sistem, ad):
    s = sabitle(kaynak, sistem)
    s = re.sub(r"^(\s*).+ if False else None[ \t]*$", r"\1pass", s, flags=re.M)   # hiç çalışmayacak tek satırlık ifade
    # "x" if True else "y"  ->  "x"   (yalnızca düz yazı sabitleri)
    s = re.sub(r'\(("[^"\n]*") if True else "[^"\n]*"\)', r"\1", s)
    s = re.sub(r'\("[^"\n]*" if False else ("[^"\n]*")\)', r"\1", s)
    s = buda(s)
    # yedek yükleme yolları:  .../file_manager/file_manager.py  ->  file_manager_win.py
    s = re.sub(r'"file_manager\.py"', '"file_manager%s.py"' % kp.SONEKLER[sistem], s)
    satirlar = s.split("\n")
    pos = 0
    while pos < min(2, len(satirlar)) and (satirlar[pos].startswith("#!") or "coding" in satirlar[pos]):
        pos += 1
    satirlar[pos:pos] = baslik(sistem, ad, f"{ad}.py").rstrip("\n").split("\n")
    return "\n".join(satirlar)


def varsayilan_dosyalar():
    """[(klasor, ad)]  — her programın varsayılan (.py) dosyaları."""
    bulunan = []
    for k in PROGRAMLAR:
        d = os.path.join(KOK, k)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".py"):
                continue
            stem = f[:-3]
            if any(stem.endswith(sk) for sk in kp.tum_sonekler()):
                continue
            bulunan.append((k, stem))
    return bulunan


def main(argv):
    zorla = "--zorla" in argv
    denetle = "--denetle" in argv
    sadece = argv[argv.index("--sadece") + 1] if "--sadece" in argv else None
    uretilen = atlanan = 0
    for klasor, ad in varsayilan_dosyalar():
        if sadece and klasor != sadece:
            continue
        kaynak_yol = os.path.join(KOK, klasor, ad + ".py")
        with open(kaynak_yol, encoding="utf-8") as f:
            kaynak = f.read()
        for sistem in SISTEMLER:
            hedef = os.path.join(KOK, klasor, ad + kp.SONEKLER[sistem] + ".py")
            var = os.path.isfile(hedef)
            if denetle:
                if not var:
                    print(f"EKSİK    {os.path.relpath(hedef, KOK)}")
                elif os.path.getmtime(kaynak_yol) > os.path.getmtime(hedef) + 1:
                    print(f"ESKİMİŞ? {os.path.relpath(hedef, KOK)}  (varsayılan dosya daha yeni)")
                continue
            if var and not zorla:
                atlanan += 1
                continue
            if var and "import kavram_capture as kc" in open(hedef, encoding="utf-8").read() and "--cok-zorla" not in argv:
                print(f"KORUNDU  {os.path.relpath(hedef, KOK)}  (kayıt altyapısı eklenmiş; ezmek için --cok-zorla)")
                atlanan += 1
                continue
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(uret(kaynak, sistem, ad))
            uretilen += 1
            print(f"yazıldı  {os.path.relpath(hedef, KOK)}")
    if not denetle:
        print(f"\n{uretilen} dosya üretildi, {atlanan} mevcut dosyaya dokunulmadı.")


if __name__ == "__main__":
    main(sys.argv[1:])
