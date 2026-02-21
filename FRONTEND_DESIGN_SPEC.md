# FreeFood UCD - Frontend Design Specification

## 🎨 Design Philosophy

**Inspiration**: Notion, Splitwise, Monzo  
**Style**: Minimal, utility-focused, professional  
**Priority**: Mobile-first, fast, clean

---

## 📐 Visual Design System

### Color Palette

```css
/* Base Colors */
--background: #f9fafb;        /* Very light grey background */
--surface: #ffffff;           /* White cards */
--border: #e5e7eb;            /* Subtle borders */
--text-primary: #111827;      /* Dark grey text */
--text-secondary: #6b7280;    /* Medium grey text */
--text-tertiary: #9ca3af;     /* Light grey text */

/* Accent Colors */
--accent-green: #10b981;      /* Free food badge */
--accent-green-light: #d1fae5; /* Badge background */
--accent-blue: #3b82f6;       /* Links/actions */
--accent-red: #ef4444;        /* Urgent/ending soon */
--accent-amber: #f59e0b;      /* Warnings */
```

### Typography

```css
/* Font Family */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Font Sizes */
--text-xs: 0.75rem;    /* 12px - timestamps, labels */
--text-sm: 0.875rem;   /* 14px - secondary text */
--text-base: 1rem;     /* 16px - body text */
--text-lg: 1.125rem;   /* 18px - card titles */
--text-xl: 1.25rem;    /* 20px - section headers */
--text-2xl: 1.5rem;    /* 24px - page titles */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### Spacing System

```css
/* Consistent spacing scale */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
```

### Border Radius

```css
--radius-sm: 0.375rem;   /* 6px - small elements */
--radius-md: 0.5rem;     /* 8px - buttons */
--radius-lg: 0.75rem;    /* 12px - cards */
--radius-xl: 1rem;       /* 16px - large cards */
--radius-2xl: 1.5rem;    /* 24px - modals */
--radius-full: 9999px;   /* Pills/badges */
```

### Shadows

```css
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
```

---

## 📱 Layout Structure

### Mobile-First Approach

```
┌─────────────────────────┐
│   Header (Fixed)        │ 64px
├─────────────────────────┤
│   Filter Bar            │ Auto
├─────────────────────────┤
│                         │
│   Event Feed            │
│   (Vertical Scroll)     │
│                         │
│   ┌─────────────────┐   │
│   │  Event Card     │   │
│   └─────────────────┘   │
│                         │
│   ┌─────────────────┐   │
│   │  Event Card     │   │
│   └─────────────────┘   │
│                         │
└─────────────────────────┘
```

### Responsive Breakpoints

```css
/* Mobile First */
@media (min-width: 640px)  { /* sm - tablets */ }
@media (min-width: 768px)  { /* md - small laptops */ }
@media (min-width: 1024px) { /* lg - desktops */ }
```

---

## 🧩 Component Specifications

### 1. Header Component

**Purpose**: App branding and navigation  
**Height**: 64px (fixed)  
**Background**: White with subtle shadow

```tsx
<header className="fixed top-0 w-full bg-white border-b border-gray-200 z-50">
  <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
    <div className="flex items-center gap-2">
      <span className="text-2xl">🍕</span>
      <h1 className="text-xl font-semibold text-gray-900">FreeFood UCD</h1>
    </div>
    <button className="text-sm font-medium text-blue-600">
      Sign Up
    </button>
  </div>
</header>
```

**Visual**:
- Logo: 🍕 emoji (24px)
- Title: "FreeFood UCD" (20px, semibold)
- Right: "Sign Up" button (text link style)

---

### 2. Filter Bar Component

**Purpose**: Quick filtering of events  
**Position**: Below header, sticky  
**Background**: Light grey (#f9fafb)

```tsx
<div className="sticky top-16 bg-gray-50 border-b border-gray-200 z-40">
  <div className="max-w-7xl mx-auto px-4 py-3">
    <div className="flex gap-2 overflow-x-auto scrollbar-hide">
      <FilterChip active>All</FilterChip>
      <FilterChip>Today</FilterChip>
      <FilterChip>Tomorrow</FilterChip>
      <FilterChip>This Week</FilterChip>
    </div>
  </div>
</div>
```

**FilterChip Component**:
```tsx
// Active state
<button className="px-4 py-2 rounded-full bg-gray-900 text-white text-sm font-medium whitespace-nowrap">
  Today
</button>

// Inactive state
<button className="px-4 py-2 rounded-full bg-white text-gray-700 text-sm font-medium border border-gray-200 whitespace-nowrap">
  Tomorrow
</button>
```

---

### 3. Event Card Component

**Purpose**: Display individual free food event  
**Layout**: Vertical card with clear hierarchy  
**Spacing**: 16px padding, 12px gap between elements

```tsx
<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-3">
  {/* Header */}
  <div className="flex items-start justify-between mb-3">
    <div className="flex-1">
      <div className="flex items-center gap-2 mb-1">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          🍕 Free Food
        </span>
        <span className="text-xs text-gray-500">2h ago</span>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 leading-tight">
        Pizza & Refreshments
      </h3>
    </div>
  </div>

  {/* Society */}
  <div className="flex items-center gap-2 mb-3">
    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
      <span className="text-sm">⚖️</span>
    </div>
    <span className="text-sm font-medium text-gray-700">UCD Law Society</span>
  </div>

  {/* Details */}
  <div className="space-y-2 mb-3">
    <div className="flex items-center gap-2 text-sm text-gray-600">
      <span className="text-gray-400">📍</span>
      <span>Newman Building, Room A105</span>
    </div>
    <div className="flex items-center gap-2 text-sm text-gray-600">
      <span className="text-gray-400">🕒</span>
      <span>Today at 6:00 PM</span>
    </div>
  </div>

  {/* Footer */}
  <div className="flex items-center justify-between pt-3 border-t border-gray-100">
    <span className="text-xs text-gray-500">From Instagram Story</span>
    <button className="text-sm font-medium text-blue-600">
      View Details →
    </button>
  </div>
</div>
```

**Card States**:

1. **Default**: White background, subtle shadow
2. **Ending Soon** (< 1 hour): Amber left border (4px)
3. **Happening Now**: Green left border (4px)
4. **Past Event**: Reduced opacity (0.6), greyed out

---

### 4. Empty State Component

**Purpose**: Show when no events match filters  
**Style**: Centered, minimal, friendly

```tsx
<div className="flex flex-col items-center justify-center py-16 px-4">
  <div className="text-6xl mb-4">🔍</div>
  <h3 className="text-lg font-semibold text-gray-900 mb-2">
    No events found
  </h3>
  <p className="text-sm text-gray-500 text-center max-w-sm">
    There are no free food events matching your filters right now.
    Check back soon!
  </p>
</div>
```

---

### 5. Loading State Component

**Purpose**: Show while fetching data  
**Style**: Skeleton screens matching card layout

```tsx
<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-3 animate-pulse">
  <div className="flex items-start justify-between mb-3">
    <div className="flex-1">
      <div className="h-5 bg-gray-200 rounded w-24 mb-2"></div>
      <div className="h-6 bg-gray-200 rounded w-3/4"></div>
    </div>
  </div>
  <div className="flex items-center gap-2 mb-3">
    <div className="w-8 h-8 rounded-full bg-gray-200"></div>
    <div className="h-4 bg-gray-200 rounded w-32"></div>
  </div>
  <div className="space-y-2">
    <div className="h-4 bg-gray-200 rounded w-full"></div>
    <div className="h-4 bg-gray-200 rounded w-2/3"></div>
  </div>
</div>
```

---

### 6. Society Filter Modal

**Purpose**: Filter events by specific societies  
**Trigger**: "Filter by Society" button in filter bar  
**Style**: Bottom sheet on mobile, modal on desktop

```tsx
<div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center sm:justify-center">
  <div className="bg-white rounded-t-2xl sm:rounded-2xl w-full sm:max-w-md max-h-[80vh] overflow-hidden">
    {/* Header */}
    <div className="flex items-center justify-between p-4 border-b border-gray-200">
      <h2 className="text-lg font-semibold text-gray-900">Filter by Society</h2>
      <button className="text-gray-400 hover:text-gray-600">✕</button>
    </div>

    {/* Search */}
    <div className="p-4 border-b border-gray-200">
      <input
        type="text"
        placeholder="Search societies..."
        className="w-full px-4 py-2 rounded-lg border border-gray-300 text-sm"
      />
    </div>

    {/* Society List */}
    <div className="overflow-y-auto max-h-96">
      <label className="flex items-center gap-3 p-4 hover:bg-gray-50 cursor-pointer">
        <input type="checkbox" className="w-4 h-4 rounded border-gray-300" />
        <div className="flex items-center gap-2 flex-1">
          <span className="text-sm">⚖️</span>
          <span className="text-sm font-medium text-gray-900">UCD Law Society</span>
        </div>
        <span className="text-xs text-gray-500">12 events</span>
      </label>
      {/* More societies... */}
    </div>

    {/* Footer */}
    <div className="p-4 border-t border-gray-200 flex gap-2">
      <button className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700">
        Clear All
      </button>
      <button className="flex-1 px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium">
        Apply Filters
      </button>
    </div>
  </div>
</div>
```

---

### 7. Notification Signup Component

**Purpose**: Collect user info for WhatsApp/Email notifications  
**Style**: Clean form with clear value proposition

```tsx
<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-4">
  <div className="text-center mb-6">
    <div className="text-4xl mb-3">🔔</div>
    <h2 className="text-xl font-semibold text-gray-900 mb-2">
      Never Miss Free Food
    </h2>
    <p className="text-sm text-gray-600">
      Get instant WhatsApp or email alerts when free food is posted
    </p>
  </div>

  <form className="space-y-4">
    {/* Phone Number */}
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        WhatsApp Number
      </label>
      <div className="flex gap-2">
        <select className="px-3 py-2 rounded-lg border border-gray-300 text-sm">
          <option>🇮🇪 +353</option>
        </select>
        <input
          type="tel"
          placeholder="87 123 4567"
          className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-sm"
        />
      </div>
    </div>

    {/* Email (Optional) */}
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Email (Optional)
      </label>
      <input
        type="email"
        placeholder="your.email@ucd.ie"
        className="w-full px-4 py-2 rounded-lg border border-gray-300 text-sm"
      />
    </div>

    {/* Submit */}
    <button className="w-full px-4 py-3 rounded-lg bg-gray-900 text-white text-sm font-medium">
      Start Getting Alerts
    </button>

    <p className="text-xs text-gray-500 text-center">
      We'll send you a verification message. Standard rates may apply.
    </p>
  </form>
</div>
```

---

## 🎯 Interaction Patterns

### Tap Targets
- Minimum: 44x44px (iOS guideline)
- Buttons: 48px height minimum
- Cards: Full card tappable

### Animations
```css
/* Subtle, fast transitions */
transition: all 150ms ease-in-out;

/* Card hover (desktop only) */
@media (hover: hover) {
  .event-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}
```

### Loading States
- Skeleton screens (no spinners)
- Fade-in when content loads
- Optimistic UI updates

---

## 📊 Event Card Variants

### 1. Standard Event
```
┌─────────────────────────────┐
│ 🍕 Free Food    2h ago      │
│ Pizza & Refreshments        │
│                             │
│ ⚖️ UCD Law Society          │
│                             │
│ 📍 Newman Building, A105    │
│ 🕒 Today at 6:00 PM         │
│                             │
│ From Story    View Details →│
└─────────────────────────────┘
```

### 2. Happening Now (Green Border)
```
┃ ┌───────────────────────────┐
┃ │ 🍕 Free Food  LIVE        │
┃ │ Pizza in Student Centre   │
┃ │                           │
┃ │ 🎓 UCD Students' Union    │
┃ │                           │
┃ │ 📍 Student Centre         │
┃ │ 🕒 Happening Now          │
┃ │                           │
┃ │ From Post   View Details →│
┃ └───────────────────────────┘
```

### 3. Ending Soon (Amber Border)
```
┃ ┌───────────────────────────┐
┃ │ 🍕 Free Food  ⚠️ 30 min   │
┃ │ Last chance for pizza!    │
┃ │                           │
┃ │ 🎭 Drama Society          │
┃ │                           │
┃ │ 📍 Arts Building          │
┃ │ 🕒 Ends at 7:00 PM        │
┃ │                           │
┃ │ From Story   View Details →│
┃ └───────────────────────────┘
```

---

## 🚫 What to Avoid

### ❌ Don't Use:
- Gradients
- Multiple bright colors
- Heavy shadows
- Decorative illustrations
- Social media-style interactions (likes, comments)
- Infinite scroll (use pagination)
- Auto-playing videos
- Pop-ups or interstitials

### ✅ Do Use:
- Flat colors
- Subtle shadows
- Clear typography hierarchy
- Functional icons (emoji or simple SVG)
- Pull-to-refresh
- Clear loading states
- Accessible contrast ratios

---

## ♿ Accessibility Requirements

### Color Contrast
- Text: Minimum 4.5:1 ratio
- Large text: Minimum 3:1 ratio
- Interactive elements: Clear focus states

### Keyboard Navigation
- All interactive elements focusable
- Logical tab order
- Visible focus indicators

### Screen Readers
- Semantic HTML
- ARIA labels where needed
- Alt text for images

### Touch Targets
- Minimum 44x44px
- Adequate spacing between elements

---

## 📱 Mobile Optimizations

### Performance
- Lazy load images
- Virtual scrolling for long lists
- Debounced search
- Optimistic UI updates

### Gestures
- Pull-to-refresh
- Swipe to dismiss modals
- Tap to expand cards

### Native Feel
- Smooth 60fps animations
- Haptic feedback (where supported)
- Safe area insets (iOS notch)

---

## 🎨 Component Library

### Recommended: shadcn/ui
- Unstyled, accessible components
- Copy-paste into project
- Full customization
- Tailwind CSS based

### Key Components Needed:
- Button
- Input
- Select
- Checkbox
- Dialog/Modal
- Sheet (bottom drawer)
- Badge
- Card

---

## 📐 Spacing & Layout Grid

### Container
```css
.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 1rem; /* 16px */
}

@media (min-width: 640px) {
  .container { padding: 0 1.5rem; } /* 24px */
}
```

### Card Grid (Desktop)
```css
@media (min-width: 768px) {
  .event-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
}

@media (min-width: 1024px) {
  .event-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

## 🎯 Key Screens

### 1. Home / Event Feed
- Header (fixed)
- Filter bar (sticky)
- Event cards (scrollable)
- Empty state (if no events)

### 2. Event Detail (Modal/Sheet)
- Full event information
- Map/directions
- Share button
- "Add to Calendar" button

### 3. Signup Flow
- Phone number input
- Verification code
- Society preferences
- Success confirmation

### 4. Settings/Preferences
- Notification preferences
- Society filters
- Account management

---

## 🔧 Implementation Notes

### Tech Stack
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **State**: Zustand (lightweight)
- **Data Fetching**: React Query
- **Forms**: React Hook Form
- **Validation**: Zod

### File Structure
```
src/
├── app/
│   ├── page.tsx              # Home/Feed
│   ├── layout.tsx            # Root layout
│   └── globals.css           # Global styles
├── components/
│   ├── ui/                   # shadcn components
│   ├── EventCard.tsx
│   ├── FilterBar.tsx
│   ├── Header.tsx
│   └── SignupForm.tsx
├── lib/
│   ├── api.ts                # API client
│   └── utils.ts              # Utilities
└── types/
    └── index.ts              # TypeScript types
```

---

## 🎨 Design Tokens (Tailwind Config)

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#10b981',  // Main green
          600: '#059669',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.1)',
      }
    }
  }
}
```

---

This design system ensures a clean, professional, utility-focused interface that prioritizes speed and usability over visual flair.