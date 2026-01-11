import { NotificationSettings } from "@/components/settings/notification-settings";

export default function SettingsPage() {
  return (
    <div className="container py-10">
      <div className="flex flex-col space-y-4 mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and notification preferences.
        </p>
      </div>
      
      <div className="grid gap-8">
        <section>
          <h2 className="text-lg font-semibold mb-4">Notifications</h2>
          <NotificationSettings />
        </section>
      </div>
    </div>
  );
}
