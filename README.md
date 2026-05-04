# ista VDM – Home Assistant Integration

HACS-kompatible Custom Integration für das [ista Verbrauchsdatenmonitoring](https://ista-vdm.at).

## Features
- Wärme (kWh)
- Kaltwasser (m³)
- Warmwasser (m³)
- Strom (kWh)
- Gas (m³)
- Jeweils aktueller Monat + Vormonat
- Automatischer täglicher Update

## Installation via HACS
1. HACS → Integrationen → ⋮ → Benutzerdefiniertes Repository
2. URL: `https://github.com/DEIN_USER/ista_vdm`, Kategorie: Integration
3. Installieren & Home Assistant neu starten
4. Einstellungen → Integrationen → + → "ista VDM"
5. E-Mail & Passwort eingeben

## Manuelle Installation
Ordner `custom_components/ista_vdm/` in dein HA-Konfigurationsverzeichnis kopieren.
