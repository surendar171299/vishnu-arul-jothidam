# விஷ்ணு அருள் ஜோதிடம் — Full Jathagam

## Included
- Tamil responsive birth-details form
- Birth-place geocoding
- Swiss Ephemeris / Lahiri sidereal calculations
- Lagna and Moon Rasi
- Nakshatra + Pada + Lord
- 9 graha positions
- South-Indian-style 12-sign display
- Navamsa (D9) sign placement
- 12 houses
- Vimshottari dasha sequence seed from Moon nakshatra
- Call and WhatsApp buttons

## Run locally
```bash
pip install pyswisseph
python server.py
```
Open `http://127.0.0.1:8000` after serving the HTML from the same web origin.

## Production
Use HTTPS and a production server/reverse proxy. Replace `YOUR_PHONE_NUMBER` and `YOUR_WHATSAPP_NUMBER` in the HTML.

The dasha section currently provides the starting sequence and duration seed. For a production-grade report, add exact calendar dates, antardasha/pratyantardasha, ayanamsa settings, and a tested chart-validation suite.
