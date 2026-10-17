# Research log

## Initial baseline — October 2026

**Hardware:** 2016 Furby Connect (owner confirms possession).

**Verified on owner's device:** Nothing yet. Discovery is the first experiment.

**Known starting points:** Bluefluff and PyFluff document BLE-based work on Furby Connect. Their compatibility with this Windows computer and this specific Furby has not been tested.

## Experiment checklist

- [ ] Verify batteries and normal operation
- [ ] Record Windows and Python versions
- [ ] Scan BLE advertisements and identify likely Furby (avoid publishing device identifiers)
- [ ] Review characteristic UUIDs and connection behavior
- [ ] Create reversible, low-risk control experiments
- [ ] Record observed sensor events

## Design questions

- Can we reliably connect from Windows using Bleak?
- Which commands are supported by the specific firmware?
- What audio paths, if any, allow arbitrary speech versus stock clips?
- How should an external AI's spontaneous actions be bounded?

Do not commit personal Bluetooth addresses, credentials, or private recordings.
