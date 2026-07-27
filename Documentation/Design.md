# Pearls AQI Predictor - Design System

## 1. Theme & Concept
The dashboard should feel clean, modern, data-centric, and premium. It must inspire confidence through clear visual hierarchy. It should support both Light and Dark modes, leveraging glassmorphism (translucent, blurred backgrounds) for widgets and cards to give it a modern 100% serverless, cloud-native feel.

## 2. Color Palette
Colors are categorized by AQI health levels and UI structure:
- **Primary Brand:** Air Blue `#4A90E2` (Used for headers, primary buttons)
- **Backgrounds:**
  - Light Mode: Off-white `#F8F9FA`
  - Dark Mode: Dark Charcoal `#121212` / `#1E1E1E`
- **AQI Indicator Colors:**
  - Good (0-50): Leaf Green `#50E3C2`
  - Moderate (51-100): Yellow `#F5A623`
  - Unhealthy for Sensitive (101-150): Orange `#F57C00`
  - Unhealthy (151-200): Red `#D0021B`
  - Very Unhealthy / Hazardous (201+): Deep Purple `#9013FE`

## 3. Typography
- **Primary Font (Headings):** *Inter* or *Outfit* - Clean, sans-serif, provides a highly legible and modern aesthetic.
- **Secondary Font (Body):** *Roboto* or *Open Sans* - highly readable for longer text and explanations.
- **Monospace (Data/Metrics):** *Fira Code* or *JetBrains Mono* - ideal for displaying raw numerical data, feature importance scores, and code blocks.

## 4. UI Elements & Micro-interactions
- **Cards & Widgets:** Use subtle drop shadows and rounded corners (e.g., `border-radius: 12px`).
- **Animations:** Subtle fade-ins when data loads, smooth transitions when toggling between models or days, and hover effects on prediction cards.
- **Alerts:** Hazardous AQI levels should trigger highly visible, bold alerts (using the Red or Purple color palette) with clear iconography (e.g., warning triangles).
- **Charts:** Use smooth, gradient-filled area charts for forecasting trends. Tooltips on hover should clearly state the date, time, and exact predicted AQI value.
