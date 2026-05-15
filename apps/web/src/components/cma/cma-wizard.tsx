'use client';

import React, { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { StepSubject } from './step-subject';
import { StepComparables } from './step-comparables';
import { StepAdjustments } from './step-adjustments';
import { StepPreview } from './step-preview';
import { StepExport } from './step-export';
import type { Property, CMAComparable, CMAReport } from '@/lib/types';

interface CMAWizardState {
  currentStep: number;
  subjectPropertyId: string | null;
  subjectProperty: Property | null;
  comparables: CMAComparable[];
  report: CMAReport | null;
  isLoading: boolean;
  error: string | null;
}

const STEP_KEYS = ['subject', 'comparables', 'adjustments', 'preview', 'export'] as const;

export function CMAWizard() {
  const t = useTranslations('cma');
  const [state, setState] = useState<CMAWizardState>({
    currentStep: 1,
    subjectPropertyId: null,
    subjectProperty: null,
    comparables: [],
    report: null,
    isLoading: false,
    error: null,
  });

  const updateState = useCallback((updates: Partial<CMAWizardState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  const goToStep = useCallback((step: number) => {
    setState((prev) => ({ ...prev, currentStep: step, error: null }));
  }, []);
  void goToStep;

  const nextStep = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.min(prev.currentStep + 1, STEP_KEYS.length),
      error: null,
    }));
  }, []);

  const prevStep = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.max(prev.currentStep - 1, 1),
      error: null,
    }));
  }, []);

  const resetWizard = useCallback(() => {
    setState({
      currentStep: 1,
      subjectPropertyId: null,
      subjectProperty: null,
      comparables: [],
      report: null,
      isLoading: false,
      error: null,
    });
  }, []);

  const renderStep = () => {
    switch (state.currentStep) {
      case 1:
        return (
          <StepSubject
            subjectPropertyId={state.subjectPropertyId}
            subjectProperty={state.subjectProperty}
            onPropertySelect={(property) => {
              updateState({
                subjectPropertyId: property.id || null,
                subjectProperty: property,
              });
            }}
            onNext={nextStep}
            canProceed={!!state.subjectProperty}
          />
        );
      case 2:
        return (
          <StepComparables
            subjectPropertyId={state.subjectPropertyId}
            selectedComparables={state.comparables}
            onComparablesChange={(comparables) => updateState({ comparables })}
            onNext={nextStep}
            onPrev={prevStep}
          />
        );
      case 3:
        return (
          <StepAdjustments
            comparables={state.comparables}
            onComparablesChange={(comparables) => updateState({ comparables })}
            onNext={nextStep}
            onPrev={prevStep}
          />
        );
      case 4:
        return (
          <StepPreview
            subjectProperty={state.subjectProperty}
            comparables={state.comparables}
            report={state.report}
            onReportGenerated={(report) => updateState({ report })}
            onNext={nextStep}
            onPrev={prevStep}
          />
        );
      case 5:
        return <StepExport report={state.report} onReset={resetWizard} onPrev={prevStep} />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Stepper */}
      <div className="flex items-center justify-between mb-8">
        {STEP_KEYS.map((stepKey, index) => {
          const stepId = index + 1;
          return (
            <React.Fragment key={stepId}>
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                    state.currentStep === stepId
                      ? 'bg-primary text-primary-foreground'
                      : state.currentStep > stepId
                        ? 'bg-primary/20 text-primary'
                        : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {state.currentStep > stepId ? (
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  ) : (
                    stepId
                  )}
                </div>
                <span
                  className={`text-xs mt-2 text-center max-w-[80px] ${
                    state.currentStep === stepId
                      ? 'text-primary font-medium'
                      : 'text-muted-foreground'
                  }`}
                >
                  {t(`steps.${stepKey}.title`)}
                </span>
              </div>
              {index < STEP_KEYS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 ${
                    state.currentStep > stepId ? 'bg-primary/20' : 'bg-muted'
                  }`}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Error display */}
      {state.error && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md" role="alert">
          {state.error}
        </div>
      )}

      {/* Step content */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            {t(`steps.${STEP_KEYS[state.currentStep - 1]}.title`)}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {t(`steps.${STEP_KEYS[state.currentStep - 1]}.description`)}
          </p>
        </CardHeader>
        <CardContent>{renderStep()}</CardContent>
      </Card>
    </div>
  );
}
