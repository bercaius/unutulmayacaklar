import json
import os
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES_FILE = os.path.join(BASE_DIR, 'data', 'names.json')

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
        return data.get('names', [])


def save_names(names):
    os.makedirs(os.path.dirname(NAMES_FILE), exist_ok=True)
    with open(NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump({'names': names}, f, ensure_ascii=False, indent=4)


def is_name_in_db(partial_name, db_names):
    parts = partial_name.split()
    for db_name in db_names:
        db_parts = db_name.split()
        if len(parts) <= len(db_parts):
            if db_parts[:len(parts)] == parts:
                return True
    return False


def extract_sehit_names(html):
    found = set()
    sehit_elements = re.findall(
        r'class="[^"]*sehit[^"]*"[^>]*>(.*?)</(?:div|span|a|h[1-6])>',
        html, re.DOTALL | re.IGNORECASE
    )
    for content in sehit_elements:
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split()
        name_words = []
        for word in words[:4]:
            if len(word) >= 2 and word[0].isupper() and word[1:].islower():
                name_words.append(word)
            else:
                if len(name_words) >= 2:
                    break
                else:
                    name_words = []
                    break
        if len(name_words) >= 2:
            candidate = ' '.join(name_words)
            if all(w[0].isupper() for w in candidate.split()):
                found.add(candidate)
    return found


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
    new_names = set()

    for url in SOURCES:
        print(f'Fetching {url}...')
        html = fetch_url(url)
        if not html:
            continue

        names = extract_sehit_names(html)
        print(f'Found {len(names)} names from {url}')
        for name in names:
            if not is_name_in_db(name, existing):
                new_names.add(name)

    added = []
    current = list(existing)
    for name in sorted(new_names):
        if name not in current:
            current.append(name)
            added.append(name)

    final_names = sorted(set(current))
    save_names(final_names)
    print(f'\nTotal names in database: {len(final_names)}')
    print(f'Added {len(added)} new names')
    if added:
        for n in added:
            print(' +', n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
