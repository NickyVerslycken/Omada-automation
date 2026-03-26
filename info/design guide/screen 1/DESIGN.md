# Design System Document

## 1. Overview & Creative North Star: "The Digital Cartographer"

In the complex landscape of network management, clarity is not enough; we require authority. This design system departs from the cluttered, "grey-box" aesthetic of traditional network GUIs (as seen in legacy desktop tools) and moves toward **The Digital Cartographer**. This North Star focuses on precision, layered depth, and an editorial hierarchy that treats network data as a premium asset.

The system breaks the "template" look through:
*   **Intentional Asymmetry:** Using sidebar navigation and staggered content headers to avoid the rigid, centered-column feel.
*   **Tonal Authority:** Replacing 1px borders with shifts in surface luminance to define space.
*   **High-Contrast Scale:** Using oversized `display` typography for status metrics, contrasted with tight, functional `label` typography for technical data.

---

## 2. Colors

The palette is a sophisticated blend of deep enterprise blues (`primary`), tactical teals (`secondary`), and a meticulously graded neutral scale.

### The "No-Line" Rule
Traditional interfaces use borders to separate sections, creating visual noise. **This design system prohibits 1px solid borders for sectioning.** Boundaries must be defined solely through:
1.  **Background Color Shifts:** Placing a `surface-container-low` component on a `surface` background.
2.  **Shadow Depth:** Using ambient shadows to indicate elevation without lines.

### Surface Hierarchy & Nesting
We treat the UI as stacked layers. Importance is conveyed through "The Nesting Principle":
*   **Base:** `surface` (#f8f9fb)
*   **Sectioning:** `surface-container-low` (#f3f4f6)
*   **Interactive Cards:** `surface-container-lowest` (#ffffff)
*   **Elevated Overlays:** `surface-bright` (#f8f9fb)

### Glass & Gradient Rule
Floating elements (e.g., dropdowns, tooltips, or temporary status modals) must use **Glassmorphism**. Apply a semi-transparent `surface` color with a 12px backdrop-blur. 
*   **Signature Texture:** Main Action buttons or Data "Hero" headers should use a subtle linear gradient from `primary` (#00408f) to `primary_container` (#0056bd) at a 135-degree angle to add depth.

---

## 3. Typography

The system utilizes two typefaces: **Manrope** for expressive headers and **Inter** for technical density.

*   **Display & Headline (Manrope):** Chosen for its geometric precision. Use `display-lg` for network-wide totals and `headline-sm` for section titles.
*   **Title, Body, & Label (Inter):** Chosen for its exceptional legibility at small sizes. 
    *   `title-sm` (1rem) is the standard for form labels and table headers.
    *   `label-md` (0.75rem) is used for technical metadata (MAC addresses, IP ranges).

**The Editorial Shift:** To emphasize hierarchy, use `on_surface_variant` (#434654) for labels and `on_surface` (#191c1e) for data values. This creates an immediate visual scan path.

---

## 4. Elevation & Depth

We move away from the flat, "old-fashioned desktop" feel by using **Tonal Layering**.

*   **The Layering Principle:** Depth is achieved by "stacking." A Batch Operation form should be a `surface-container-lowest` card sitting on a `surface-container-low` background. This creates a soft, natural lift.
*   **Ambient Shadows:** For floating elements like Sidebar Nav or Modals, use:
    *   `blur`: 24px | `spread`: 0px | `opacity`: 6% | `color`: `on_surface` (#191c1e).
*   **The "Ghost Border" Fallback:** If accessibility requires a container boundary, use `outline_variant` (#c3c6d6) at **15% opacity**. Never use 100% opaque borders.

---

## 5. Components

### Robust Data Tables
*   **Separation:** Forbid horizontal divider lines. Use `surface_container_low` for the header row and vertical padding (`spacing-4`) to separate rows.
*   **Status Indicators:** Use `tertiary_container` for "Connected" states and `error_container` for "Critical" states. These should be pills with `label-sm` text.

### Sidebar Navigation
*   **Scalability:** The sidebar is a fixed width (280px) using `surface_container_low`. 
*   **Active State:** Use a vertical "accent bar" (4px width) of `primary` on the far left of the active item, with the item background shifting to `surface_container_highest`.

### Form Layouts (Batch Operations)
*   **Structure:** Group batch parameters into logical sets using white space (`spacing-10`) rather than lines.
*   **Inputs:** `surface_container_highest` background with a `ghost border` on focus.
*   **Buttons:**
    *   **Primary:** Gradient of `primary` to `primary_container`, `rounded-md`.
    *   **Secondary:** `on_primary_fixed` text on a `primary_fixed` background. No border.

### Chips & Tags
*   Use `secondary_container` (#6ae1ff) for network tags (e.g., VLAN IDs). Text should be `on_secondary_container`. Use `rounded-full` for a modern, SaaS aesthetic.

---

## 6. Do's and Don'ts

### Do:
*   **DO** use whitespace as a functional tool. If elements feel crowded, increase spacing using the `spacing-8` or `spacing-10` tokens.
*   **DO** use "surface-container" tiers to group related form fields.
*   **DO** use `inter` for all numeric data; its tabular figures ensure IP addresses and subnet masks align perfectly.

### Don't:
*   **DON'T** use black (#000000) for text or shadows. Use `on_surface` for text and tinted opacities for shadows.
*   **DON'T** use 1px borders to separate the sidebar from the main content; use the tonal shift between `surface_container_low` and `surface`.
*   **DON'T** use "Standard" blue. Always use the specified `primary` (#00408f) which is deeper and more "enterprise-grade" than default web blue.