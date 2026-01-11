import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MortgageCalculator } from "../mortgage-calculator";
import { calculateMortgage } from "@/lib/api";

jest.mock("@/lib/api");

describe("MortgageCalculator", () => {
  const mockResult = {
    monthly_payment: 2533.43,
    total_interest: 412033.64,
    total_cost: 912033.64,
    down_payment: 100000,
    loan_amount: 400000,
    breakdown: { principal: 1000, interest: 1533.43 },
  };

  beforeEach(() => {
    (calculateMortgage as jest.Mock).mockReset();
  });

  it("renders the form", () => {
    render(<MortgageCalculator />);
    expect(screen.getByLabelText(/Property Price/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Down Payment/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Interest Rate/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Loan Term/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Calculate/i })).toBeInTheDocument();
  });

  it("calculates mortgage on submit", async () => {
    (calculateMortgage as jest.Mock).mockResolvedValueOnce(mockResult);

    render(<MortgageCalculator />);

    fireEvent.click(screen.getByRole("button", { name: /Calculate/i }));

    expect(screen.getByRole("button", { name: /Calculate/i })).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText("Results")).toBeInTheDocument();
      expect(screen.getByText("$2,533.43")).toBeInTheDocument();
    });

    expect(calculateMortgage).toHaveBeenCalledWith({
      property_price: 500000,
      down_payment_percent: 20,
      interest_rate: 4.5,
      loan_years: 30,
    });
  });

  it("handles errors", async () => {
    (calculateMortgage as jest.Mock).mockRejectedValueOnce(new Error("API Error"));

    render(<MortgageCalculator />);

    fireEvent.click(screen.getByRole("button", { name: /Calculate/i }));

    await waitFor(() => {
      expect(screen.getByText("Failed to calculate mortgage. Please check your inputs.")).toBeInTheDocument();
    });
  });

  it("updates inputs", () => {
    render(<MortgageCalculator />);
    const priceInput = screen.getByLabelText(/Property Price/i);
    fireEvent.change(priceInput, { target: { value: "600000" } });
    expect(priceInput).toHaveValue(600000);
  });
});
