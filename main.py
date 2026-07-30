V12.0 botunda 1H kapanışı bekleyen giriş mantığını değiştir.

İstediğim değişiklik:

- 1H mum kapanışı zorunlu olmasın.
- Sinyal, 15m kapanışında üretilebilsin.
- Ancak aşağıdaki şartların hepsi sağlanmalı:

1. 15m BOS veya CHoCH oluşmuş olsun.
2. Gerçek CVD sinyal yönünü desteklesin.
3. Balina baskısı sinyal yönüyle uyumlu olsun veya en azından ters olmasın.
4. BTC yön filtresi mevcut kurallara uygun olsun.
5. Spread limiti geçerli kalsın.
6. Hacim filtresi geçerli kalsın.
7. Spoofing riski yüksekse sinyal üretme.

1H kapanışını giriş şartı olmaktan çıkar, sadece ek doğrulama (confidence artırıcı) olarak kullan.

Mevcut skor sistemi, TP/SL hesapları, risk yönetimi, Telegram mesaj formatı ve diğer filtreler kesinlikle değişmesin.

Kodun tamamında bu değişikliği uygula. Hiçbir eski 1H kapanışı zorunluluğu kalmasın.