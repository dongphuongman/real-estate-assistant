import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] bg-background">
      <div className="container px-4 md:px-6 flex flex-col items-center text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl">
          AI Real Estate Assistant
        </h1>
        <p className="mx-auto max-w-[700px] text-muted-foreground md:text-xl">
          Intelligent property search, market analytics, and investment insights powered by advanced AI.
        </p>
        <div className="flex gap-4">
          <Link
            href="/search"
            className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          >
            Start Searching
          </Link>
          <Link
            href="/chat"
            className="inline-flex h-10 items-center justify-center rounded-md border border-input bg-background px-8 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 gap-2"
          >
            Ask Assistant <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
