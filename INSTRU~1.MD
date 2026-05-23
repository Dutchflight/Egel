# AVI → MP4 Converter

## Lokaal draaien

1. Zorg dat Python en FFmpeg geïnstalleerd zijn
2. Installeer afhankelijkheden:
   ```
   pip install flask
   ```
3. Start de server:
   ```
   python app.py
   ```
4. Open je browser op: http://localhost:5000

---

## Gratis online zetten via Railway

Railway is een gratis cloudplatform dat FFmpeg ondersteunt — geen creditcard nodig.

### Stappen:

1. **Maak een gratis account** op https://railway.app
2. **Maak een GitHub repository** aan en upload alle bestanden uit deze map
3. **Ga naar Railway → New Project → Deploy from GitHub**
4. Selecteer je repository
5. Railway detecteert automatisch Python + FFmpeg via `nixpacks.toml`
6. Na deploy krijg je een publieke URL zoals `https://jouwapp.railway.app`

### Belangrijk voor productie:
- Pas in `app.py` de laatste regel aan:
  ```python
  app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
  ```
  (de `PORT` variabele wordt door Railway automatisch ingesteld)
- Geüploade bestanden worden tijdelijk opgeslagen — Railway heeft geen permanente opslag.
  Voor grote bestanden overweeg een object storage zoals Cloudflare R2 (ook gratis).

---

## Bestandsstructuur

```
avi_to_mp4/
├── app.py              ← Flask server
├── requirements.txt    ← Python afhankelijkheden
├── Procfile            ← Startcommando voor Railway
├── nixpacks.toml       ← FFmpeg installatie op Railway
├── static/
│   └── index.html      ← De webpagina
├── uploads/            ← Tijdelijke uploads (automatisch aangemaakt)
└── outputs/            ← Geconverteerde MP4's (automatisch aangemaakt)
```
