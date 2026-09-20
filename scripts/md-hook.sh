#!/usr/bin/env bash
# CLAUDE.md boyut circirini otomatik kosan hook. IKI olayda birden baglanir:
#
#   PostToolUse (Edit|Write) : duzenlemenin hemen ardindan, aninda geri bildirim
#   Stop                     : tur sonunda, YONTEMDEN BAGIMSIZ yakalama agi
#
# ⚠️ STOP OLAYI NEDEN SART: PostToolUse matcher'i ARAC ADINA bakar. Claude bir
# CLAUDE.md'yi `Bash` ile (sed / python heredoc / cat >) duzenlerse Edit de
# Write de calismaz ve hook SESSIZ kalir. Bu teorik degil: 05/09/2026'da bu
# hook'un kuruldugu oturumun KENDISI butun CLAUDE.md duzenlemelerini Bash ile
# yapti — yani hook kendi kuruldugu turda bir kez bile atesienmeyecekti.
# Stop olayi tur sonunda deponun tamamina bakar ve yontemi umursamaz.
#
# ⚠️ YESILKEN SESSIZ: her turda "butce icinde" yazmak gurultu olur ve gurultu
# okunmamayi ogretir. Yalnizca ASIM ya da BUTCESIZ dosya varken konusur.
#
# ⚠️ Bu bir RELEASE kapisi DEGIL, davranis uyarisidir; cikis kodu her zaman 0.
# Gercek merge kapisi olan projede betigin KOPYASI repoda durur ve CI onu
# kosar (bkz. ~/.claude/scripts/README.md). Ayrimi koru.
set -uo pipefail

girdi="$(cat 2>/dev/null || true)"

# PostToolUse ise dosya yolu gelir; Stop olayinda gelmez.
yol="$(printf '%s' "$girdi" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
ti=d.get("tool_input") or {}
print(ti.get("file_path") or ti.get("path") or "")' 2>/dev/null)"

if [ -n "$yol" ]; then
  # Arac tabanli cagri: yalnizca CLAUDE.md ilgilendirir.
  case "$(basename "$yol")" in CLAUDE.md) ;; *) exit 0 ;; esac
  baslangic="$(dirname "$yol")"
else
  # Stop olayi: cwd'nin deposuna bak.
  baslangic="$PWD"
fi

kok="$(git -C "$baslangic" rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$kok" ] || exit 0

cikti="$(MD_KOK="$kok" bash "$HOME/.claude/scripts/md-size-gate.sh" --hook 2>&1)" || true

# Butce kurulu degilse Stop olayinda SUS (her turda kurulum onerisi gurultudur);
# acikca bir CLAUDE.md duzenlendiyse bir kez soyle.
if printf '%s' "$cikti" | grep -q 'butcesi bu projede kurulu degil'; then
  [ -n "$yol" ] && printf '%s\n' "$cikti"
  exit 0
fi

if printf '%s' "$cikti" | grep -q 'TAVAN AŞILDI\|BÜTÇESİZ\|DOSYA YOK'; then
  echo "⚠️ CLAUDE.md butcesi asildi — yeni kalici karar KOKE degil docs/kurallar/<konu>.md'ye:"
  printf '%s\n' "$cikti" | grep -E 'TAVAN AŞILDI|BÜTÇESİZ|DOSYA YOK'
  echo "   Sadelestirdiysen:  bash scripts/md-size-gate.sh --guncelle"
fi

# ── Ikiz sapmasi ────────────────────────────────────────────────────────────
# Bu uc arac bilincli IKIZDIR: kanonik kopya ~/.claude/scripts/ altinda durur,
# her proje kendi scripts/'ine bir KOPYA alir ve onu commit'ler (bir projenin
# kapisi repo disi bir yola baglanamaz). Ikiz varsa SAPMA TESTI de olmali —
# bu depo baska ikizlerde (normalizeSearch, safeUrl) tam olarak boyle yapiyor.
# 05/09/2026'da sapma GERCEKTEN yasandi: kanonik guncellendi, projedeki kopya
# eski kaldi ve yalniz elle karsilastirmayla fark edildi.
sapan=""
for arac in md-size-gate.sh md-rule-gate.py md-split.py; do
  [ -f "$kok/scripts/$arac" ] || continue
  cmp -s "$kok/scripts/$arac" "$HOME/.claude/scripts/$arac" || sapan="$sapan $arac"
done
if [ -n "$sapan" ]; then
  echo "⚠️ MD araclari kanonik kopyadan SAPMIS:$sapan"
  echo "   Kanonik: ~/.claude/scripts/  ·  Bu proje: $kok/scripts/"
  echo "   Hangisi guncel? Once karsilastir, sonra IKISINI DE ayni hale getir:"
  echo "   diff ~/.claude/scripts/<arac> scripts/<arac>"
fi
exit 0
