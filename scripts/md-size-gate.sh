#!/usr/bin/env bash
# CLAUDE.md boyut kapısı — rehber dosyalarının sessizce şişmesini durdurur.
#
# Her `CLAUDE.md` o dizinde çalışan HER oturumda otomatik bağlama girer; yani
# bir satır eklemenin bedeli bir kez değil, o dosyanın okunduğu her oturumda
# tekrar ödenir. Bütçe `scripts/md-budget.tsv`'de (cırcır: tavan yalnız iner).
#
# Kullanım:
#   scripts/md-size-gate.sh              # denetle (kapı)
#   scripts/md-size-gate.sh --guncelle   # tavanları BUGÜNKÜ boyuta çek
#
# Çıkış kodu: 0 = geçti, 1 = bütçe aşıldı veya bütçesiz dosya var.
set -uo pipefail

# ⚠️ KOK ve BUTCE disaridan verilebilir. Sebep: bu betigin KANONIK kopyasi
# ~/.claude/scripts/ altinda durur ve oradan cagrildiginda script konumundan
# turetilen KOK yanlis olur (~/.claude cikar, proje degil). Projeye KOPYALANMIS
# hali icin varsayilanlar dogru calisir; hook MD_KOK gecer.
KOK="${MD_KOK:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
GUNCELLE=0
HOOK=0
for arg in "$@"; do
  [ "$arg" = "--guncelle" ] && GUNCELLE=1
  [ "$arg" = "--hook" ] && HOOK=1
done

# Butce dosyasi: acik yol > scripts/ > kok > docs/. Cogu projede scripts/ yok.
if [ -n "${MD_BUTCE:-}" ]; then BUTCE="$MD_BUTCE"; else
  for aday in "$KOK/scripts/md-budget.tsv" "$KOK/md-budget.tsv" "$KOK/docs/md-budget.tsv"; do
    [ -f "$aday" ] && { BUTCE="$aday"; break; }
  done
fi

if [ -z "${BUTCE:-}" ] || [ ! -f "$BUTCE" ]; then
  # ⚠️ HOOK modunda "butce yok" bir HATA DEGIL, "kurulmamis" demektir; kapi
  # sessizce gecer ve yalniz bir satirla haber verir. Merge kapisi olarak
  # kosuldugunda (varsayilan) EKSIK BUTCE HATADIR — aksi halde butce dosyasini
  # silmek kapiyi da silerdi.
  if [ "$HOOK" -eq 1 ]; then
    echo "· CLAUDE.md butcesi bu projede kurulu degil (md-budget.tsv yok)."
    echo "  Kurmak icin: /apply-project-standards  ya da"
    echo "  cp ~/.claude/scripts/md-*.sh ~/.claude/scripts/md-*.py scripts/ && bash scripts/md-size-gate.sh --guncelle"
    exit 0
  fi
  echo "✗ Bütçe dosyası yok: ${BUTCE:-<bulunamadı>}"; exit 1
fi

# ⚠️ SATIR SONU NORMALIZE EDILIR (Agustos 2026 - gercek bir hata).
# Eskiden `wc -c` calisma agacindaki dosyayi olcuyordu. `core.autocrlf=true`
# olan bir Windows checkout'unda her satir bir bayt daha uzun olur; sonuc:
# HICBIR DEGISIKLIK YAPILMADAN backend/web/mobile CLAUDE.md dosyalari
# "tavan asildi" veriyordu (sirasiyla +1753, +930, +659 bayt). Yani kapi
# Windows'ta yapisi geregi kirmiziydi ve tavanlar makineye gore kayiyordu.
# Artik CR baytlari sayimdan DUSULUR — olcum git blob'u ile ayni ve
# isletim sisteminden BAGIMSIZDIR.
kb() {
  local bytes cr
  bytes=$(wc -c < "$1")
  cr=$(tr -cd '\r' < "$1" | wc -c)
  echo $(( ( bytes - cr + 1023 ) / 1024 ))
}

HATA=0
BULUNAN=""
# Projeye ozel kesif dislamalari: butce dosyasinda `# disla:<goreli-yol>`.
# Neden tsv'de: dislama proje verisidir (~/.claude'da plugins/, skills/addy
# ucuncu taraf; baska projede baska sey) — betige gomulmez, betik geneldir.
# ⚠️ Bos "# disla:" yok sayilir: yanlislikla her seyi dislamasin.
DISLA=()
while IFS= read -r satir; do
  case "$satir" in "# disla:"*) d="${satir#\# disla:}"; d="${d%%[[:space:]]*}"; [ -n "$d" ] && DISLA+=("${d%/}") ;; esac
done < "$BUTCE"

printf '%-28s %7s %7s %7s  %s\n' DOSYA ŞİMDİ TAVAN HEDEF DURUM
printf '%.0s─' {1..78}; echo

while IFS=$'\t' read -r yol tavan hedef not; do
  case "$yol" in ''|\#*) continue ;; esac
  BULUNAN="$BULUNAN|$yol"
  tam="$KOK/$yol"
  if [ ! -f "$tam" ]; then
    printf '%-28s %7s %7s %7s  %s\n' "$yol" "-" "$tavan" "$hedef" "✗ DOSYA YOK"
    HATA=1; continue
  fi
  simdi=$(kb "$tam")
  if [ "$simdi" -gt "$tavan" ]; then
    printf '%-28s %7s %7s %7s  %s\n' "$yol" "$simdi" "$tavan" "$hedef" "✗ TAVAN AŞILDI (+$((simdi-tavan)) KB)"
    HATA=1
  elif [ "$simdi" -le "$hedef" ]; then
    printf '%-28s %7s %7s %7s  %s\n' "$yol" "$simdi" "$tavan" "$hedef" "✓ hedefte"
  else
    printf '%-28s %7s %7s %7s  %s\n' "$yol" "$simdi" "$tavan" "$hedef" "· tavan altında"
  fi
done < "$BUTCE"

# Bütçesiz yeni CLAUDE.md — sessizce eklenip büyümesin diye kapı bunu da tutar.
# ⚠️ Dislama KOKE GORELI yapilir, mutlak yola degil (05/09/2026, mutasyonla
# bulundu): eski desen `-not -path "*/.claude/*"` idi ve betik bir git
# WORKTREE'den kosuldugunda (yol: .../Repo/.claude/worktrees/x/) kokun KENDISI
# desene uyuyordu — kesif dongusu HICBIR dosya bulmuyor, butcesiz yeni bir
# CLAUDE.md sessizce geciyordu. Butceli dosyalar tsv uzerinden yine
# denetlendigi icin belirti yoktu; kor nokta tam bir gun fark edilmedi.
# ⚠️ Asagidaki <( ... ) icine YORUM KOYMA: bash calisma zamaninda ")" sinirini
# kaybeder, dongu coker ve kapi yine "yesil" der (bash -n bunu YAKALAMAZ).
while IFS= read -r f; do
  rel="${f#$KOK/}"
  case "$rel" in .claude/*|**/node_modules/*|docs/claude-md-archive/*) continue ;; esac
  atla=0; for d in "${DISLA[@]+"${DISLA[@]}"}"; do case "$rel" in "$d"/*|"$d") atla=1 ;; esac; done
  [ "$atla" -eq 1 ] && continue
  if ! echo "$BULUNAN" | grep -q "|$rel"; then
    printf '%-28s %7s %7s %7s  %s\n' "$rel" "$(kb "$f")" "-" "-" "✗ BÜTÇESİZ"
    HATA=1
  fi
done < <(find "$KOK" \( -path "$KOK/.claude" -o -path "*/node_modules" -o -path "$KOK/docs/claude-md-arsiv" \) -prune -o -name CLAUDE.md -print 2>/dev/null)

echo

if [ "$GUNCELLE" -eq 1 ]; then
  # Tavanı yalnız İNDİRİR. Yükseltme elle ve gerekçeyle yapılır — otomatik
  # yükseltme cırcırı iptal eder ve kapıyı dekoratif hâle getirir.
  tmp="$(mktemp)"
  while IFS=$'\t' read -r yol tavan hedef not; do
    case "$yol" in ''|\#*) echo "$yol" >> "$tmp"; continue ;; esac
    tam="$KOK/$yol"
    if [ -f "$tam" ]; then
      simdi=$(kb "$tam")
      if [ "$simdi" -lt "$tavan" ]; then
        echo "  ↓ $yol tavanı $tavan -> $simdi KB"
        tavan="$simdi"
      fi
    fi
    printf '%s\t%s\t%s\t%s\n' "$yol" "$tavan" "$hedef" "$not" >> "$tmp"
  done < "$BUTCE"
  mv "$tmp" "$BUTCE"
  echo "Bütçe güncellendi (yalnız indirildi)."
  exit 0
fi

if [ "$HATA" -eq 1 ]; then
  cat <<'SON'
✗ KAPI KAPALI — CLAUDE.md bütçesi aşıldı.

Yapılacak (sırayla):
  1. Eklediğin şey bir KURAL mı, yoksa gerekçe/tarihçe/test tutanağı mı?
     Gerekçe ve tarihçe aktif dosyada DURMAZ — docs/<ayak>-decision-log.md'ye taşı,
     aktif dosyada kural cümlesi + detay linki kalsın.
  2. Gerçekten aktif dosyada kalması gereken yeni bir kuralsa:
     scripts/md-budget.tsv'de tavanı yükselt ve NOT sütununa GEREKÇE yaz.
  3. Sadeleştirme yaptıysan tavanı indir:  scripts/md-size-gate.sh --guncelle
SON
  exit 1
fi

echo "✓ Tüm CLAUDE.md dosyaları bütçe içinde."
exit 0
