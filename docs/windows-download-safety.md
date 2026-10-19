# Windows download safety

## New packaging

RaggaMuffin now uses PyInstaller `--onedir` rather than `--onefile`. The build produces a `RaggaMuffin` directory containing `RaggaMuffin.exe`, its runtime dependencies, and a SHA256 file manifest. This removes PyInstaller's single-file extraction bootloader behavior; it **does not** make an unsigned program inherently trustworthy or ensure SmartScreen/Chrome/Edge acceptance.

## How to obtain

Open the latest successful GitHub Actions **Build Windows EXE** run. Download `RaggaMuffin-Windows-onedir`, extract it to a regular directory, then inspect and scan before running. Keep all extracted files together; the EXE depends on accompanying files.

## Verification

- Do not disable browser protection or Microsoft Defender to get the app running.
- Confirm that the build was from this repository and was successful.
- Scan the extracted directory with Microsoft Defender.
- If antivirus names a Trojan or other specific threat, do not run it. Investigate the detection and the provenance of dependencies.
- SHA256SUMS.txt provides file-integrity checks **within the downloaded artifact**, but is not a publisher signature or independent guarantee of safety.
- If the browser still blocks the artifact, don't override it. You can inspect the source and run it directly via Python from a trusted environment instead.

This application is experimental and currently has no code-signing certificate.
