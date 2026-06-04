# Refreshed App Store / Play Store Screenshots — Feb 2026

Generated screenshot suite matching the new purple → teal SACOParents brand and the latest dashboard / wizard / reflection / safety surfaces.

## Asset map

| Folder | Size | Where to upload |
|---|---|---|
| `iphone_6_7/` | 1290×2796 | App Store Connect — iPhone 6.7" (iPhone 15/14 Pro Max). **Required.** |
| `iphone_6_5/` | 1242×2688 | App Store Connect — iPhone 6.5" (Xs Max). Recommended for backward compatibility. |
| `ipad_12_9/` | 2048×2732 | App Store Connect — iPad Pro 12.9". Only needed if you're publishing the iPad app. |
| `android_phone/` | 1080×1920 | Google Play Console — Phone screenshots. |
| `play_feature_graphic/feature_graphic.png` | 1024×500 | Google Play Console — Feature Graphic (the wide banner on the listing). |
| `raw/` | 1290×2796 | Just the unframed app UI. Source for the composer. Don't upload these. |

## Screen list (in the order they should appear)

1. **01_dashboard** — _"Your space, ready when you are"_
2. **02_child_goals** — _"Keep your children at the center"_
3. **03_communication** — _"Reframe before you react"_
4. **04_summary** — _"AI-prepared mediation summary in minutes"_
5. **05_reflection** — _"Quiet space for honest reflection"_
6. **06_safety** — _"Help is always one tap away"_

Apple allows 3–10. Play Store allows up to 8. Six is a good middle.

## Captions
Defined in `refresh_compose.py` → `CAPTIONS` dict. Edit + re-run to change.

## Regenerating
```bash
cd /app/memory/app_store_assets
# 1. Capture fresh mobile UI screenshots from preview env
PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python refresh_capture.py

# 2. Compose marketing-framed screenshots for every store size
python refresh_compose.py
```

The capture script logs into the admin test account, sets localStorage to dismiss the Legal Acknowledgment + Verification banner + Orientation gate, then screenshots each route at iPhone 6.7" pixel-perfect resolution.

The composer:
- Draws a brand purple→magenta→teal gradient with soft accent blobs
- Adds a 2-line headline + small `SACOPARENTS · RELATIONAL MEDIATION PREP` eyebrow tag
- Frames the captured UI in a charcoal phone shell with rounded corners + dynamic-island notch
- Drops a soft shadow under the phone for depth

## Old assets
The previous (pre-rebrand) screenshots are still in their original folders (`screenshots/`, `ios_6_5_inch_screenshots/`, `ios_6_7_inch_screenshots/`, etc.) — keep them as a backup until App Store review approves the new build.
