# ADR-UI-006: React Native with Expo

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The platform requires mobile applications for both buyers and suppliers to enable on-the-go procurement and order management.

### Business Context
Mobile requirements:
- Field procurement officers need mobile access
- Suppliers need to respond to RFQs quickly
- Order tracking and notifications
- Document capture (photos, scans)
- Offline capability for ship environments
- Push notifications for urgent RFQs

### Technical Context
- React/TypeScript expertise on team
- Code sharing with web app desired
- Both iOS and Android required
- Backend API already defined (ADR-NF-007)
- Real-time features needed

### Assumptions
- React Native is performant enough
- Expo simplifies deployment
- EAS Build handles app store submissions
- OTA updates valuable for quick fixes

---

## Decision Drivers

- Development speed
- Code sharing with web
- iOS and Android parity
- Deployment simplicity
- OTA update capability
- Native feature access

---

## Considered Options

### Option 1: React Native with Expo
**Description:** React Native with Expo managed workflow.

**Pros:**
- Fastest development
- OTA updates via EAS
- Simplified native access
- Great developer experience
- Code sharing with web
- EAS Build for app stores

**Cons:**
- Some native limitations
- Expo SDK size
- Dependency on Expo

### Option 2: React Native CLI (Bare)
**Description:** Pure React Native without Expo.

**Pros:**
- Full native control
- Smaller app size
- No Expo dependency

**Cons:**
- More complex setup
- No OTA updates
- Manual native config
- Slower development

### Option 3: Flutter
**Description:** Google's cross-platform framework.

**Pros:**
- Excellent performance
- Beautiful UI
- Single codebase
- Hot reload

**Cons:**
- Dart language (new learning)
- No web code sharing
- Smaller ecosystem than React

### Option 4: Native (Swift/Kotlin)
**Description:** Separate native apps.

**Pros:**
- Best performance
- Full platform features
- Platform-specific UX

**Cons:**
- Two codebases
- Double development effort
- No code sharing
- Specialist developers needed

---

## Decision

**Chosen Option:** React Native with Expo

We will use React Native with Expo managed workflow for mobile development, leveraging EAS Build for app store submissions and EAS Update for OTA updates.

### Rationale
Expo provides the fastest path to mobile apps while maintaining code quality. The managed workflow handles most native complexity. EAS Build simplifies app store deployment. OTA updates enable rapid bug fixes without app store review. Code sharing with the web app improves consistency.

---

## Consequences

### Positive
- Rapid development
- OTA updates for quick fixes
- Simplified build process
- Code sharing with web
- Single TypeScript codebase

### Negative
- Expo SDK limitations
- **Mitigation:** Expo Development Build for custom native
- Larger app size
- **Mitigation:** Acceptable for B2B app

### Risks
- Native feature limitations: Development builds, custom native modules
- Performance issues: Optimization, native modules where needed
- Expo breaking changes: Pin versions, test updates

---

## Implementation Notes

### Project Structure

```
apps/mobile/
├── app/                    # Expo Router pages
│   ├── (auth)/
│   │   ├── login.tsx
│   │   └── _layout.tsx
│   ├── (buyer)/
│   │   ├── _layout.tsx
│   │   ├── index.tsx
│   │   ├── catalog/
│   │   ├── rfqs/
│   │   └── orders/
│   ├── (supplier)/
│   │   ├── _layout.tsx
│   │   ├── index.tsx
│   │   ├── opportunities/
│   │   └── orders/
│   └── _layout.tsx
├── components/
│   ├── ui/
│   ├── forms/
│   └── shared/
├── hooks/
├── lib/
│   ├── api/
│   ├── storage/
│   └── utils/
├── stores/
├── app.json
├── eas.json
└── package.json
```

### App Configuration

```json
// app.json
{
  "expo": {
    "name": "Ship Chandlery",
    "slug": "ship-chandlery",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "userInterfaceStyle": "automatic",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#0369a1"
    },
    "updates": {
      "fallbackToCacheTimeout": 0,
      "url": "https://u.expo.dev/your-project-id"
    },
    "runtimeVersion": {
      "policy": "sdkVersion"
    },
    "assetBundlePatterns": ["**/*"],
    "ios": {
      "supportsTablet": true,
      "bundleIdentifier": "com.shipchandlery.app",
      "config": {
        "usesNonExemptEncryption": false
      }
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#0369a1"
      },
      "package": "com.shipchandlery.app",
      "permissions": [
        "CAMERA",
        "READ_EXTERNAL_STORAGE",
        "WRITE_EXTERNAL_STORAGE"
      ]
    },
    "plugins": [
      "expo-router",
      "expo-secure-store",
      "expo-camera",
      "expo-document-picker",
      [
        "expo-notifications",
        {
          "icon": "./assets/notification-icon.png",
          "color": "#0369a1"
        }
      ]
    ],
    "extra": {
      "eas": {
        "projectId": "your-project-id"
      }
    }
  }
}
```

### EAS Configuration

```json
// eas.json
{
  "cli": {
    "version": ">= 5.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "ios": {
        "simulator": true
      }
    },
    "preview": {
      "distribution": "internal",
      "channel": "preview"
    },
    "production": {
      "channel": "production",
      "ios": {
        "resourceClass": "m-medium"
      }
    }
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "your@email.com",
        "ascAppId": "your-app-id"
      },
      "android": {
        "serviceAccountKeyPath": "./google-service-account.json"
      }
    }
  }
}
```

### Root Layout with Auth

```tsx
// app/_layout.tsx
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import * as SplashScreen from 'expo-splash-screen';
import { useAuthStore } from '@/stores/auth-store';
import { queryClient } from '@/lib/query-client';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const { isLoading, initialize } = useAuthStore();

  useEffect(() => {
    initialize().finally(() => {
      SplashScreen.hideAsync();
    });
  }, []);

  if (isLoading) {
    return null;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="auto" />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(buyer)" />
          <Stack.Screen name="(supplier)" />
        </Stack>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
```

### Auth Store with Secure Storage

```tsx
// stores/auth-store.ts
import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { router } from 'expo-router';
import { authApi } from '@/lib/api/auth';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  initialize: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  initialize: async () => {
    try {
      const token = await SecureStore.getItemAsync('accessToken');
      if (token) {
        const user = await authApi.getCurrentUser();
        set({ user, isAuthenticated: true });

        // Navigate based on user type
        if (user.organizationType === 'BUYER') {
          router.replace('/(buyer)');
        } else {
          router.replace('/(supplier)');
        }
      }
    } catch (error) {
      await SecureStore.deleteItemAsync('accessToken');
      await SecureStore.deleteItemAsync('refreshToken');
    } finally {
      set({ isLoading: false });
    }
  },

  login: async (email, password) => {
    const { accessToken, refreshToken, user } = await authApi.login(email, password);

    await SecureStore.setItemAsync('accessToken', accessToken);
    await SecureStore.setItemAsync('refreshToken', refreshToken);

    set({ user, isAuthenticated: true });

    if (user.organizationType === 'BUYER') {
      router.replace('/(buyer)');
    } else {
      router.replace('/(supplier)');
    }
  },

  logout: async () => {
    await SecureStore.deleteItemAsync('accessToken');
    await SecureStore.deleteItemAsync('refreshToken');
    set({ user: null, isAuthenticated: false });
    router.replace('/(auth)/login');
  },

  refreshToken: async () => {
    const refreshToken = await SecureStore.getItemAsync('refreshToken');
    if (!refreshToken) throw new Error('No refresh token');

    const { accessToken, refreshToken: newRefreshToken } =
      await authApi.refreshToken(refreshToken);

    await SecureStore.setItemAsync('accessToken', accessToken);
    await SecureStore.setItemAsync('refreshToken', newRefreshToken);
  },
}));
```

### Buyer Dashboard Screen

```tsx
// app/(buyer)/index.tsx
import { View, ScrollView, RefreshControl } from 'react-native';
import { useCallback, useState } from 'react';
import { useBuyerMetrics, useRecentOrders } from '@/hooks/queries/use-buyer';
import { MetricCard } from '@/components/ui/metric-card';
import { OrderCard } from '@/components/orders/order-card';
import { Text } from '@/components/ui/text';
import { styles } from './styles';

export default function BuyerDashboard() {
  const [refreshing, setRefreshing] = useState(false);
  const { data: metrics, refetch: refetchMetrics } = useBuyerMetrics();
  const { data: orders, refetch: refetchOrders } = useRecentOrders();

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refetchMetrics(), refetchOrders()]);
    setRefreshing(false);
  }, []);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <Text variant="h1" style={styles.title}>Dashboard</Text>

      <View style={styles.metricsGrid}>
        <MetricCard
          title="Active RFQs"
          value={metrics?.activeRfqs || 0}
          icon="file-text"
          href="/(buyer)/rfqs"
        />
        <MetricCard
          title="Pending Orders"
          value={metrics?.pendingOrders || 0}
          icon="shopping-cart"
          href="/(buyer)/orders"
        />
        <MetricCard
          title="Monthly Spend"
          value={formatCurrency(metrics?.monthlySpend || 0)}
          icon="dollar-sign"
        />
        <MetricCard
          title="Savings"
          value={`${metrics?.savingsPercent || 0}%`}
          icon="trending-down"
        />
      </View>

      <View style={styles.section}>
        <Text variant="h2">Recent Orders</Text>
        {orders?.map((order) => (
          <OrderCard key={order.id} order={order} />
        ))}
      </View>
    </ScrollView>
  );
}
```

### Push Notifications Setup

```tsx
// lib/notifications.ts
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import { api } from './api';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    console.log('Push notifications require a physical device');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('Push notification permission denied');
    return null;
  }

  const token = await Notifications.getExpoPushTokenAsync({
    projectId: 'your-project-id',
  });

  // Register token with backend
  await api.post('/users/push-token', { token: token.data });

  if (Platform.OS === 'android') {
    Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
    });
  }

  return token.data;
}

export function useNotificationListener() {
  useEffect(() => {
    const subscription = Notifications.addNotificationReceivedListener(
      (notification) => {
        console.log('Notification received:', notification);
      }
    );

    const responseSubscription =
      Notifications.addNotificationResponseReceivedListener((response) => {
        const data = response.notification.request.content.data;

        // Navigate based on notification type
        if (data.type === 'NEW_RFQ') {
          router.push(`/(supplier)/opportunities/${data.rfqId}`);
        } else if (data.type === 'ORDER_UPDATE') {
          router.push(`/(buyer)/orders/${data.orderId}`);
        }
      });

    return () => {
      subscription.remove();
      responseSubscription.remove();
    };
  }, []);
}
```

### API Client with Token Refresh

```tsx
// lib/api/client.ts
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { useAuthStore } from '@/stores/auth-store';

const client = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL,
  timeout: 30000,
});

client.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        await useAuthStore.getState().refreshToken();
        const token = await SecureStore.getItemAsync('accessToken');
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return client(originalRequest);
      } catch (refreshError) {
        await useAuthStore.getState().logout();
        throw refreshError;
      }
    }

    throw error;
  }
);

export { client };
```

### Dependencies
- ADR-UI-007: Offline-First Mobile
- ADR-UI-008: Mobile Catalog Caching
- ADR-UI-003: State Management Strategy

### Migration Strategy
1. Initialize Expo project
2. Set up EAS Build
3. Create navigation structure
4. Implement authentication
5. Build shared components
6. Create buyer screens
7. Create supplier screens
8. Set up push notifications
9. Configure OTA updates
10. Submit to app stores

---

## Operational Considerations

### Native Module Requirements

#### Required Native Modules (Expo SDK)

| Module | Use Case | Expo Support | Notes |
|--------|----------|--------------|-------|
| expo-camera | Document scanning, photo capture | Native | Included in SDK |
| expo-document-picker | File uploads | Native | Included in SDK |
| expo-file-system | Offline storage, downloads | Native | Included in SDK |
| expo-secure-store | Token storage | Native | Included in SDK |
| expo-notifications | Push notifications | Native | Requires config plugin |
| expo-sqlite | Offline database | Native | Included in SDK |
| expo-image-picker | Product images | Native | Included in SDK |
| expo-barcode-scanner | IMPA code scanning | Native | Included in SDK |

#### Modules Requiring Development Build

| Module | Use Case | Why Dev Build | Alternative |
|--------|----------|--------------|-------------|
| react-native-pdf | Invoice viewing | Not in Expo Go | expo-web-browser |
| @react-native-community/netinfo | Connectivity detection | Config plugin | Included since SDK 48 |
| react-native-background-fetch | Background sync | Native code | expo-background-fetch |

### Ejection Criteria

#### Decision Matrix for Ejection

| Criterion | Threshold | Action |
|-----------|-----------|--------|
| Custom native module needed | Not available in Expo | Try config plugin first |
| Performance critical native code | Measured bottleneck | Profile before deciding |
| Third-party SDK requirement | No React Native wrapper | Evaluate necessity |
| Binary size > 150MB | After optimization | Review asset strategy |
| Expo SDK missing critical feature | After 6-month wait | Consider development build |

#### Ejection Decision Flowchart

```
Need native functionality?
├── Available in Expo SDK? → Use Expo SDK module
├── Available via config plugin? → Use config plugin with dev build
├── Can build custom config plugin? → Build plugin, stay managed
└── Requires native code changes?
    ├── Is it performance critical? → Profile first
    │   ├── Yes, proven bottleneck → Consider ejection
    │   └── No measurable impact → Use JS alternative
    └── Is there a React Native library?
        ├── Yes, supports Expo → Use with dev build
        └── No → Evaluate build vs buy
            ├── Build effort < 2 weeks → Build config plugin
            └── Build effort > 2 weeks → Consider ejection
```

#### Pre-Ejection Checklist

- [ ] Documented specific native requirement
- [ ] Attempted Expo config plugin solution
- [ ] Benchmarked performance impact
- [ ] Evaluated alternative JS-only solutions
- [ ] Assessed team native development capacity
- [ ] Calculated maintenance cost increase (estimate: +30% effort)
- [ ] Obtained stakeholder approval for increased complexity

### OTA Update Policy

#### Update Channels

| Channel | Purpose | Auto-Update | Approval |
|---------|---------|-------------|----------|
| `production` | Live users | Yes | Required |
| `staging` | QA testing | Yes | Team lead |
| `preview` | Stakeholder review | Yes | None |
| `development` | Dev testing | Yes | None |

#### OTA Update Rules

```typescript
// app.json configuration
{
  "expo": {
    "updates": {
      "enabled": true,
      "checkAutomatically": "ON_LOAD",
      "fallbackToCacheTimeout": 30000,
      "url": "https://u.expo.dev/[project-id]"
    },
    "runtimeVersion": {
      "policy": "sdkVersion"
    }
  }
}
```

#### Update Classification

| Update Type | OTA Eligible | App Store Required | Examples |
|-------------|--------------|-------------------|----------|
| Bug fixes | Yes | No | Crash fixes, logic errors |
| UI tweaks | Yes | No | Spacing, colors, copy |
| New features (JS only) | Yes | No | New screens, workflows |
| Performance improvements | Yes | No | Optimization, caching |
| Native module update | No | Yes | Camera, notifications |
| Expo SDK upgrade | No | Yes | SDK version bump |
| New permissions | No | Yes | Location, contacts |

#### OTA Deployment Process

```
1. Code merged to main
         │
         ▼
2. CI builds update bundle
         │
         ▼
3. Deploy to `staging` channel
         │
         ▼
4. QA verification (2-4 hours)
         │
         ▼
5. Deploy to `production` channel
         │
         ▼
6. Monitor error rates (30 min)
         │
         ├── Error rate < 0.1% → Complete
         │
         └── Error rate > 0.1% → Rollback
                    │
                    ▼
            Revert to previous update
```

### App Store Release Cadence

| Release Type | Frequency | Trigger |
|--------------|-----------|---------|
| Major version | Quarterly | New features requiring native |
| Minor version | Monthly | Accumulated OTA updates |
| Patch version | As needed | Critical native fixes |
| Hotfix (OTA) | As needed | Critical JS fixes |

#### Release Calendar (Example)

```
Q1 2025:
├── Jan 15: v1.4.0 (Feature release)
├── Feb 15: v1.4.1 (Monthly rollup)
├── Mar 15: v1.4.2 (Monthly rollup)
└── Mar 30: v1.5.0 (Quarterly feature)

Between releases: OTA updates for JS changes
```

### Large Asset & App Size Strategy

#### Size Budget

| Component | Budget | Current | Strategy |
|-----------|--------|---------|----------|
| App binary | 80 MB | ~60 MB | Optimize images, tree-shake |
| Initial JS bundle | 5 MB | ~3 MB | Code splitting, lazy load |
| Catalog database | 50 MB | ~45 MB | Compressed SQLite |
| Cached images | 100 MB | Variable | LRU eviction |
| Total on-device | 250 MB | Variable | User notification at 200MB |

#### Asset Management

```typescript
// Lazy loading for large assets
const ProductCatalog = React.lazy(() => import('./ProductCatalog'));

// Image caching with size limits
import * as FileSystem from 'expo-file-system';

const IMAGE_CACHE_DIR = `${FileSystem.cacheDirectory}images/`;
const MAX_CACHE_SIZE = 100 * 1024 * 1024; // 100 MB

async function cacheImage(url: string): Promise<string> {
  const filename = url.split('/').pop();
  const localPath = `${IMAGE_CACHE_DIR}${filename}`;

  // Check cache size before adding
  const cacheInfo = await FileSystem.getInfoAsync(IMAGE_CACHE_DIR);
  if (cacheInfo.size > MAX_CACHE_SIZE) {
    await evictOldestImages();
  }

  await FileSystem.downloadAsync(url, localPath);
  return localPath;
}

// Catalog download with progress
async function downloadCatalog(onProgress: (percent: number) => void) {
  const callback = (downloadProgress) => {
    const progress = downloadProgress.totalBytesWritten /
      downloadProgress.totalBytesExpectedToWrite;
    onProgress(Math.round(progress * 100));
  };

  const downloadResumable = FileSystem.createDownloadResumable(
    CATALOG_URL,
    `${FileSystem.documentDirectory}catalog.db`,
    {},
    callback
  );

  await downloadResumable.downloadAsync();
}
```

#### Storage Management UI

```typescript
// Settings screen storage management
export function StorageManagement() {
  const { catalogSize, cacheSize, totalSize } = useStorageInfo();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Storage</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <StorageBar
            label="Product Catalog"
            size={catalogSize}
            max={50 * 1024 * 1024}
          />
          <StorageBar
            label="Cached Images"
            size={cacheSize}
            max={100 * 1024 * 1024}
          />
          <div className="flex justify-between text-sm">
            <span>Total: {formatBytes(totalSize)}</span>
            <Button variant="outline" size="sm" onPress={clearCache}>
              Clear Cache
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Open Questions - Resolved

- **Q:** How will you handle large offline assets and app size limits?
  - **A:** We implement a tiered storage strategy:
    1. **App binary budget**: 80MB max, achieved through image optimization and tree-shaking
    2. **Catalog storage**: 50MB SQLite database, downloaded on first launch with progress indicator
    3. **Image caching**: 100MB LRU cache with automatic eviction of oldest images
    4. **User transparency**: Settings screen shows storage breakdown with "Clear Cache" option
    5. **Proactive management**: Warning notification when total storage exceeds 200MB
    6. **Selective sync**: Users can choose which product categories to cache offline
    7. **Compression**: All downloaded assets use gzip compression (catalog: ~15MB compressed)
    8. **Lazy loading**: Large screens/features loaded on-demand, not in initial bundle

---

## Voice-First Mobile Architecture

The PortiQ AI-native UX emphasizes voice input as a primary interaction method on mobile, enabling hands-free operation for field procurement officers and busy suppliers.

### Voice Input Architecture

```
apps/mobile/
├── lib/
│   └── voice/
│       ├── VoiceService.ts         # Voice recognition service
│       ├── VoiceCommandParser.ts   # NLU intent parsing
│       ├── WakeWordDetector.ts     # Optional wake word
│       └── AudioFeedback.ts        # Haptic/audio feedback
├── components/
│   └── voice/
│       ├── VoiceInputButton.tsx    # Main voice button
│       ├── VoiceWaveform.tsx       # Visual waveform
│       ├── VoiceBottomSheet.tsx    # Conversation sheet
│       └── VoiceTranscript.tsx     # Real-time transcript
└── hooks/
    └── useVoiceInput.ts            # Voice input hook
```

### Voice Service Implementation

```tsx
// lib/voice/VoiceService.ts
import * as Speech from 'expo-speech';
import { Audio } from 'expo-av';
import * as Haptics from 'expo-haptics';

interface VoiceServiceConfig {
  language: string;
  continuous: boolean;
  onTranscript: (text: string, isFinal: boolean) => void;
  onError: (error: Error) => void;
}

class VoiceService {
  private recording: Audio.Recording | null = null;
  private isListening = false;

  async startListening(config: VoiceServiceConfig): Promise<void> {
    // Request permissions
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) {
      throw new Error('Microphone permission denied');
    }

    // Configure audio session
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
    });

    // Haptic feedback on start
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

    // Start recording
    this.recording = new Audio.Recording();
    await this.recording.prepareToRecordAsync(
      Audio.RecordingOptionsPresets.HIGH_QUALITY
    );
    await this.recording.startAsync();
    this.isListening = true;

    // Stream audio to speech recognition endpoint
    this.streamToRecognition(config);
  }

  async stopListening(): Promise<string | null> {
    if (!this.recording || !this.isListening) return null;

    this.isListening = false;
    await this.recording.stopAndUnloadAsync();

    // Haptic feedback on stop
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    const uri = this.recording.getURI();
    this.recording = null;
    return uri;
  }

  private async streamToRecognition(config: VoiceServiceConfig): Promise<void> {
    // Implementation would stream audio chunks to speech recognition API
    // Using either on-device (expo-speech) or cloud (Google/Azure) STT
  }

  async speak(text: string, options?: Speech.SpeechOptions): Promise<void> {
    await Speech.speak(text, {
      language: options?.language ?? 'en-US',
      pitch: 1.0,
      rate: 0.9,
      ...options,
    });
  }

  async stopSpeaking(): Promise<void> {
    await Speech.stop();
  }
}

export const voiceService = new VoiceService();
```

### Voice Input Hook

```tsx
// hooks/useVoiceInput.ts
import { useState, useCallback, useEffect, useRef } from 'react';
import { voiceService } from '@/lib/voice/VoiceService';
import { usePortiQStore } from '@/stores/portiq-store';

interface UseVoiceInputOptions {
  onTranscript?: (text: string) => void;
  onFinalTranscript?: (text: string) => void;
  autoSubmit?: boolean;
  language?: string;
}

export function useVoiceInput(options: UseVoiceInputOptions = {}) {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<Error | null>(null);
  const silenceTimeoutRef = useRef<NodeJS.Timeout>();

  const { sendMessage } = usePortiQStore();

  const startListening = useCallback(async () => {
    try {
      setError(null);
      setTranscript('');
      setIsListening(true);

      await voiceService.startListening({
        language: options.language ?? 'en-US',
        continuous: true,
        onTranscript: (text, isFinal) => {
          setTranscript(text);
          options.onTranscript?.(text);

          if (isFinal) {
            options.onFinalTranscript?.(text);

            // Auto-submit after silence
            if (options.autoSubmit) {
              clearTimeout(silenceTimeoutRef.current);
              silenceTimeoutRef.current = setTimeout(() => {
                stopListening();
                handleSubmit(text);
              }, 1500);
            }
          }
        },
        onError: (err) => {
          setError(err);
          setIsListening(false);
        },
      });
    } catch (err) {
      setError(err as Error);
      setIsListening(false);
    }
  }, [options]);

  const stopListening = useCallback(async () => {
    clearTimeout(silenceTimeoutRef.current);
    await voiceService.stopListening();
    setIsListening(false);
  }, []);

  const handleSubmit = useCallback(async (text: string) => {
    if (!text.trim()) return;

    setIsProcessing(true);
    try {
      await sendMessage(text);
    } finally {
      setIsProcessing(false);
      setTranscript('');
    }
  }, [sendMessage]);

  const toggleListening = useCallback(async () => {
    if (isListening) {
      await stopListening();
    } else {
      await startListening();
    }
  }, [isListening, startListening, stopListening]);

  useEffect(() => {
    return () => {
      clearTimeout(silenceTimeoutRef.current);
      voiceService.stopListening();
    };
  }, []);

  return {
    isListening,
    isProcessing,
    transcript,
    error,
    startListening,
    stopListening,
    toggleListening,
  };
}
```

### Voice-First Mobile Layout

```tsx
// components/voice/VoiceFirstLayout.tsx
import { View, StyleSheet, Dimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { VoiceInputButton } from './VoiceInputButton';
import { VoiceWaveform } from './VoiceWaveform';
import { VoiceBottomSheet } from './VoiceBottomSheet';
import { useVoiceInput } from '@/hooks/useVoiceInput';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

export function VoiceFirstLayout({ children }: { children: React.ReactNode }) {
  const insets = useSafeAreaInsets();
  const { isListening, isProcessing, transcript, toggleListening } = useVoiceInput({
    autoSubmit: true,
  });

  return (
    <View style={styles.container}>
      {/* Main content */}
      <View style={styles.content}>{children}</View>

      {/* Voice waveform overlay when listening */}
      {isListening && (
        <View style={styles.waveformOverlay}>
          <VoiceWaveform isActive={isListening} />
          {transcript && (
            <Text style={styles.transcript}>{transcript}</Text>
          )}
        </View>
      )}

      {/* Large voice button - thumb zone optimized */}
      <View style={[styles.voiceButtonContainer, { bottom: insets.bottom + 20 }]}>
        <VoiceInputButton
          state={isListening ? 'listening' : isProcessing ? 'processing' : 'idle'}
          onToggle={toggleListening}
          size="xl"
        />
      </View>

      {/* Conversation bottom sheet */}
      <VoiceBottomSheet />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'var(--background)',
  },
  content: {
    flex: 1,
    paddingBottom: 100, // Space for voice button
  },
  waveformOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  transcript: {
    color: 'white',
    fontSize: 18,
    textAlign: 'center',
    marginTop: 24,
    paddingHorizontal: 32,
  },
  voiceButtonContainer: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
  },
});
```

### Large Microphone Button Component

```tsx
// components/voice/VoiceInputButton.tsx
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  withSpring,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { Mic } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';

interface VoiceInputButtonProps {
  state: 'idle' | 'listening' | 'processing';
  onToggle: () => void;
  size?: 'md' | 'lg' | 'xl';
}

const SIZES = {
  md: { button: 56, icon: 24, ring: 72 },
  lg: { button: 72, icon: 32, ring: 96 },
  xl: { button: 88, icon: 40, ring: 120 },
};

export function VoiceInputButton({
  state,
  onToggle,
  size = 'lg',
}: VoiceInputButtonProps) {
  const dimensions = SIZES[size];

  const handlePress = () => {
    Haptics.impactAsync(
      state === 'idle'
        ? Haptics.ImpactFeedbackStyle.Medium
        : Haptics.ImpactFeedbackStyle.Light
    );
    onToggle();
  };

  // Pulsing ring animation when listening
  const ringStyle = useAnimatedStyle(() => {
    if (state !== 'listening') {
      return { opacity: 0, transform: [{ scale: 1 }] };
    }

    return {
      opacity: withRepeat(
        withTiming(0, { duration: 1500, easing: Easing.out(Easing.ease) }),
        -1,
        false
      ),
      transform: [
        {
          scale: withRepeat(
            withTiming(1.5, { duration: 1500, easing: Easing.out(Easing.ease) }),
            -1,
            false
          ),
        },
      ],
    };
  }, [state]);

  // Button scale animation
  const buttonStyle = useAnimatedStyle(() => ({
    transform: [
      {
        scale: withSpring(state === 'listening' ? 1.1 : 1, {
          damping: 15,
          stiffness: 150,
        }),
      },
    ],
  }), [state]);

  return (
    <View style={styles.container}>
      {/* Pulsing ring */}
      <Animated.View
        style={[
          styles.ring,
          {
            width: dimensions.ring,
            height: dimensions.ring,
            borderRadius: dimensions.ring / 2,
          },
          ringStyle,
        ]}
      />

      {/* Main button */}
      <Pressable onPress={handlePress} disabled={state === 'processing'}>
        <Animated.View
          style={[
            styles.button,
            {
              width: dimensions.button,
              height: dimensions.button,
              borderRadius: dimensions.button / 2,
            },
            state === 'idle' && styles.buttonIdle,
            state === 'listening' && styles.buttonListening,
            state === 'processing' && styles.buttonProcessing,
            buttonStyle,
          ]}
        >
          {state === 'processing' ? (
            <ActivityIndicator size="small" color="white" />
          ) : (
            <Mic
              size={dimensions.icon}
              color={state === 'listening' ? 'white' : '#6b7280'}
            />
          )}
        </Animated.View>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  ring: {
    position: 'absolute',
    backgroundColor: '#f97316', // secondary color
  },
  button: {
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  buttonIdle: {
    backgroundColor: '#f3f4f6',
  },
  buttonListening: {
    backgroundColor: '#f97316', // secondary color
  },
  buttonProcessing: {
    backgroundColor: '#0ea5e9', // primary color
    opacity: 0.8,
  },
});
```

### Voice Waveform Visualization

```tsx
// components/voice/VoiceWaveform.tsx
import { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
} from 'react-native-reanimated';

interface VoiceWaveformProps {
  isActive: boolean;
  barCount?: number;
}

export function VoiceWaveform({ isActive, barCount = 5 }: VoiceWaveformProps) {
  return (
    <View style={styles.container}>
      {Array.from({ length: barCount }).map((_, i) => (
        <WaveformBar key={i} index={i} isActive={isActive} />
      ))}
    </View>
  );
}

function WaveformBar({ index, isActive }: { index: number; isActive: boolean }) {
  const height = useSharedValue(20);

  useEffect(() => {
    if (isActive) {
      // Random heights for organic feel
      const minHeight = 20;
      const maxHeight = 60;
      const randomDelay = index * 100;

      height.value = withRepeat(
        withSequence(
          withTiming(maxHeight * (0.5 + Math.random() * 0.5), {
            duration: 300 + Math.random() * 200,
            easing: Easing.inOut(Easing.ease),
          }),
          withTiming(minHeight + Math.random() * 20, {
            duration: 300 + Math.random() * 200,
            easing: Easing.inOut(Easing.ease),
          })
        ),
        -1,
        true
      );
    } else {
      height.value = withTiming(20, { duration: 200 });
    }
  }, [isActive, index]);

  const animatedStyle = useAnimatedStyle(() => ({
    height: height.value,
  }));

  return (
    <Animated.View style={[styles.bar, animatedStyle]} />
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 80,
  },
  bar: {
    width: 8,
    backgroundColor: '#f97316', // secondary color
    borderRadius: 4,
  },
});
```

### Voice Bottom Sheet for Conversation

```tsx
// components/voice/VoiceBottomSheet.tsx
import { useMemo, useCallback, forwardRef } from 'react';
import { View, StyleSheet, FlatList } from 'react-native';
import BottomSheet, { BottomSheetFlatList } from '@gorhom/bottom-sheet';
import { usePortiQStore } from '@/stores/portiq-store';
import { ConversationBubble } from './ConversationBubble';

export const VoiceBottomSheet = forwardRef<BottomSheet>((_, ref) => {
  const snapPoints = useMemo(() => ['15%', '50%', '85%'], []);
  const { messages, isTyping } = usePortiQStore();

  const renderMessage = useCallback(({ item }) => (
    <ConversationBubble
      type={item.role}
      timestamp={item.timestamp}
    >
      {item.content}
    </ConversationBubble>
  ), []);

  return (
    <BottomSheet
      ref={ref}
      index={0}
      snapPoints={snapPoints}
      backgroundStyle={styles.background}
      handleIndicatorStyle={styles.indicator}
    >
      <View style={styles.header}>
        <Text style={styles.title}>PortiQ Assistant</Text>
        {isTyping && <AIThinkingIndicator variant="dots" size="sm" />}
      </View>

      <BottomSheetFlatList
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.list}
        inverted
      />
    </BottomSheet>
  );
});

const styles = StyleSheet.create({
  background: {
    backgroundColor: '#ffffff',
    borderRadius: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
  },
  indicator: {
    backgroundColor: '#d1d5db',
    width: 40,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
});
```

### Thumb Zone Optimization

The PortiQ mobile UI is designed with thumb reachability in mind:

```
┌─────────────────────────────────────┐
│                                     │
│        Context/Information          │  ← View-only zone
│           (scrollable)              │
│                                     │
├─────────────────────────────────────┤
│                                     │
│     Quick Actions (swipe cards)     │  ← Natural thumb zone
│                                     │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │      Command Bar Input       │   │  ← Easy thumb reach
│  └─────────────────────────────┘   │
│                                     │
│           ┌─────────┐              │
│           │   🎤    │              │  ← Primary CTA
│           │  Voice  │              │     Bottom center
│           └─────────┘              │
│                                     │
└─────────────────────────────────────┘
```

### Required Expo Plugins for Voice

```json
// app.json additions
{
  "expo": {
    "plugins": [
      [
        "expo-av",
        {
          "microphonePermission": "Allow $(PRODUCT_NAME) to access your microphone for voice commands."
        }
      ],
      "expo-speech"
    ],
    "ios": {
      "infoPlist": {
        "NSSpeechRecognitionUsageDescription": "Allow $(PRODUCT_NAME) to recognize your voice for hands-free procurement.",
        "NSMicrophoneUsageDescription": "Allow $(PRODUCT_NAME) to access your microphone for voice commands."
      }
    },
    "android": {
      "permissions": [
        "android.permission.RECORD_AUDIO",
        "android.permission.MODIFY_AUDIO_SETTINGS"
      ]
    }
  }
}
```

### Voice Input Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `expo-av` | Audio recording | ^14.0.0 |
| `expo-speech` | Text-to-speech | ^12.0.0 |
| `expo-haptics` | Haptic feedback | ^13.0.0 |
| `@gorhom/bottom-sheet` | Conversation sheet | ^4.6.0 |
| `react-native-reanimated` | Animations | ^3.6.0 |

---

## References
- [Expo Documentation](https://docs.expo.dev/)
- [Expo Router](https://docs.expo.dev/router/introduction/)
- [EAS Build](https://docs.expo.dev/build/introduction/)
- [EAS Update](https://docs.expo.dev/eas-update/introduction/)
- [Expo AV (Audio Recording)](https://docs.expo.dev/versions/latest/sdk/av/)
- [Expo Speech](https://docs.expo.dev/versions/latest/sdk/speech/)
- [ADR-UI-015: Command Bar & Voice Input](./ADR-UI-015-command-bar-voice-input.md)
