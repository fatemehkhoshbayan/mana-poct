# Mana POCT — Front End

React + TypeScript web app built with Vite and Tailwind CSS.

## Stack

- **React 19** with TypeScript
- **Vite 8** for dev server and production builds
- **Tailwind CSS 4** via `@tailwindcss/vite`
- **ESLint** for linting
- **Prettier** with `prettier-plugin-tailwindcss` for formatting

## Getting started

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |
| `npm run prettier` | Format source files with Prettier |
| `npm run check-format` | Check formatting without writing changes |

## Project layout

```
front-end/
├── src/
│   ├── App.tsx       # Root component
│   ├── main.tsx      # App entry point
│   └── index.css     # Tailwind imports
├── eslint.config.js
├── vite.config.ts
└── .prettierrc.json
```

Path aliases: `@/` maps to `src/` (configured in `vite.config.ts`).

## Tooling

**ESLint** — flat config in `eslint.config.js` with TypeScript, React Hooks, and React Refresh rules.

**Prettier** — config in `.prettierrc.json`. Tailwind classes are sorted automatically via `prettier-plugin-tailwindcss`.

**lint-staged** — on commit, JS/TS files are linted with ESLint and formatted with Prettier; other supported files are formatted only.

## Build

```bash
npm run build
```

Output is written to `dist/`.
