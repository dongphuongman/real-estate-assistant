import { render, screen, waitFor } from "@testing-library/react";
import SettingsPage from "../page";
import { getNotificationSettings } from "@/lib/api";

// Mock API
jest.mock("@/lib/api", () => ({
  getNotificationSettings: jest.fn(),
  updateNotificationSettings: jest.fn(),
}));

// Mock child component to simplify integration test
jest.mock("@/components/settings/notification-settings", () => ({
  NotificationSettings: () => <div data-testid="notification-settings">Notification Settings Component</div>,
}));

describe("SettingsPage", () => {
  it("renders page title and description", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Manage your account settings and notification preferences.")).toBeInTheDocument();
  });

  it("renders notification settings section", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Notifications")).toBeInTheDocument();
    expect(screen.getByTestId("notification-settings")).toBeInTheDocument();
  });
});
