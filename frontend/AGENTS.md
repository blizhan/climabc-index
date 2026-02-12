# Architecture Decisions

## Project Overview
ENSO (El Niño-Southern Oscillation) climate data visualization dashboard.

## Tech Stack
- **Framework**: React + TypeScript
- **Chart Library**: ECharts
- **Data Format**: Parquet (Apache Arrow for browser reading)
- **Styling**: Tailwind CSS
- **Deployment**: GitHub Pages

## Key Decisions

### 1. Data Loading Strategy
- Use Apache Arrow JS to read Parquet files directly in browser
- No backend required, fully client-side
- Mock data for development, real data in production

### 2. State Management
- React Context for global state (selected metrics, time range)
- Local state for component-specific UI

### 3. Chart Configuration
- ECharts with dataZoom for time range selection
- Multiple Y-axes for different metric scales
- Dynamic series toggle

### 4. File Structure
```
src/
├── components/     # UI components
├── hooks/         # Custom React hooks
├── utils/         # Utility functions
└── types/         # TypeScript definitions
```

## Constraints
- Must work on GitHub Pages (static hosting)
- Weekly data updates
- Decades of monthly data
