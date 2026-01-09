# AI Real Estate Assistant - Frontend

This is the Next.js frontend for the AI Real Estate Assistant (V4).

## Tech Stack

- **Framework**: Next.js 15+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **Utilities**: clsx, tailwind-merge
- **Data Fetching**: Axios (or SWR/TanStack Query in future)

## Getting Started

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Run Development Server**:
    ```bash
    npm run dev
    ```

    Open [http://localhost:3000](http://localhost:3000) with your browser.

    The app proxies `/api` requests to the Python backend running on `http://localhost:8000`.

## Project Structure

- `src/app`: App Router pages and layouts.
- `src/components`: Reusable UI components.
  - `layout`: Structural components (Navbar, Sidebar).
  - `ui`: Primitive components (Buttons, Inputs, etc.).
- `src/lib`: Utility functions and configuration.

## Key Features

- **Search**: Property search interface.
- **Chat**: AI Assistant interaction.
- **Analytics**: Market insights and dashboards.
