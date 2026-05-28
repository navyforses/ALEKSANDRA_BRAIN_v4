# Redesign visual smoke check notes

Date: 2026-05-28
Route checked: `http://localhost:3000/ka`
Screenshot: `/home/ubuntu/screenshots/localhost_2026-05-28_19-46-39_7567.webp`

## Key findings

The redesigned Georgian-first shell renders successfully in production mode. The left navigation, sticky top context bar, central Evidence → Risk → Doctor Question hero flow, and right research assistant panel are visible and coherent. The Georgian labels are readable and the research-only disclaimer is visible before the main navigation.

The page content correctly communicates the intended clinical-safety framing: it does not present diagnosis or treatment instructions, and it repeatedly routes the reader toward evidence, uncertainty, and a doctor-facing question.

## Adjustment to make

A horizontal scrollbar appears at the bottom of the viewport in the screenshot. To make the design more robust across viewport widths, add an overflow-x guard to the root/body level.

## Re-check after overflow guard

Route checked again: `http://localhost:3000/ka`
Screenshot: `/home/ubuntu/screenshots/localhost_2026-05-28_19-48-25_7578.webp`

The redesigned content still renders correctly after the CSS guard. The screenshot continues to show a horizontal scrollbar indicator, so the next step is to diagnose the exact overflowing element by comparing document width and element bounding boxes rather than guessing from the screenshot alone.

## Overflow diagnosis and resources route check

DOM diagnosis result: `documentElement.clientWidth`, `documentElement.scrollWidth`, and `body.scrollWidth` all reported `1265`, with no overflowing elements detected. The bottom bar seen in the annotated screenshot is therefore not caused by actual DOM horizontal overflow after the CSS guard.

Route checked: `http://localhost:3000/ka/resources`
Screenshot: `/home/ubuntu/screenshots/localhost_2026-05-28_19-48-54_2825.webp`

The resources page correctly uses the unified redesigned structure. It presents the doctor-facing brief as a safe communication artifact rather than as medical instruction, with Georgian content organized around evidence, uncertainty/risk, and doctor questions.
