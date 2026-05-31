# Real-data policy local visual smoke check

Date: 2026-05-28
Environment: local production server (`npm run start`), `http://localhost:3000`

## Checked routes

| Route | Result | Notes |
|---|---:|---|
| `/ka` | Pass | Georgian-first portal shell loads. The primary dashboard shows the real-data rule and repeated `მონაცემი არ არის` fallbacks instead of hardcoded factual/placeholder content. |
| `/ka/resources` | Pass | Doctor brief/resources page states that the brief cannot be generated without real data and uses `მონაცემი არ არის` in evidence/risk/question sections. |

## Observed policy behavior

The UI consistently communicates that it displays only source-confirmed data. Where no source-confirmed records exist, the page text shows `მონაცემი არ არის`. The research/medical boundary is visible: the portal says it does not diagnose and does not provide medical recommendations. The Doctor Brief CTA is disabled/unavailable until real evidence, risk, and doctor-question data are present.

## Browser artifacts

- `/ka` screenshot: `/home/ubuntu/screenshots/localhost_2026-05-28_20-59-19_1885.webp`
- `/ka/resources` screenshot: `/home/ubuntu/screenshots/localhost_2026-05-28_20-59-31_7997.webp`
- Extracted text: `/home/ubuntu/page_texts/localhost_3000_ka.md`, `/home/ubuntu/page_texts/localhost_3000_ka_resources.md`

## Conclusion

Local production visual smoke check passes for the real-data/no-data policy before GitHub push.
