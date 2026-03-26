'use client';

import { CMAWizard } from '@/components/cma/cma-wizard';

export default function CMAPage() {
  return (
    <div className="container mx-auto py-6 px-4 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Comparative Market Analysis</h1>
        <p className="text-muted-foreground mt-1">
          Generate professional CMA reports by selecting a subject property and comparable listings.
        </p>
      </div>
      <CMAWizard />
    </div>
  );
}
