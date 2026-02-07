import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Package, FolderTree, Users, FileText } from "lucide-react";
import { type LucideIcon } from "lucide-react";

interface ActivityItem {
  id: string;
  icon: LucideIcon;
  description: string;
  timestamp: string;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

const placeholderActivities: ActivityItem[] = [
  {
    id: "1",
    icon: Package,
    description: "Product catalog initialized",
    timestamp: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "2",
    icon: FolderTree,
    description: "Category hierarchy created",
    timestamp: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: "3",
    icon: Users,
    description: "Supplier onboarding module deployed",
    timestamp: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "4",
    icon: FileText,
    description: "Search index synchronized",
    timestamp: new Date(Date.now() - 172800000).toISOString(),
  },
];

export function RecentActivity() {
  const activities = placeholderActivities;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {activities.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No recent activity
          </p>
        ) : (
          <div className="space-y-4">
            {activities.map((activity) => (
              <div key={activity.id} className="flex items-start gap-3">
                <activity.icon className="mt-0.5 h-4 w-4 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{activity.description}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatRelativeTime(activity.timestamp)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
