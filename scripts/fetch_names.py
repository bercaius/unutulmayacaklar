import json
import os
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES_FILE = os.path.join(BASE_DIR, 'data', 'names.json')
ROOT = 'https://www.mehmetcik.org.tr'

SOURCES = [
    'https://www.mehmetcik.org.tr/sehitlerimiz',
    'https://www.mehmetcik.org.tr/sehitlerimiz?yil=2025',
    'https://www.mehmetcik.org.tr/sehitlerimiz?yil=2024',
    'https://www.mehmetcik.org.tr/sehitlerimiz?yil=2023',
    'https://www.mehmetcik.org.tr/sehitlerimiz?yil=2022',
    'https://www.mehmetcik.org.tr/sehitlerimiz?yil=2021',
    'https://www.mehmetcik.org.tr/sehitlerimiz?yil=2020',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; UnutulmayacaklarBot/1.0)'
}

# Only accept proper Turkish personal names: 2-3 words, Title Case, no punctuation/numbers
BLOCKLIST_PHRASES = [
    'bağışlarınızla', 'bağışlar hakkında', 'telif geliri', 'adana temsilciliği',
    'bursa temsilciliği', 'erzurum temsilciliği', 'samsun temsilciliği',
    'izmir temsilciliği', 'ankara temsilciliği', 'gaziantep temsilciliği',
    'konya temsilciliği', 'istanbul temsilciliği', 'aydınlatma metni',
    'kvkk aydınlatma', 'gizlilik politikası', 'kullanım koşulları',
    'çerez politikası', 'online bağış', 'sms ile bağış', 'kurban bağışları',
    'düzenli bağış', 'gayrimenkul bağışı', 'satıştaki gayrimenkuller',
    'web tasarım', 'tümünü gör', 'yıllara göre', 'türk silahlı',
    'mehmetçik vakfı', 'mehmetçik vakfına', 'şehit ve gazi', 'gazi mehmetçik',
    'engelli mehmetçik', 'şehit aileleri', 'gazi aileleri', 'nasuh akar',
    'sok no', 'kişi sayıları', 'kişisel verilerin', 'merak ettikleriniz',
    'her hakkı', 'rahmetle anıyoruz', 'bağışlarımızla şöyleşiler',
    'genel ilanlarımız', 'iletişim kanalları', 'temel görevlerimiz',
    'teşkilat yapısı', 'mali bilgiler', 'gelir kaynaklarımız',
    'yardım çeşitleri', 'müracaat esasları', 'yazılı basın',
    'internet haberleri', 'tanıtım materyallerimiz', 'yüreğimize dokunanlar',
    'bağışlar hakkında merak', 'bağışlarınızla neler', 'ne yapılıyor',
    'telif geliri banka', 'gayrimenkuller iletişim', 'mehmetçik vakfı hakkımızda',
    'temsilcilikler basın', 'tasarım dataişlem', 'bağışlarımızı şöyleşiler',
    'data işlem', 'bağışlar hakkında', 'bağışlarınızla', 'bağışlarımızla',
    'bağış', 'yardım', 'destek', 'katkı', 'sponsor', 'maddi', 'manevi'
]

STOP_WORDS = {
    'adana', 'bursa', 'erzurum', 'samsun', 'izmir', 'istanbul', 'ankara', 'konya',
    'gaziantep', 'kayseri', 'kocaeli', 'antalya', 'diyarbakır', 'sanliurfa', 'mardin',
    'van', 'malatya', 'trabzon', 'sivas', 'eskisehir', 'balikesir', 'manisa', 'aydin',
    'denizli', 'afyonkarahisar', 'usak', 'nigde', 'kirikkale', 'yozgat', 'aksaray',
    'nevsehir', 'kutahya', 'canakkale', 'edirne', 'kirklareli', 'tekirdag', 'bilecik',
    'bolu', 'duzce', 'zonguldak', 'karabuk', 'bartin', 'kastamonu', 'sinop', 'ordu',
    'giresun', 'tokat', 'amasya', 'corum', 'kahramanmaras', 'adiyaman', 'kilis',
    'osmaniye', 'hatay', 'mersin', 'burdur', 'isparta', 'rize', 'gumushane',
    'bayburt', 'ardahan', 'kars', 'igdir', 'agri', 'mus', 'bitlis', 'siirt',
    'sirnak', 'hakkari', 'batman', 'gayrimenkul', 'bagis', 'yardim', 'kurban',
    'sms', 'online', 'banka', 'zekat', 'ramazan', 'fitre', 'dizenli', 'web',
    'tasarim', 'data', 'islem', 'kvkk', 'gizlilik', 'kosullar', 'reklam', 'cerez',
    'iletisim', 'tel', 'eposta', 'adres', 'sosyal', 'medya', 'facebook', 'instagram',
    'twitter', 'youtube', 'linkedin', 'whatsapp', 'paylas', 'yazdir', 'anahtar',
    'kelime', 'baslik', 'aciklama', 'kategori', 'etiket', 'yorum', 'soru', 'cevap',
    'sss', 'sikca', 'sorulan', 'merak', 'ettikleriniz', 'nasil', 'yapilir', 'kimler',
    'yazili', 'elektronik', 'basinda', 'haberler', 'duyurular', 'etkinlik', 'program',
    'proje', 'kampanya', 'hediye', 'cekilis', 'kayit', 'form', 'gonder', 'onayla',
    'iptal', 'geri', 'devam', 'ana', 'sayfa', 'menu', 'navigasyon', 'arama', 'sonuc',
    'liste', 'detay', 'resim', 'video', 'fotograf', 'galeri', 'slider', 'carousel',
    'banner', 'logo', 'icon', 'font', 'renk', 'arka', 'plan', 'ozel', 'genel', 'yeni',
    'eski', 'tumu', 'filtrele', 'sirala', 'goster', 'gizle', 'ac', 'kapat', 'yukle',
    'indir', 'dosya', 'belge', 'evrak', 'fotokopi', 'nufus', 'cuzdan', 'hesap',
    'numara', 'kod', 'pin', 'sifre', 'giris', 'uye', 'ol', 'olustur', 'hesap',
    'memnuniyet', 'anket', 'oy', 'puan', 'yildiz', 'derece', 'seviye', 'basari',
    'odul', 'sertifika', 'belgelendirme', 'onay', 'denetim', 'rapor', 'istatistik',
    'sayi', 'tutar', 'miktar', 'oran', 'yuzde', 'toplam', 'ortalama', 'en', 'az',
    'cok', 'fazla', 'azalt', 'arttir', 'degistir', 'guncelle', 'sil', 'ekle',
    'duzenle', 'kaydet', 'vazgec', 'tamam', 'onay', 'hayir', 'evet', 'bilgi', 'veri',
    'kayit', 'saklama', 'guvenlik', 'koruma', 'hak', 'sorumluluk', 'sorun', 'hata',
    'bakim', 'destek', 'yardim', 'yardimci', 'kullan', 'kullanici', 'musteri',
    'satici', 'alici', 'odem', 'odeme', 'fatura', 'makbuz', 'dekont', 'transfer',
    'havale', 'eft', 'kredi', 'kart', 'nakit', 'cek', 'senet', 'teminat', 'depozit',
    'borc', 'alacak', 'gelir', 'gider', 'kar', 'zarar', 'butce', 'mali', 'finans',
    'ekonomi', 'ticaret', 'sanayi', 'hizmet', 'uretim', 'imalat', 'ithalat', 'ihracat',
    'doviz', 'kur', 'borsa', 'hisse', 'fon', 'yatirim', 'kalkinma', 'plan', 'strateji',
    'hedef', 'politika', 'yonetim', 'kurul', 'direktor', 'genel', 'mudur', 'sorumlu',
    'yetkili', 'temsilci', 'sube', 'merkez', 'bolge', 'il', 'ilce', 'mahalle',
    'cadde', 'sokak', 'no', 'kat', 'daire', 'bin', 'site', 'kule', 'avm',
    'alisveris', 'magaza', 'urun', 'talep', 'siparis', 'teslimat', 'kargo', 'paket',
    'koli', 'agirlik', 'hacim', 'ebat', 'model', 'marka', 'kalite', 'standart',
    'norm', 'yonetmelik', 'kanun', 'tuzuk', 'madde', 'bolum', 'fiyat', 'indirim',
    'promosyon', 'uyelik', 'abonelik', 'iade', 'degisim', 'zaman', 'tarih', 'saat',
    'gun', 'hafta', 'ay', 'yil', 'mevsim', 'donem', 'baslangic', 'bitis', 'sure',
    'vade', 'taksit', 'faiz', 'komisyon', 'birim', 'adet', 'parca', 'set', 'seri',
    'versiyon', 'surum', 'guncelleme', 'yama', 'patch', 'fix', 'bug', 'problem',
    'cozum', 'teknik', 'servis', 'onarim', 'ikinci', 'el', 'sifir', 'kullanilmis',
    'orjinal', 'kopya', 'taklit', 'sahte', 'gercek', 'dogru', 'yanlis', 'dogruluk',
    'hatali', 'eksik', 'tam', 'bos', 'dolu', 'var', 'yok', 'mevcut', 'stok',
    'tedarik', 'temin', 'satin', 'al', 'sat', 'kira', 'kiralik', 'satilik', 'firsat'
}


def load_names():
    if not os.path.exists(NAMES_FILE):
        return []
    with open(NAMES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        raw = data.get('names', [])
        return [n if isinstance(n, dict) else {'name': n, 'photo': None} for n in raw]


def save_names(entries):
    os.makedirs(os.path.dirname(NAMES_FILE), exist_ok=True)
    with open(NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump({'names': entries}, f, ensure_ascii=False, indent=4)


def is_valid_name(text):
    words = text.split()
    if len(words) < 2 or len(words) > 3:
        return False
    for w in words:
        if len(w) < 2:
            return False
        if not (w[0].isupper() and w[1:].islower()):
            return False
    low = text.lower()
    if any(p in low for p in BLOCKLIST_PHRASES):
        return False
    if any(w.lower() in STOP_WORDS for w in words):
        return False
    return True


def extract_sehit_entries(html):
    blocks = re.findall(
        r'<div class="col-md-2 col-6 text-center sehit">(.*?)</div>',
        html, re.DOTALL)
    entries = {}
    for b in blocks:
        img = re.search(r'src="([^"]+)"', b)
        name = re.search(r'<strong>([^<]+)</strong>', b)
        if img and name:
            nm = name.group(1).strip()
            if is_valid_name(nm):
                src = img.group(1)
                full = src if src.startswith('http') else ROOT + src
                mid = re.search(r'/(\d+)-', src)
                url = (ROOT + '/sehitlerimiz?id=' + mid.group(1)) if mid else (ROOT + '/sehitlerimiz')
                entries[nm] = (full, url)
    return entries


def fetch_url(url):
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'Fetch error {url}: {e}')
        return ''


def main():
    existing = load_names()
    # Geriye dönük: mevcut kayıtlara fotoğraftan detay URL'si türet
    for e in existing:
        if not e.get('url') and e.get('photo'):
            mid = re.search(r'/(\d+)-', e['photo'])
            if mid:
                e['url'] = ROOT + '/sehitlerimiz?id=' + mid.group(1)
    existing_map = {e['name']: e for e in existing}
    new_entries = []

    for url in SOURCES:
        print(f'Fetching {url}...')
        html = fetch_url(url)
        if not html:
            continue

        entries = extract_sehit_entries(html)
        print(f'Found {len(entries)} entries from {url}')
        for nm, (ph, det_url) in entries.items():
            if nm not in existing_map:
                new_entries.append({'name': nm, 'photo': ph, 'url': det_url})

    final = existing + new_entries
    final_sorted = sorted(final, key=lambda e: e['name'])

    # Güvenlik: siteden beklenenden çok az veri geldiyse (site geçici çökmüş
    # veya yapı değişmiş olabilir) mevcut dosyayı bozmadan koru.
    min_safe = max(1, int(len(existing) * 0.5))
    if len(final_sorted) < min_safe:
        print('SAFETY: fetched count too low ({} < {}), keeping previous file.'.format(
            len(final_sorted), min_safe))
        return 0

    save_names(final_sorted)
    print(f'\nTotal entries in database: {len(final_sorted)}')
    print(f'Added {len(new_entries)} new entries')
    if new_entries:
        for n in new_entries:
            print(' +', n['name'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
