---
name: Culinary Intelligence System
colors:
  surface: '#fbf9f8'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#e9e8e7'
  surface-container-highest: '#e4e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#5b403f'
  inverse-surface: '#303031'
  inverse-on-surface: '#f2f0f0'
  outline: '#8f6f6e'
  outline-variant: '#e4bebc'
  surface-tint: '#bb162c'
  primary: '#b7122a'
  on-primary: '#ffffff'
  primary-container: '#db313f'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb3b1'
  secondary: '#5f5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e2dfde'
  on-secondary-container: '#636262'
  tertiary: '#5b5c5c'
  on-tertiary: '#ffffff'
  tertiary-container: '#737575'
  on-tertiary-container: '#fcfcfc'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1b1b1b'
  on-secondary-fixed-variant: '#474746'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#fbf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e2'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 60px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1200px
  split-form: 40%
  split-results: 60%
  gutter: 32px
  margin-page: 24px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
---

## Brand & Style

This design system is built to balance high-utility data input with the sensory delight of food discovery. The brand personality is **Professional, Curated, and Appetizing**. It moves away from cluttered marketplace aesthetics toward a focused, AI-driven concierge experience.

The visual style is **Corporate Modern with Tactile Warmth**. It utilizes generous whitespace, a sophisticated neutral palette, and high-quality typography to ensure the AI's recommendations feel trustworthy and premium. While the interface is clean and systematic, the use of the signature primary red provides the necessary energy and appetite-triggering warmth expected from a leader in the food-tech space.

## Colors

The palette is anchored by the signature red, used purposefully for primary actions and brand presence. 

- **Primary Red:** Reserved for the "Primary Action" button, active states of filter chips, and key brand accents.
- **Surface Strategy:** The application uses a "Layered White" approach. The main page background is pure white (#FFFFFF), while functional sidebars and form containers use the light gray panel background (#F8F8F8) to create subtle structural distinction without heavy borders.
- **Typography & Icons:** All primary text is set in the deep dark neutral (#1C1C1C) to maintain maximum legibility and a premium feel. Secondary information uses a mid-range neutral (#696969).

## Typography

The typography system relies on **Inter**, a typeface designed for screen legibility and systematic precision.

- **Weight Usage:** Use Bold (700) for page-level headers and Semibold (600) for component titles. Medium (500) is preferred for labels and interactive elements like buttons and chips.
- **Scale:** On desktop, the "display-lg" scale is used sparingly for hero statements. Most interface work is handled by "headline-md" for card titles and "body-md" for general information.
- **Micro-copy:** Labels for inputs and status badges should use "label-sm" with increased letter spacing to maintain clarity at smaller sizes.

## Layout & Spacing

This design system follows a **Desktop-First Fixed Grid** philosophy within a centered container.

- **The 40/60 Split:** The interface is divided into a left-hand configuration panel (40% width) and a right-hand results feed (60% width). The configuration panel should be sticky to allow users to refine inputs while scrolling through recommendations.
- **Rhythm:** A 32px gutter separates the two main columns. Inside the forms and cards, a vertical rhythm of 16px (Medium) or 24px (Large) should be maintained to ensure the "warm and inviting" mood is supported by adequate breathing room.
- **Mobile Reflow:** On screens smaller than 1024px, the layout transitions to a single-column fluid stack, with the configuration panel moving to a collapsible top section or a floating action button modal.

## Elevation & Depth

To maintain a "Consumer-Grade" yet "Professional" feel, the design system avoids heavy shadows in favor of **Soft Ambient Depth**.

- **Level 0 (Flat):** Used for the main background.
- **Level 1 (Subtle):** Used for Recommendation Cards. Shadow: `0px 4px 20px rgba(0, 0, 0, 0.05)`. This creates a soft lift that suggests the card is a tangible object.
- **Interactive State:** Upon hover, a card's elevation should increase slightly with a tighter, darker shadow: `0px 8px 24px rgba(0, 0, 0, 0.08)`.
- **Form Inputs:** Use a 1px solid border (#E8E8E8) rather than shadows to keep the input area feeling crisp and functional.

## Shapes

The shape language is **Refined and Friendly**. 

- **Components:** Standard buttons, input fields, and cards utilize a 0.5rem (8px) corner radius. 
- **Chips & Badges:** Use a "Pill" style (rounded-full) to distinguish them from structural elements like cards and inputs.
- **Visual Continuity:** Rounded corners should be applied consistently to images and skeleton loaders to match the container's aesthetic.

## Components

### Form Inputs
- **Text Areas & Dropdowns:** 1px solid border (#E8E8E8) with 12px padding. Focus state: 1px solid Primary Red with a 2px soft red outer glow.
- **Sliders:** A thick gray track (#F0F0F0) with a Primary Red thumb and active track portion. 

### Recommendation Cards
- **Structure:** 1:1 or 16:9 aspect ratio image at the top, followed by title, rating, and description.
- **Badges:** Small, pill-shaped markers (e.g., "Must Try" or "AI Choice") placed in the top-left corner of the image with a semi-transparent dark background or a solid white background.
- **Ranking:** Use a bold "label-md" rank number (e.g., #1) in the top right of the card.

### Filter Chips
- **Inactive:** White background, 1px gray border, dark text.
- **Active:** Primary Red background, no border, white text.

### Feedback & States
- **Alert Banners:** Full-width at the top of the results column. Warning (Amber background), Error (Soft Red background), Success (Soft Green background). Use 16px padding and left-aligned text.
- **Skeleton Skeletons:** Use the #F8F8F8 gray with a subtle shimmer animation for card images and text lines during AI generation.