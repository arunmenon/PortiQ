# ADR-UI-016: Proactive Intelligence & Notifications

**Status:** Accepted
**Date:** 2026-02-06
**Technical Area:** Frontend
**Supersedes:** ADR-UI-012

---

## Context

The PortiQ UX Design Specification introduces **proactive AI assistance** that anticipates user needs and surfaces relevant information before users ask for it. This fundamentally changes the notification paradigm from reactive alerts (ADR-UI-012) to intelligent, context-aware suggestions that drive action.

### Business Context

The traditional notification approach (ADR-UI-012) focused on:
- Event-driven alerts (new RFQ, bid received, etc.)
- Status updates (order shipped, document processed)
- Passive information delivery requiring user action

The PortiQ proactive intelligence approach enables:
- **Zero-click completions: > 40%** through predictive suggestions
- **Predictive restocking alerts** before supplies run low
- **Anomaly detection** surfacing unusual patterns
- **AI recommendations** with one-click actions
- **Conversation-integrated updates** that flow naturally

### Technical Context

- WebSocket for real-time push (preserved from ADR-UI-012)
- ML models for prediction and anomaly detection
- Event-driven architecture (ADR-NF-009)
- Conversation context integration
- Mobile push notifications (Expo)

### Assumptions

- Users value proactive assistance over passive alerts
- Prediction accuracy is sufficient for trust
- Users can easily dismiss irrelevant suggestions
- Proactive notifications won't overwhelm users

---

## Decision Drivers

- Increase zero-click task completions
- Surface high-value opportunities proactively
- Reduce missed procurement windows
- Enable one-click action execution
- Balance helpfulness with notification fatigue

---

## Decision

We will implement **intelligence-driven notifications** that combine traditional event alerts with proactive AI suggestions. Notifications are categorized by actionability, integrated into the conversation flow, and personalized based on user behavior and preferences.

---

## Implementation Notes

### Notification Types Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PROACTIVE INTELLIGENCE                    EVENT NOTIFICATIONS              │
│  (AI-Generated)                            (System-Generated)               │
│                                                                             │
│  ┌────────────────────────────────────┐   ┌────────────────────────────┐   │
│  │ 🔮 Predictive Restocking           │   │ 📋 New RFQ Available       │   │
│  │    "MV Pacific Star will need      │   │    RFQ-2024-0159 matches   │   │
│  │     deck supplies before Mumbai"   │   │    your categories         │   │
│  │    [Start RFQ] [Remind Later]      │   │    [View] [Dismiss]        │   │
│  └────────────────────────────────────┘   └────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────────┐   ┌────────────────────────────┐   │
│  │ ⚠️ Anomaly Detection               │   │ 💰 Quote Received          │   │
│  │    "Unusual price increase for     │   │    Ocean Supply submitted  │   │
│  │     safety equipment this month"   │   │    quote for RFQ-0158      │   │
│  │    [Investigate] [Dismiss]         │   │    [View Quote]            │   │
│  └────────────────────────────────────┘   └────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────────┐   ┌────────────────────────────┐   │
│  │ 💡 Quick Win Suggestion            │   │ 📦 Order Status Update     │   │
│  │    "Accept recommended quote for   │   │    ORD-2024-0892 shipped   │   │
│  │     RFQ-0157, saves $2,340"        │   │    Tracking: MH123456789   │   │
│  │    [Accept] [Compare First]        │   │    [Track Shipment]        │   │
│  └────────────────────────────────────┘   └────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────────┐   ┌────────────────────────────┐   │
│  │ 📊 Performance Insight             │   │ ⏰ Deadline Reminder       │   │
│  │    "Your win rate improved 15%     │   │    RFQ-0158 closes in 2h   │   │
│  │     after switching to balanced    │   │    3 quotes received       │   │
│  │     pricing strategy"              │   │    [Review Quotes]         │   │
│  │    [View Analytics]                │   └────────────────────────────┘   │
│  └────────────────────────────────────┘                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Predictive Restocking Alerts

```typescript
// components/portiq/proactive/restocking-alert.tsx
interface RestockingAlertProps {
  prediction: RestockingPrediction;
  onStartRfq: () => void;
  onRemindLater: () => void;
  onDismiss: () => void;
}

interface RestockingPrediction {
  id: string;
  vesselId: string;
  vesselName: string;
  port: string;
  eta: Date;
  categories: {
    name: string;
    itemCount: number;
    urgency: 'high' | 'medium' | 'low';
  }[];
  estimatedValue: [number, number];
  confidence: number;
  reasoning: string;
  lastSupplyDate: Date;
  daysUntilArrival: number;
}

export function RestockingAlert({
  prediction,
  onStartRfq,
  onRemindLater,
  onDismiss,
}: RestockingAlertProps) {
  const totalItems = prediction.categories.reduce((sum, c) => sum + c.itemCount, 0);
  const highUrgencyCount = prediction.categories.filter(c => c.urgency === 'high').length;

  return (
    <Card className="border-primary/50 bg-primary/5">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
              <RefreshCw className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Predictive Restocking</CardTitle>
              <CardDescription>{prediction.vesselName}</CardDescription>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onDismiss}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-sm">{prediction.reasoning}</p>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Port</p>
            <p className="font-medium">{prediction.port}</p>
          </div>
          <div>
            <p className="text-muted-foreground">ETA</p>
            <p className="font-medium">
              {formatDate(prediction.eta)} ({prediction.daysUntilArrival} days)
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Last Supply</p>
            <p className="font-medium">
              {formatDistanceToNow(prediction.lastSupplyDate)} ago
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Est. Value</p>
            <p className="font-medium">
              {formatCurrency(prediction.estimatedValue[0])} - {formatCurrency(prediction.estimatedValue[1])}
            </p>
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Recommended categories ({totalItems} items)</p>
          <div className="flex flex-wrap gap-2">
            {prediction.categories.map((category, i) => (
              <Badge
                key={i}
                variant={category.urgency === 'high' ? 'destructive' : 'secondary'}
              >
                {category.name} ({category.itemCount})
              </Badge>
            ))}
          </div>
        </div>

        <ConfidenceIndicator level={prediction.confidence} showLabel />

        <div className="flex gap-2">
          <Button onClick={onStartRfq} className="flex-1">
            Start RFQ
          </Button>
          <Button variant="outline" onClick={onRemindLater}>
            <Clock className="h-4 w-4 mr-2" />
            Remind Later
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Anomaly Detection UI

```typescript
// components/portiq/proactive/anomaly-alert.tsx
interface AnomalyAlertProps {
  anomaly: AnomalyDetection;
  onInvestigate: () => void;
  onDismiss: () => void;
}

interface AnomalyDetection {
  id: string;
  type: 'price_spike' | 'demand_surge' | 'supplier_issue' | 'delivery_delay';
  severity: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  affectedItems?: {
    name: string;
    currentValue: number;
    expectedValue: number;
    deviation: number;
  }[];
  recommendation?: string;
  detectedAt: Date;
}

export function AnomalyAlert({
  anomaly,
  onInvestigate,
  onDismiss,
}: AnomalyAlertProps) {
  const severityStyles = {
    critical: 'border-red-500/50 bg-red-500/5',
    warning: 'border-yellow-500/50 bg-yellow-500/5',
    info: 'border-blue-500/50 bg-blue-500/5',
  };

  const severityIcons = {
    critical: <AlertTriangle className="h-4 w-4 text-red-500" />,
    warning: <AlertCircle className="h-4 w-4 text-yellow-500" />,
    info: <Info className="h-4 w-4 text-blue-500" />,
  };

  return (
    <Card className={severityStyles[anomaly.severity]}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-background flex items-center justify-center">
              {severityIcons[anomaly.severity]}
            </div>
            <div>
              <CardTitle className="text-base">{anomaly.title}</CardTitle>
              <CardDescription>
                Detected {formatDistanceToNow(anomaly.detectedAt)} ago
              </CardDescription>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onDismiss}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-sm">{anomaly.description}</p>

        {anomaly.affectedItems && anomaly.affectedItems.length > 0 && (
          <div className="rounded-lg bg-background p-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Affected Items</p>
            {anomaly.affectedItems.slice(0, 3).map((item, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span>{item.name}</span>
                <span className={cn(
                  "font-medium",
                  item.deviation > 0 ? "text-red-600" : "text-green-600"
                )}>
                  {item.deviation > 0 ? '+' : ''}{item.deviation.toFixed(1)}%
                </span>
              </div>
            ))}
            {anomaly.affectedItems.length > 3 && (
              <p className="text-xs text-muted-foreground">
                +{anomaly.affectedItems.length - 3} more items
              </p>
            )}
          </div>
        )}

        {anomaly.recommendation && (
          <div className="flex items-start gap-2 text-sm">
            <Sparkles className="h-4 w-4 text-primary mt-0.5" />
            <p>{anomaly.recommendation}</p>
          </div>
        )}

        <div className="flex gap-2">
          <Button onClick={onInvestigate} className="flex-1">
            Investigate
          </Button>
          <Button variant="ghost" onClick={onDismiss}>
            Dismiss
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### "PortiQ Suggests" Cards

```typescript
// components/portiq/proactive/suggestion-card.tsx
interface SuggestionCardProps {
  suggestion: PortiQSuggestion;
  onPrimaryAction: () => void;
  onSecondaryAction?: () => void;
  onDismiss: () => void;
}

interface PortiQSuggestion {
  id: string;
  type: 'quick_win' | 'optimization' | 'insight' | 'reminder';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  benefit?: {
    type: 'savings' | 'time' | 'efficiency';
    value: string;
  };
  primaryAction: {
    label: string;
    action: string;
    params?: Record<string, any>;
  };
  secondaryAction?: {
    label: string;
    action: string;
    params?: Record<string, any>;
  };
  expiresAt?: Date;
  confidence: number;
}

export function SuggestionCard({
  suggestion,
  onPrimaryAction,
  onSecondaryAction,
  onDismiss,
}: SuggestionCardProps) {
  const typeIcons = {
    quick_win: <Zap className="h-4 w-4 text-yellow-500" />,
    optimization: <TrendingUp className="h-4 w-4 text-green-500" />,
    insight: <Lightbulb className="h-4 w-4 text-blue-500" />,
    reminder: <Bell className="h-4 w-4 text-purple-500" />,
  };

  const priorityStyles = {
    high: 'border-l-4 border-l-primary',
    medium: 'border-l-4 border-l-yellow-500',
    low: '',
  };

  return (
    <Card className={cn(priorityStyles[suggestion.priority])}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              {typeIcons[suggestion.type]}
            </div>
            <div>
              <CardTitle className="text-base">PortiQ Suggests</CardTitle>
              <CardDescription>{suggestion.title}</CardDescription>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onDismiss}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-sm">{suggestion.description}</p>

        {suggestion.benefit && (
          <div className="inline-flex items-center gap-2 bg-green-500/10 text-green-700 px-3 py-1.5 rounded-full text-sm">
            {suggestion.benefit.type === 'savings' && <DollarSign className="h-4 w-4" />}
            {suggestion.benefit.type === 'time' && <Clock className="h-4 w-4" />}
            {suggestion.benefit.type === 'efficiency' && <Gauge className="h-4 w-4" />}
            <span>{suggestion.benefit.value}</span>
          </div>
        )}

        {suggestion.expiresAt && (
          <p className="text-xs text-muted-foreground">
            Expires {formatDistanceToNow(suggestion.expiresAt)}
          </p>
        )}

        <div className="flex gap-2">
          <Button onClick={onPrimaryAction} className="flex-1">
            {suggestion.primaryAction.label}
          </Button>
          {suggestion.secondaryAction && onSecondaryAction && (
            <Button variant="outline" onClick={onSecondaryAction}>
              {suggestion.secondaryAction.label}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Conversation-Integrated Updates

```typescript
// components/portiq/conversation/notification-message.tsx
interface NotificationMessageProps {
  notification: ConversationNotification;
  onAction: (action: NotificationAction) => void;
}

interface ConversationNotification {
  id: string;
  type: 'update' | 'alert' | 'suggestion';
  content: string;
  relatedEntity?: {
    type: 'rfq' | 'quote' | 'order' | 'vessel';
    id: string;
    name: string;
  };
  actions?: NotificationAction[];
  timestamp: Date;
}

export function NotificationMessage({
  notification,
  onAction,
}: NotificationMessageProps) {
  return (
    <div className="flex gap-3 py-2">
      <div className="flex-shrink-0">
        <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center">
          <Bell className="h-3 w-3 text-muted-foreground" />
        </div>
      </div>

      <div className="flex-1 bg-muted/50 rounded-lg p-3">
        <p className="text-sm">{notification.content}</p>

        {notification.relatedEntity && (
          <Button
            variant="link"
            size="sm"
            className="h-auto p-0 mt-1"
            onClick={() =>
              onAction({
                type: 'navigate',
                params: {
                  path: `/${notification.relatedEntity!.type}s/${notification.relatedEntity!.id}`,
                },
              })
            }
          >
            View {notification.relatedEntity.name}
          </Button>
        )}

        {notification.actions && notification.actions.length > 0 && (
          <div className="flex gap-2 mt-2">
            {notification.actions.map((action, i) => (
              <Button
                key={i}
                variant={i === 0 ? 'default' : 'outline'}
                size="sm"
                onClick={() => onAction(action)}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}

        <p className="text-xs text-muted-foreground mt-2">
          {formatDistanceToNow(notification.timestamp)} ago
        </p>
      </div>
    </div>
  );
}
```

### Notification Center with Intelligence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔔 Notifications                              [Mark All Read] [Settings]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ PortiQ Suggestions ───────────────────────────────────────────────────┐│
│  │                                                                        ││
│  │  ┌─────────────────────────────────────────────────────────────────┐  ││
│  │  │ 💡 Quick win: Accept recommended quote for RFQ-0157             │  ││
│  │  │    Saves $2,340 vs. second-best option                          │  ││
│  │  │    [Review & Accept] [See Comparison]               2 min ago   │  ││
│  │  └─────────────────────────────────────────────────────────────────┘  ││
│  │                                                                        ││
│  │  ┌─────────────────────────────────────────────────────────────────┐  ││
│  │  │ 🔄 MV Pacific Star needs restocking before Mumbai arrival       │  ││
│  │  │    Based on consumption patterns, you'll need deck supplies     │  ││
│  │  │    [Start RFQ] [Remind Me Later]                    15 min ago  │  ││
│  │  └─────────────────────────────────────────────────────────────────┘  ││
│  │                                                                        ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Recent Updates ───────────────────────────────────────────────────────┐│
│  │                                                                        ││
│  │  ┌─────────────────────────────────────────────────────────────────┐  ││
│  │  │ 💰 New quote received                                           │  ││
│  │  │    Ocean Supply submitted quote for RFQ-2024-0158               │  ││
│  │  │    [View Quote]                                     10 min ago  │  ││
│  │  └─────────────────────────────────────────────────────────────────┘  ││
│  │                                                                        ││
│  │  ┌─────────────────────────────────────────────────────────────────┐  ││
│  │  │ 📦 Order shipped                                                │  ││
│  │  │    ORD-2024-0892 is on its way to Mumbai Port                   │  ││
│  │  │    [Track Shipment]                                 1 hour ago  │  ││
│  │  └─────────────────────────────────────────────────────────────────┘  ││
│  │                                                                        ││
│  │  ┌─────────────────────────────────────────────────────────────────┐  ││
│  │  │ ✅ Document processed                                           │  ││
│  │  │    Requisition form extracted: 45 line items                    │  ││
│  │  │    [Review Items]                                   2 hours ago │  ││
│  │  └─────────────────────────────────────────────────────────────────┘  ││
│  │                                                                        ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Load More]                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Preference Management

```typescript
// components/settings/notification-preferences.tsx
interface NotificationPreferencesProps {
  preferences: NotificationPreferences;
  onUpdate: (updates: Partial<NotificationPreferences>) => void;
}

interface NotificationPreferences {
  // Proactive Intelligence
  proactive: {
    restockingAlerts: boolean;
    restockingLeadDays: number;
    quickWinSuggestions: boolean;
    minSavingsThreshold: number;
    anomalyAlerts: boolean;
    anomalySeverityThreshold: 'all' | 'warning' | 'critical';
    performanceInsights: boolean;
    insightFrequency: 'daily' | 'weekly' | 'monthly';
  };

  // Event Notifications
  events: {
    newRfq: boolean;
    quoteReceived: boolean;
    orderUpdates: boolean;
    deadlineReminders: boolean;
    reminderLeadHours: number;
  };

  // Channels
  channels: {
    inApp: boolean;
    push: boolean;
    email: boolean;
    emailDigest: 'immediate' | 'daily' | 'weekly';
  };

  // Quiet Hours
  quietHours: {
    enabled: boolean;
    start: string;
    end: string;
    allowUrgent: boolean;
  };
}

export function NotificationPreferencesForm({
  preferences,
  onUpdate,
}: NotificationPreferencesProps) {
  return (
    <div className="space-y-8">
      {/* Proactive Intelligence Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Proactive Intelligence
          </CardTitle>
          <CardDescription>
            Let PortiQ anticipate your needs and suggest actions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <Label>Restocking Alerts</Label>
              <p className="text-sm text-muted-foreground">
                Get notified when vessels may need restocking
              </p>
            </div>
            <Switch
              checked={preferences.proactive.restockingAlerts}
              onCheckedChange={(checked) =>
                onUpdate({ proactive: { ...preferences.proactive, restockingAlerts: checked } })
              }
            />
          </div>

          {preferences.proactive.restockingAlerts && (
            <div className="ml-6 space-y-2">
              <Label>Lead time (days before arrival)</Label>
              <Slider
                value={[preferences.proactive.restockingLeadDays]}
                onValueChange={([value]) =>
                  onUpdate({ proactive: { ...preferences.proactive, restockingLeadDays: value } })
                }
                min={1}
                max={14}
                step={1}
              />
              <p className="text-sm text-muted-foreground">
                {preferences.proactive.restockingLeadDays} days
              </p>
            </div>
          )}

          <Separator />

          <div className="flex items-center justify-between">
            <div>
              <Label>Quick Win Suggestions</Label>
              <p className="text-sm text-muted-foreground">
                Get notified about cost-saving opportunities
              </p>
            </div>
            <Switch
              checked={preferences.proactive.quickWinSuggestions}
              onCheckedChange={(checked) =>
                onUpdate({ proactive: { ...preferences.proactive, quickWinSuggestions: checked } })
              }
            />
          </div>

          {preferences.proactive.quickWinSuggestions && (
            <div className="ml-6 space-y-2">
              <Label>Minimum savings threshold</Label>
              <Input
                type="number"
                value={preferences.proactive.minSavingsThreshold}
                onChange={(e) =>
                  onUpdate({
                    proactive: {
                      ...preferences.proactive,
                      minSavingsThreshold: parseInt(e.target.value),
                    },
                  })
                }
                prefix="$"
              />
              <p className="text-sm text-muted-foreground">
                Only suggest when savings exceed this amount
              </p>
            </div>
          )}

          <Separator />

          <div className="flex items-center justify-between">
            <div>
              <Label>Anomaly Alerts</Label>
              <p className="text-sm text-muted-foreground">
                Get notified about unusual patterns
              </p>
            </div>
            <Switch
              checked={preferences.proactive.anomalyAlerts}
              onCheckedChange={(checked) =>
                onUpdate({ proactive: { ...preferences.proactive, anomalyAlerts: checked } })
              }
            />
          </div>

          {preferences.proactive.anomalyAlerts && (
            <div className="ml-6 space-y-2">
              <Label>Severity threshold</Label>
              <Select
                value={preferences.proactive.anomalySeverityThreshold}
                onValueChange={(value: any) =>
                  onUpdate({
                    proactive: {
                      ...preferences.proactive,
                      anomalySeverityThreshold: value,
                    },
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All anomalies</SelectItem>
                  <SelectItem value="warning">Warning and above</SelectItem>
                  <SelectItem value="critical">Critical only</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Event Notifications Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Event Notifications
          </CardTitle>
          <CardDescription>
            Standard notifications for platform events
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ... event notification toggles ... */}
        </CardContent>
      </Card>

      {/* Delivery Channels Section */}
      <Card>
        <CardHeader>
          <CardTitle>Delivery Channels</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ... channel preferences ... */}
        </CardContent>
      </Card>

      {/* Quiet Hours Section */}
      <Card>
        <CardHeader>
          <CardTitle>Quiet Hours</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ... quiet hours config ... */}
        </CardContent>
      </Card>
    </div>
  );
}
```

### Proactive Trigger Rules

```typescript
// lib/proactive/triggers.ts

interface ProactiveTrigger {
  id: string;
  name: string;
  condition: (context: TriggerContext) => boolean;
  generate: (context: TriggerContext) => Promise<ProactiveNotification | null>;
  cooldown: number; // ms between triggers
  priority: number; // 1 = highest
}

export const proactiveTriggers: ProactiveTrigger[] = [
  // Restocking Alert
  {
    id: 'restocking_alert',
    name: 'Vessel Restocking Alert',
    condition: (ctx) => {
      const vessel = ctx.vessel;
      if (!vessel || !vessel.nextPort) return false;

      const daysUntilArrival = differenceInDays(vessel.nextPort.eta, new Date());
      const daysSinceLastSupply = vessel.lastSupplyDate
        ? differenceInDays(new Date(), vessel.lastSupplyDate)
        : 999;

      // Trigger if arriving within lead time AND needs supplies
      return (
        daysUntilArrival <= ctx.preferences.restockingLeadDays &&
        daysSinceLastSupply > 30
      );
    },
    generate: async (ctx) => {
      const prediction = await predictRestockingNeeds(ctx.vessel!);
      if (!prediction || prediction.confidence < 0.7) return null;

      return {
        type: 'restocking',
        priority: 'high',
        title: `${ctx.vessel!.name} needs restocking before ${ctx.vessel!.nextPort!.name}`,
        prediction,
      };
    },
    cooldown: 24 * 60 * 60 * 1000, // 24 hours
    priority: 1,
  },

  // Quick Win Suggestion
  {
    id: 'quick_win',
    name: 'Quote Acceptance Suggestion',
    condition: (ctx) => {
      if (!ctx.rfq || ctx.rfq.status !== 'BIDDING') return false;

      const quotes = ctx.rfq.quotes;
      if (quotes.length < 2) return false;

      // Check if there's a clear winner
      const recommendation = analyzeQuotes(quotes);
      return recommendation && recommendation.savingsVsSecond >= ctx.preferences.minSavingsThreshold;
    },
    generate: async (ctx) => {
      const recommendation = analyzeQuotes(ctx.rfq!.quotes);
      if (!recommendation) return null;

      return {
        type: 'quick_win',
        priority: 'medium',
        title: `Accept recommended quote for ${ctx.rfq!.title}`,
        description: `Saves ${formatCurrency(recommendation.savingsVsSecond)} vs. second-best option`,
        benefit: {
          type: 'savings',
          value: formatCurrency(recommendation.savingsVsSecond),
        },
        recommendation,
      };
    },
    cooldown: 60 * 60 * 1000, // 1 hour
    priority: 2,
  },

  // Anomaly Detection
  {
    id: 'price_anomaly',
    name: 'Price Anomaly Detection',
    condition: (ctx) => {
      return ctx.preferences.anomalyAlerts && ctx.anomalies && ctx.anomalies.length > 0;
    },
    generate: async (ctx) => {
      const anomaly = ctx.anomalies![0];
      if (anomaly.severity === 'info' && ctx.preferences.anomalySeverityThreshold !== 'all') {
        return null;
      }
      if (anomaly.severity === 'warning' && ctx.preferences.anomalySeverityThreshold === 'critical') {
        return null;
      }

      return {
        type: 'anomaly',
        priority: anomaly.severity === 'critical' ? 'high' : 'medium',
        anomaly,
      };
    },
    cooldown: 4 * 60 * 60 * 1000, // 4 hours
    priority: 3,
  },

  // Deadline Reminder
  {
    id: 'deadline_reminder',
    name: 'RFQ Deadline Reminder',
    condition: (ctx) => {
      if (!ctx.rfq || ctx.rfq.status !== 'BIDDING') return false;

      const hoursUntilDeadline = differenceInHours(ctx.rfq.deadline, new Date());
      return hoursUntilDeadline <= ctx.preferences.reminderLeadHours && hoursUntilDeadline > 0;
    },
    generate: async (ctx) => {
      return {
        type: 'reminder',
        priority: 'high',
        title: `${ctx.rfq!.title} closes in ${formatDistanceToNow(ctx.rfq!.deadline)}`,
        description: `${ctx.rfq!.quotes.length} quotes received`,
        rfq: ctx.rfq,
      };
    },
    cooldown: 2 * 60 * 60 * 1000, // 2 hours
    priority: 1,
  },
];
```

### Notification Service

```typescript
// lib/notifications/proactive-service.ts
import { proactiveTriggers } from './triggers';

class ProactiveNotificationService {
  private cooldowns = new Map<string, number>();

  async evaluate(context: TriggerContext): Promise<ProactiveNotification[]> {
    const notifications: ProactiveNotification[] = [];

    // Sort triggers by priority
    const sortedTriggers = [...proactiveTriggers].sort((a, b) => a.priority - b.priority);

    for (const trigger of sortedTriggers) {
      // Check cooldown
      const lastTriggered = this.cooldowns.get(`${trigger.id}:${context.userId}`);
      if (lastTriggered && Date.now() - lastTriggered < trigger.cooldown) {
        continue;
      }

      // Check condition
      if (!trigger.condition(context)) {
        continue;
      }

      // Generate notification
      try {
        const notification = await trigger.generate(context);
        if (notification) {
          notifications.push(notification);
          this.cooldowns.set(`${trigger.id}:${context.userId}`, Date.now());
        }
      } catch (error) {
        console.error(`Error generating notification for trigger ${trigger.id}:`, error);
      }
    }

    return notifications;
  }

  async deliver(
    userId: string,
    notification: ProactiveNotification,
    preferences: NotificationPreferences
  ): Promise<void> {
    // In-app notification (always)
    if (preferences.channels.inApp) {
      await this.deliverInApp(userId, notification);
    }

    // Push notification (if enabled and appropriate)
    if (preferences.channels.push && notification.priority === 'high') {
      await this.deliverPush(userId, notification);
    }

    // Email (based on digest preference)
    if (preferences.channels.email) {
      if (preferences.channels.emailDigest === 'immediate') {
        await this.deliverEmail(userId, notification);
      } else {
        await this.queueForDigest(userId, notification);
      }
    }
  }

  private async deliverInApp(userId: string, notification: ProactiveNotification) {
    // WebSocket delivery
    socketGateway.notifyUser(userId, {
      type: 'proactive',
      notification,
    });

    // Persist for notification center
    await notificationRepository.create({
      userId,
      type: 'proactive',
      subType: notification.type,
      priority: notification.priority,
      data: notification,
      read: false,
    });
  }

  private async deliverPush(userId: string, notification: ProactiveNotification) {
    const user = await userRepository.findById(userId);
    if (!user.pushTokens?.length) return;

    await pushService.send(user.pushTokens, {
      title: notification.title,
      body: notification.description,
      data: {
        type: 'proactive',
        notificationId: notification.id,
      },
    });
  }

  private async deliverEmail(userId: string, notification: ProactiveNotification) {
    const user = await userRepository.findById(userId);

    await emailService.send({
      to: user.email,
      template: `proactive-${notification.type}`,
      data: notification,
    });
  }

  private async queueForDigest(userId: string, notification: ProactiveNotification) {
    await redis.lpush(`digest:${userId}`, JSON.stringify(notification));
  }
}

export const proactiveService = new ProactiveNotificationService();
```

### Market Intelligence During RFQ Creation

*Added 2026-02-08 based on AI-native RFQ creation research*

While the proactive triggers above handle push-based intelligence, the RFQ creation form also needs **pull-based intelligence** that updates reactively as the buyer fills in the form. This section specifies the Intelligence Sidebar and its data sources.

#### Seven Intelligence Types

| # | Intelligence Type | What It Provides | Data Sources |
|---|---|---|---|
| 1 | **Supplier Recommendations** | Real-time supplier match counts by port and category | `supplier_profiles.port_coverage`, `supplier_profiles.categories`, historical `quotes` |
| 2 | **Price Benchmarks** | Historical price ranges for IMPA codes at specific ports (P25/P50/P75) | `quote_line_items.unit_price` aggregated by IMPA code x port x time window |
| 3 | **Lead Time Insights** | Typical delivery timelines by category at specific ports | `quotes.estimated_delivery_days` aggregated by port and category |
| 4 | **Supply Availability Signals** | Alerts about constraints, seasonal patterns, port issues | Quote response rates, supplier onboarding status, seasonal volume patterns |
| 5 | **Historical Comparison** | Current RFQ vs buyer's own historical patterns | Previous `rfqs` by same `buyer_organization_id` filtered by port/category |
| 6 | **Timing Optimization** | Optimal bidding windows based on supplier response patterns | `rfq_invitations` response times, quote submission patterns by day-of-week |
| 7 | **Port-Specific Intelligence** | Port-level metrics comparing supplier ecosystems | Aggregated supplier counts, response times, quote-to-invite ratios per port |

#### Intelligence Sidebar UX

A collapsible right-hand panel (~30% width on desktop, bottom sheet on mobile) that updates reactively as form fields change (debounced 500ms):

```
+-----------------------------+-------------------+
|  RFQ Creation Form          |  Intelligence     |
|                             |  Sidebar          |
|  Title: [______________]    |                   |
|  Vessel: [MV Pacific Star]  |  Port: Mumbai     |
|  Port: [Mumbai ▼]           |  12 suppliers     |
|  Deadline: [__/__/____]     |  Avg response: 1d |
|                             |                   |
|  Line Items:                |  -- Price Alert -- |
|  1. IMPA 232501 Qty: 10     |  Alkyd Paint 5L   |
|     [Est: $42-67 ea]        |  $42-$67 (90d)    |
|  2. IMPA 271300 Qty: 5      |  12 quotes basis  |
|     [Est: $120-185 ea]      |                   |
|                             |  -- Suppliers --   |
|  + Add line item            |  5 match all items |
|                             |  3 VERIFIED+       |
|                             |  [Auto-invite ...]|
|                             |                   |
|  [Save Draft] [Publish]     |  Budget est: $1.2K |
+-----------------------------+-------------------+
```

Sidebar sections appear/disappear based on form context (no port = no port insights). Cards ordered by relevance: warnings first, then recommendations, then informational.

#### Inline Form Hints

Small non-intrusive annotations on form fields:

- **Port field:** Badge "12 suppliers | avg 1.5d response" after selection
- **Delivery date:** Yellow warning if tight vs ETA, green check if sufficient margin
- **Bidding deadline:** Badge "5-day window recommended (2.3x more quotes)"
- **Line items:** Per-item price range badge, supplier availability dot (green/yellow/red)

#### Risk Flag Taxonomy

| Flag | Trigger | Severity |
|------|---------|----------|
| Single-source risk | Only 1 supplier covers all line items at this port | HIGH |
| Tight timeline | Delivery date - vessel ETA < average lead time | HIGH |
| No price history | >50% of line items have no historical pricing | MEDIUM |
| Unusual quantity | Quantity > 3x standard deviation from buyer's history | MEDIUM |
| New category | Buyer has never ordered this category before | LOW |
| Suspended suppliers | Previously used suppliers are now suspended | MEDIUM |
| Low response port | Historical quote-to-invite ratio < 50% at this port | MEDIUM |

#### Supplier Auto-Matching Pipeline

When the buyer has set at least a delivery port and one line item, the system runs a 6-stage matching pipeline:

```
Stage 1: Port Filter
  supplier_profiles.port_coverage @> [delivery_port]
  → Candidates pool

Stage 2: Category Match
  coverage_score = matched_categories / rfq_categories
  Filter: coverage_score >= 30%
  → Qualified pool

Stage 3: Tier Filter
  Default: VERIFIED+ (tier IN VERIFIED, PREFERRED, PREMIUM)
  Fallback: If <3 candidates, include BASIC tier
  → Eligible pool

Stage 4: Performance Scoring (0-100)
  score = (on_time_rate x 30) + (quality_score x 25) +
          (quote_response_rate x 20) + (price_competitiveness x 15) +
          (category_coverage x 10)

Stage 5: Diversity Check
  Ensure minimum 3 suppliers. If <3, expand port radius or lower tier.
  Flag single-source risk if only 1-2 available.

Stage 6: Ranking & Presentation
  Sort by performance_score DESC.
  Group: "Recommended" (top 3-5) vs "Other" (rest).
  Pre-select top 3 by default.
```

#### Budget Estimation

Running budget estimate displayed prominently, updating as line items are added:

```
Budget Estimate (based on 90-day price history)
  Low:    $980  (P25)
  Likely: $1,240 (P50)
  High:   $1,680 (P75)
Based on 47 historical quotes for similar items at Mumbai.
3 of 8 items have no price history (excluded).
```

Uses percentile bands from historical quote data for matching IMPA codes at matching ports.

#### Timing Advisor

Visual timeline correlating publish date, bidding window, vessel ETA, and delivery:

```
Today        Publish     Deadline     Vessel ETA    Delivery
  |            |            |            |             |
  |----2d----->|----5d----->|----3d----->|-----2d----->|
  Feb 8        Feb 10       Feb 15       Feb 18        Feb 20
```

Recommendation: "5-day bidding window historically attracts 4.2 quotes (avg). 3 days between deadline and ETA is sufficient for top 3 suppliers."

#### Privacy Constraints

| Data Point | Visible to Buyer | Protection |
|---|---|---|
| Individual supplier quotes | Never (before deadline) | Sealed-bid enforcement (ADR-FN-012) |
| Price benchmarks | Aggregated ranges only | Minimum 3 quotes threshold; no supplier attribution |
| Supplier names in suggestions | Yes (public profiles) | Only APPROVED suppliers with adequate visibility tier |
| Supplier performance scores | Relative ranking only | Exact scores hidden; shown as tiers or stars |
| Other buyers' order patterns | Never | Cross-organization aggregates only |

#### Data Aggregation Infrastructure

| Aggregation | Granularity | Refresh | Storage |
|---|---|---|---|
| Price benchmarks | IMPA code x port x 30/90/365 day windows | Daily materialized view | PostgreSQL MV |
| Supplier match scores | Supplier x port x category | Daily batch job | Redis cache (24h TTL) |
| Quote response metrics | Supplier x port | Daily batch job | PostgreSQL table |
| Lead time statistics | Category x port | Weekly batch job | PostgreSQL table |
| Port supplier counts | Port code | Real-time (on supplier profile change) | Redis cache |
| Buyer historical patterns | Organization x route/port | Daily batch job | PostgreSQL table |

#### API Design

Single debounce-friendly endpoint for all intelligence:

```
GET /api/v1/intelligence
  ?delivery_port=INMAA
  &impa_codes=232501,271300
  &vessel_id=<uuid>
  &delivery_date=2026-02-20
  &bidding_deadline=2026-02-15

Response: IntelligenceResponse {
  suppliers: { count, verified_plus_count, top_matches[] },
  price_benchmarks: { per_item[], budget_estimate },
  lead_times: { per_category[] },
  risk_flags: RiskFlag[],
  timing: { recommendation, optimal_window_days },
  port_info: { supplier_count, avg_response_days, quote_to_invite_ratio }
}
```

---

## Dependencies

- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-009: Design System & Theming (notification components)
- ADR-UI-013: PortiQ Buyer Experience (conversation integration)
- ADR-NF-009: Event-Driven Communication
- ADR-FN-021: Predictive Supply ML Model (prediction backend)

---

## Migration Strategy

### From ADR-UI-012 (Traditional Notifications)

1. **Phase 1: Add Proactive Layer**
   - Deploy proactive suggestions alongside existing notifications
   - Add "PortiQ Suggests" section to notification center
   - Maintain all existing event notifications

2. **Phase 2: Intelligence Enhancement**
   - Enable ML-based predictions
   - Add anomaly detection alerts
   - Introduce quick win suggestions

3. **Phase 3: Full Integration**
   - Integrate proactive updates into conversation flow
   - Add preference controls for proactive features
   - Optimize based on user feedback

### Feature Mapping

| Notification Feature | Proactive Equivalent |
|----------------------|----------------------|
| New RFQ alert | Proactive RFQ matching + restocking predictions |
| Deadline reminder | AI-timed reminders with context |
| Quote received | Quick win suggestions when quotes are optimal |
| Order status | Proactive delivery predictions |
| Generic alerts | Contextualized insights |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Trigger evaluation | < 100ms | Per user context |
| Prediction generation | < 2s | ML model inference |
| Notification delivery | < 500ms | Socket to client |
| Preference update | < 200ms | Settings change |

---

## Success Metrics

| Metric | Target | Tracking |
|--------|--------|----------|
| Zero-click completions | > 40% | Action tracking |
| Suggestion acceptance | > 50% | Primary action clicks |
| Suggestion dismissal | < 20% | Dismiss clicks |
| Time savings per user | > 2 hours/week | Before/after comparison |
| User satisfaction | > 4.5/5 | Feature surveys |

---

## References

- PortiQ UX Design Specification (internal)
- [Proactive UX Design](https://www.nngroup.com/articles/proactive-ux/)
- [Notification Best Practices](https://material.io/design/platform-guidance/android-notifications.html)
- [AI Transparency Guidelines](https://pair.withgoogle.com/guidebook/)
