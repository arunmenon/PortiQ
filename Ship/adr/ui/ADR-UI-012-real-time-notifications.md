# ADR-UI-012: Real-Time Notifications

**Status:** Superseded
**Superseded By:** ADR-UI-016
**Date:** 2025-01-20 (original) | 2026-02-06 (superseded)
**Reason:** PortiQ AI-native UX specification replaces reactive notifications with proactive intelligence. See ADR-UI-016 for the new architecture.
**Technical Area:** Frontend

---

> **This ADR has been superseded.** The PortiQ UX Design introduces proactive intelligence that anticipates user needs with AI-driven suggestions rather than reactive notifications. Please refer to [ADR-UI-016](./ADR-UI-016-proactive-intelligence.md) for current architecture.

---

## Context (Historical)

The platform requires real-time notifications to keep users informed about time-sensitive events like new RFQs, bid updates, order status changes, and auction deadlines.

### Business Context
Real-time requirements:
- New RFQ notifications for suppliers
- Bid updates during auctions
- Order status changes
- Auction countdown timers
- Document processing completion
- Price alerts and reminders

### Technical Context
- NestJS backend with event system (ADR-NF-009)
- Next.js web frontend (ADR-UI-001)
- React Native mobile (ADR-UI-006)
- BullMQ for async processing (ADR-NF-008)
- Push notifications for mobile (ADR-UI-006)
- Redis for pub/sub (ADR-NF-005)

### Assumptions
- WebSocket connections are feasible
- Mobile push for background notifications
- Redis handles pub/sub at scale
- Graceful fallback to polling

---

## Decision Drivers

- Real-time latency (< 1s)
- Connection reliability
- Mobile battery efficiency
- Scalability to 10K concurrent
- Offline notification queue

---

## Considered Options

### Option 1: Socket.io with Redis Adapter
**Description:** Socket.io for bi-directional communication with Redis pub/sub.

**Pros:**
- Auto-reconnection
- Fallback transports
- Room-based broadcasting
- Good React/React Native support
- Redis adapter for scaling

**Cons:**
- Socket.io protocol overhead
- More complex than native WebSocket

### Option 2: Native WebSocket + Redis Pub/Sub
**Description:** Raw WebSocket implementation with Redis.

**Pros:**
- Minimal overhead
- Full control
- Standard protocol

**Cons:**
- Manual reconnection logic
- No automatic fallbacks
- More implementation effort

### Option 3: Server-Sent Events (SSE)
**Description:** One-way push from server.

**Pros:**
- Simple HTTP-based
- Auto-reconnection built-in
- Works through proxies

**Cons:**
- One-way only
- No binary support
- Connection limits

### Option 4: Pusher/Ably (Managed Service)
**Description:** Third-party real-time service.

**Pros:**
- Managed infrastructure
- SDKs available
- Guaranteed delivery

**Cons:**
- Vendor dependency
- Cost at scale
- Data routing through third party

---

## Decision

**Chosen Option:** Socket.io with Redis Adapter

We will use Socket.io for real-time communication between server and clients, with Redis adapter for horizontal scaling across multiple server instances.

### Rationale
Socket.io provides robust connection management with automatic reconnection and fallback transports. The Redis adapter enables scaling across multiple NestJS instances. Good ecosystem support for both React and React Native. The slight protocol overhead is acceptable for reliability benefits.

---

## Consequences

### Positive
- Reliable real-time delivery
- Automatic reconnection
- Scalable architecture
- Rich feature set

### Negative
- Socket.io overhead
- **Mitigation:** Acceptable for B2B use case
- Connection state management
- **Mitigation:** Well-documented patterns

### Risks
- High concurrent connections: Redis clustering, connection pooling
- Mobile battery drain: Intelligent connection management

---

## Implementation Notes

### Server Architecture

```
                    ┌─────────────────┐
                    │   Redis Pub/Sub │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────┴────────┐ ┌────────┴────────┐ ┌────────┴────────┐
│  NestJS Node 1  │ │  NestJS Node 2  │ │  NestJS Node 3  │
│  Socket.io      │ │  Socket.io      │ │  Socket.io      │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                      ┌──────┴──────┐
                      │   Clients   │
                      └─────────────┘
```

### NestJS Gateway Implementation

```typescript
// src/notifications/notifications.gateway.ts
import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  ConnectedSocket,
  MessageBody,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { UseGuards } from '@nestjs/common';
import { WsJwtGuard } from '@/auth/guards/ws-jwt.guard';
import { NotificationService } from './notification.service';
import { CurrentUser } from '@/auth/decorators/current-user.decorator';
import { User } from '@/users/entities/user.entity';

@WebSocketGateway({
  cors: {
    origin: process.env.CORS_ORIGINS?.split(','),
    credentials: true,
  },
  namespace: '/notifications',
})
export class NotificationsGateway
  implements OnGatewayConnection, OnGatewayDisconnect
{
  @WebSocketServer()
  server: Server;

  constructor(private notificationService: NotificationService) {}

  async handleConnection(client: Socket) {
    try {
      // Authenticate socket connection
      const user = await this.authenticateSocket(client);
      if (!user) {
        client.disconnect();
        return;
      }

      // Join user-specific room
      client.join(`user:${user.id}`);

      // Join organization room
      client.join(`org:${user.organizationId}`);

      // Store user info on socket
      client.data.user = user;

      // Send unread notification count
      const unreadCount = await this.notificationService.getUnreadCount(user.id);
      client.emit('unread_count', { count: unreadCount });

      console.log(`Client connected: ${user.id}`);
    } catch (error) {
      console.error('Socket authentication failed:', error);
      client.disconnect();
    }
  }

  async handleDisconnect(client: Socket) {
    if (client.data.user) {
      console.log(`Client disconnected: ${client.data.user.id}`);
    }
  }

  private async authenticateSocket(client: Socket): Promise<User | null> {
    const token = client.handshake.auth.token ||
      client.handshake.headers.authorization?.replace('Bearer ', '');

    if (!token) return null;

    try {
      return await this.notificationService.validateToken(token);
    } catch {
      return null;
    }
  }

  @SubscribeMessage('mark_read')
  @UseGuards(WsJwtGuard)
  async handleMarkRead(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { notificationId: string }
  ) {
    const user = client.data.user;
    await this.notificationService.markAsRead(data.notificationId, user.id);

    const unreadCount = await this.notificationService.getUnreadCount(user.id);
    client.emit('unread_count', { count: unreadCount });
  }

  @SubscribeMessage('mark_all_read')
  @UseGuards(WsJwtGuard)
  async handleMarkAllRead(@ConnectedSocket() client: Socket) {
    const user = client.data.user;
    await this.notificationService.markAllAsRead(user.id);
    client.emit('unread_count', { count: 0 });
  }

  // Methods for emitting notifications

  async notifyUser(userId: string, notification: NotificationPayload) {
    this.server.to(`user:${userId}`).emit('notification', notification);
  }

  async notifyOrganization(orgId: string, notification: NotificationPayload) {
    this.server.to(`org:${orgId}`).emit('notification', notification);
  }

  async broadcastAuctionUpdate(rfqId: string, update: AuctionUpdate) {
    this.server.to(`auction:${rfqId}`).emit('auction_update', update);
  }
}

interface NotificationPayload {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  data?: Record<string, any>;
  createdAt: string;
}

type NotificationType =
  | 'NEW_RFQ'
  | 'BID_RECEIVED'
  | 'BID_ACCEPTED'
  | 'BID_REJECTED'
  | 'ORDER_CREATED'
  | 'ORDER_STATUS'
  | 'DOCUMENT_READY'
  | 'AUCTION_ENDING'
  | 'PRICE_ALERT';
```

### Socket.io Redis Adapter Configuration

```typescript
// src/notifications/notifications.module.ts
import { Module } from '@nestjs/common';
import { createAdapter } from '@socket.io/redis-adapter';
import { createClient } from 'redis';
import { NotificationsGateway } from './notifications.gateway';
import { NotificationService } from './notification.service';

@Module({
  providers: [
    NotificationsGateway,
    NotificationService,
    {
      provide: 'REDIS_ADAPTER',
      useFactory: async () => {
        const pubClient = createClient({
          url: process.env.REDIS_URL,
        });
        const subClient = pubClient.duplicate();

        await Promise.all([pubClient.connect(), subClient.connect()]);

        return createAdapter(pubClient, subClient);
      },
    },
  ],
  exports: [NotificationsGateway, NotificationService],
})
export class NotificationsModule {}

// main.ts - Apply adapter
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { IoAdapter } from '@nestjs/platform-socket.io';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  const redisAdapter = app.get('REDIS_ADAPTER');
  app.useWebSocketAdapter(new IoAdapter(app).createIOServer(3001, {
    adapter: redisAdapter,
  }));

  await app.listen(3000);
}
```

### Notification Service with Event Integration

```typescript
// src/notifications/notification.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { OnEvent } from '@nestjs/event-emitter';
import { Notification } from './entities/notification.entity';
import { NotificationsGateway } from './notifications.gateway';
import { PushNotificationService } from './push-notification.service';

@Injectable()
export class NotificationService {
  constructor(
    @InjectRepository(Notification)
    private notificationRepo: Repository<Notification>,
    private gateway: NotificationsGateway,
    private pushService: PushNotificationService,
  ) {}

  @OnEvent('rfq.published')
  async handleRfqPublished(event: RfqPublishedEvent) {
    // Get suppliers matching RFQ categories
    const suppliers = await this.getMatchingSuppliers(event.rfq);

    for (const supplier of suppliers) {
      const notification = await this.createNotification({
        userId: supplier.userId,
        type: 'NEW_RFQ',
        title: 'New RFQ Available',
        message: `New RFQ "${event.rfq.title}" matches your product categories`,
        data: {
          rfqId: event.rfq.id,
          buyerName: event.rfq.buyer.organizationName,
          deadline: event.rfq.deadline,
        },
      });

      // Real-time notification
      this.gateway.notifyUser(supplier.userId, notification);

      // Push notification for mobile
      await this.pushService.sendPush(supplier.userId, {
        title: notification.title,
        body: notification.message,
        data: { type: 'NEW_RFQ', rfqId: event.rfq.id },
      });
    }
  }

  @OnEvent('bid.submitted')
  async handleBidSubmitted(event: BidSubmittedEvent) {
    const notification = await this.createNotification({
      userId: event.rfq.buyerId,
      type: 'BID_RECEIVED',
      title: 'New Bid Received',
      message: `${event.supplier.organizationName} submitted a bid for "${event.rfq.title}"`,
      data: {
        rfqId: event.rfq.id,
        bidId: event.bid.id,
        supplierName: event.supplier.organizationName,
      },
    });

    this.gateway.notifyUser(event.rfq.buyerId, notification);

    // Broadcast to auction room if live bidding
    if (event.rfq.auctionType === 'REVERSE') {
      this.gateway.broadcastAuctionUpdate(event.rfq.id, {
        type: 'NEW_BID',
        lowestBid: event.bid.totalAmount,
        bidsCount: event.bidsCount,
        timestamp: new Date().toISOString(),
      });
    }
  }

  @OnEvent('order.status_changed')
  async handleOrderStatusChanged(event: OrderStatusChangedEvent) {
    const notification = await this.createNotification({
      userId: event.order.buyerId,
      type: 'ORDER_STATUS',
      title: 'Order Status Updated',
      message: `Order #${event.order.number} status changed to ${event.newStatus}`,
      data: {
        orderId: event.order.id,
        orderNumber: event.order.number,
        status: event.newStatus,
      },
    });

    this.gateway.notifyUser(event.order.buyerId, notification);
    await this.pushService.sendPush(event.order.buyerId, {
      title: notification.title,
      body: notification.message,
      data: { type: 'ORDER_STATUS', orderId: event.order.id },
    });
  }

  async createNotification(data: CreateNotificationDto): Promise<Notification> {
    const notification = this.notificationRepo.create(data);
    return this.notificationRepo.save(notification);
  }

  async getUnreadCount(userId: string): Promise<number> {
    return this.notificationRepo.count({
      where: { userId, readAt: null },
    });
  }

  async markAsRead(notificationId: string, userId: string): Promise<void> {
    await this.notificationRepo.update(
      { id: notificationId, userId },
      { readAt: new Date() }
    );
  }

  async markAllAsRead(userId: string): Promise<void> {
    await this.notificationRepo.update(
      { userId, readAt: null },
      { readAt: new Date() }
    );
  }
}
```

### React Notifications Hook

```typescript
// hooks/use-notifications.ts
import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '@/stores/auth-store';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  data?: Record<string, any>;
  createdAt: string;
  readAt?: string;
}

export function useNotifications() {
  const socketRef = useRef<Socket | null>(null);
  const { isAuthenticated, accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  const [isConnected, setIsConnected] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      return;
    }

    // Initialize socket connection
    const socket = io(`${process.env.NEXT_PUBLIC_WS_URL}/notifications`, {
      auth: { token: accessToken },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      console.log('Notifications connected');
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      console.log('Notifications disconnected');
    });

    socket.on('unread_count', (data: { count: number }) => {
      setUnreadCount(data.count);
    });

    socket.on('notification', (notification: Notification) => {
      setNotifications(prev => [notification, ...prev]);
      setUnreadCount(prev => prev + 1);

      // Show toast notification
      toast(notification.title, {
        description: notification.message,
        action: notification.data?.rfqId ? {
          label: 'View',
          onClick: () => window.location.href = `/rfqs/${notification.data.rfqId}`,
        } : undefined,
      });

      // Invalidate relevant queries
      invalidateQueriesForNotification(notification, queryClient);
    });

    return () => {
      socket.disconnect();
    };
  }, [isAuthenticated, accessToken, queryClient]);

  const markAsRead = useCallback((notificationId: string) => {
    socketRef.current?.emit('mark_read', { notificationId });
    setNotifications(prev =>
      prev.map(n =>
        n.id === notificationId ? { ...n, readAt: new Date().toISOString() } : n
      )
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    socketRef.current?.emit('mark_all_read');
    setNotifications(prev =>
      prev.map(n => ({ ...n, readAt: new Date().toISOString() }))
    );
    setUnreadCount(0);
  }, []);

  return {
    isConnected,
    unreadCount,
    notifications,
    markAsRead,
    markAllAsRead,
  };
}

function invalidateQueriesForNotification(
  notification: Notification,
  queryClient: ReturnType<typeof useQueryClient>
) {
  switch (notification.type) {
    case 'NEW_RFQ':
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
      break;
    case 'BID_RECEIVED':
      queryClient.invalidateQueries({ queryKey: ['rfqs', notification.data?.rfqId] });
      queryClient.invalidateQueries({ queryKey: ['bids'] });
      break;
    case 'ORDER_STATUS':
      queryClient.invalidateQueries({ queryKey: ['orders', notification.data?.orderId] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      break;
  }
}
```

### Notification Center Component

```tsx
// components/notifications/notification-center.tsx
'use client';

import { useState } from 'react';
import { Bell, Check, CheckCheck, Settings } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useNotifications } from '@/hooks/use-notifications';
import { cn } from '@/lib/utils';
import Link from 'next/link';

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const {
    isConnected,
    unreadCount,
    notifications,
    markAsRead,
    markAllAsRead,
  } = useNotifications();

  const getNotificationLink = (notification: Notification): string => {
    switch (notification.type) {
      case 'NEW_RFQ':
        return `/opportunities/${notification.data?.rfqId}`;
      case 'BID_RECEIVED':
      case 'BID_ACCEPTED':
      case 'BID_REJECTED':
        return `/rfqs/${notification.data?.rfqId}`;
      case 'ORDER_STATUS':
      case 'ORDER_CREATED':
        return `/orders/${notification.data?.orderId}`;
      default:
        return '#';
    }
  };

  const getNotificationIcon = (type: string) => {
    // Return appropriate icon based on notification type
    const icons: Record<string, string> = {
      NEW_RFQ: '📋',
      BID_RECEIVED: '💰',
      BID_ACCEPTED: '✅',
      BID_REJECTED: '❌',
      ORDER_CREATED: '🛒',
      ORDER_STATUS: '📦',
      DOCUMENT_READY: '📄',
      AUCTION_ENDING: '⏰',
    };
    return icons[type] || '🔔';
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 min-w-5 px-1 text-xs"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
          {!isConnected && (
            <span className="absolute bottom-0 right-0 h-2 w-2 bg-yellow-500 rounded-full" />
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-96 p-0" align="end">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h3 className="font-semibold">Notifications</h3>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={markAllAsRead}
                className="text-xs"
              >
                <CheckCheck className="h-4 w-4 mr-1" />
                Mark all read
              </Button>
            )}
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link href="/settings/notifications">
                <Settings className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        {/* Notification List */}
        <ScrollArea className="h-[400px]">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <Bell className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No notifications yet</p>
            </div>
          ) : (
            <div className="divide-y">
              {notifications.map((notification) => (
                <Link
                  key={notification.id}
                  href={getNotificationLink(notification)}
                  onClick={() => {
                    if (!notification.readAt) {
                      markAsRead(notification.id);
                    }
                    setOpen(false);
                  }}
                  className={cn(
                    'flex gap-3 p-4 hover:bg-accent transition-colors',
                    !notification.readAt && 'bg-accent/50'
                  )}
                >
                  <span className="text-2xl" role="img" aria-hidden="true">
                    {getNotificationIcon(notification.type)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium leading-tight">
                      {notification.title}
                    </p>
                    <p className="text-sm text-muted-foreground line-clamp-2 mt-0.5">
                      {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(notification.createdAt), {
                        addSuffix: true,
                      })}
                    </p>
                  </div>
                  {!notification.readAt && (
                    <span className="h-2 w-2 bg-primary rounded-full shrink-0 mt-2" />
                  )}
                </Link>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Footer */}
        <div className="p-2 border-t">
          <Button variant="ghost" className="w-full text-sm" asChild>
            <Link href="/notifications">View all notifications</Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
```

### Auction Live Bidding Component

```tsx
// components/rfq/live-auction.tsx
'use client';

import { useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '@/stores/auth-store';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { formatCurrency } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface LiveAuctionProps {
  rfqId: string;
  deadline: Date;
  initialLowestBid?: number;
  initialBidsCount?: number;
}

interface AuctionUpdate {
  type: 'NEW_BID' | 'TIME_UPDATE' | 'AUCTION_ENDED';
  lowestBid?: number;
  bidsCount?: number;
  timestamp: string;
}

export function LiveAuction({
  rfqId,
  deadline,
  initialLowestBid,
  initialBidsCount = 0,
}: LiveAuctionProps) {
  const { accessToken } = useAuthStore();
  const [lowestBid, setLowestBid] = useState(initialLowestBid);
  const [bidsCount, setBidsCount] = useState(initialBidsCount);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [recentUpdate, setRecentUpdate] = useState(false);

  // Calculate time remaining
  useEffect(() => {
    const updateTime = () => {
      const remaining = Math.max(0, deadline.getTime() - Date.now());
      setTimeRemaining(remaining);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [deadline]);

  // Socket connection for auction updates
  useEffect(() => {
    const socket = io(`${process.env.NEXT_PUBLIC_WS_URL}/notifications`, {
      auth: { token: accessToken },
    });

    socket.on('connect', () => {
      setIsConnected(true);
      // Join auction room
      socket.emit('join_auction', { rfqId });
    });

    socket.on('disconnect', () => setIsConnected(false));

    socket.on('auction_update', (update: AuctionUpdate) => {
      if (update.lowestBid !== undefined) {
        setLowestBid(update.lowestBid);
      }
      if (update.bidsCount !== undefined) {
        setBidsCount(update.bidsCount);
      }

      // Visual feedback for updates
      setRecentUpdate(true);
      setTimeout(() => setRecentUpdate(false), 1000);
    });

    return () => {
      socket.emit('leave_auction', { rfqId });
      socket.disconnect();
    };
  }, [rfqId, accessToken]);

  const formatTime = (ms: number) => {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((ms % (1000 * 60)) / 1000);

    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
  };

  const isEnding = timeRemaining < 5 * 60 * 1000; // Last 5 minutes
  const isEnded = timeRemaining === 0;

  return (
    <div
      className={cn(
        'rounded-lg border p-4 transition-all',
        recentUpdate && 'ring-2 ring-primary',
        isEnding && !isEnded && 'border-destructive bg-destructive/5'
      )}
    >
      {/* Connection Status */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              isConnected ? 'bg-green-500' : 'bg-yellow-500'
            )}
          />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Live' : 'Connecting...'}
          </span>
        </div>
        <Badge variant={isEnded ? 'secondary' : isEnding ? 'destructive' : 'default'}>
          {isEnded ? 'Ended' : 'Active'}
        </Badge>
      </div>

      {/* Timer */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span>Time Remaining</span>
          <span className={cn('font-mono font-bold', isEnding && 'text-destructive')}>
            {isEnded ? 'Auction Ended' : formatTime(timeRemaining)}
          </span>
        </div>
        <Progress
          value={isEnded ? 0 : (timeRemaining / (deadline.getTime() - Date.now() + timeRemaining)) * 100}
          className={cn(isEnding && '[&>div]:bg-destructive')}
        />
      </div>

      {/* Bid Info */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Lowest Bid</p>
          <p
            className={cn(
              'text-2xl font-bold transition-colors',
              recentUpdate && 'text-primary'
            )}
          >
            {lowestBid ? formatCurrency(lowestBid) : '—'}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Total Bids</p>
          <p className="text-2xl font-bold">{bidsCount}</p>
        </div>
      </div>
    </div>
  );
}
```

### React Native Notifications

```tsx
// apps/mobile/hooks/use-mobile-notifications.ts
import { useEffect, useRef, useState } from 'react';
import { AppState, Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { io, Socket } from 'socket.io-client';
import { router } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import { useAuthStore } from '@/stores/auth-store';

export function useMobileNotifications() {
  const socketRef = useRef<Socket | null>(null);
  const appState = useRef(AppState.currentState);
  const { isAuthenticated } = useAuthStore();

  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  // Handle push notification tap
  useEffect(() => {
    const subscription = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        const data = response.notification.request.content.data;
        handleNotificationNavigation(data);
      }
    );

    return () => subscription.remove();
  }, []);

  // Manage socket connection based on app state
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextAppState) => {
      if (
        appState.current.match(/inactive|background/) &&
        nextAppState === 'active'
      ) {
        // App came to foreground - reconnect
        connectSocket();
      } else if (nextAppState.match(/inactive|background/)) {
        // App went to background - disconnect to save battery
        disconnectSocket();
      }
      appState.current = nextAppState;
    });

    return () => subscription.remove();
  }, []);

  const connectSocket = async () => {
    if (!isAuthenticated) return;

    const token = await SecureStore.getItemAsync('accessToken');
    if (!token) return;

    const socket = io(`${process.env.EXPO_PUBLIC_WS_URL}/notifications`, {
      auth: { token },
      transports: ['websocket'],
      reconnection: true,
    });

    socket.on('connect', () => setIsConnected(true));
    socket.on('disconnect', () => setIsConnected(false));

    socket.on('unread_count', (data) => {
      setUnreadCount(data.count);
      // Update app badge
      if (Platform.OS === 'ios') {
        Notifications.setBadgeCountAsync(data.count);
      }
    });

    socket.on('notification', (notification) => {
      setUnreadCount((prev) => prev + 1);

      // Show local notification when app is in foreground
      if (appState.current === 'active') {
        Notifications.scheduleNotificationAsync({
          content: {
            title: notification.title,
            body: notification.message,
            data: notification.data,
          },
          trigger: null, // Immediate
        });
      }
    });

    socketRef.current = socket;
  };

  const disconnectSocket = () => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      connectSocket();
    } else {
      disconnectSocket();
    }

    return () => disconnectSocket();
  }, [isAuthenticated]);

  return {
    unreadCount,
    isConnected,
  };
}

function handleNotificationNavigation(data: any) {
  switch (data.type) {
    case 'NEW_RFQ':
      router.push(`/(supplier)/opportunities/${data.rfqId}`);
      break;
    case 'ORDER_STATUS':
      router.push(`/(buyer)/orders/${data.orderId}`);
      break;
    case 'BID_RECEIVED':
      router.push(`/(buyer)/rfqs/${data.rfqId}`);
      break;
    default:
      router.push('/');
  }
}
```

### Dependencies
- ADR-NF-005: Redis Caching
- ADR-NF-008: BullMQ Async Processing
- ADR-NF-009: Event-Driven Communication
- ADR-UI-006: React Native with Expo

### Migration Strategy
1. Set up Socket.io gateway in NestJS
2. Configure Redis adapter
3. Implement notification service
4. Build web notification center
5. Integrate mobile push notifications
6. Add auction live bidding
7. Test reconnection scenarios
8. Monitor connection metrics
9. Optimize for mobile battery

---

## Operational Considerations

### Delivery Channels

#### Channel Matrix by Notification Type

| Notification Type | In-App | Push (Mobile) | Email | SMS | Priority |
|------------------|--------|---------------|-------|-----|----------|
| New RFQ matching categories | Yes | Yes | Yes | No | High |
| RFQ deadline approaching (24h) | Yes | Yes | Yes | No | High |
| RFQ deadline approaching (1h) | Yes | Yes | No | Yes | Critical |
| Quote received | Yes | Yes | Yes | No | High |
| Quote accepted | Yes | Yes | Yes | No | High |
| Quote rejected | Yes | No | Yes | No | Medium |
| Order confirmed | Yes | Yes | Yes | No | High |
| Order status update | Yes | Yes | No | No | Medium |
| Order shipped | Yes | Yes | Yes | No | High |
| Payment received | Yes | No | Yes | No | Medium |
| System maintenance | Yes | No | Yes | No | Low |

#### Channel Implementation

```typescript
// lib/notifications/channels.ts
interface NotificationChannel {
  id: string;
  name: string;
  isEnabled: boolean;
  send: (notification: Notification, user: User) => Promise<void>;
}

const channels: NotificationChannel[] = [
  {
    id: 'in_app',
    name: 'In-App',
    isEnabled: true,
    send: async (notification, user) => {
      await socketGateway.notifyUser(user.id, notification);
      await notificationRepository.create(notification);
    },
  },
  {
    id: 'push',
    name: 'Push Notification',
    isEnabled: true,
    send: async (notification, user) => {
      if (!user.pushTokens?.length) return;

      await expo.sendPushNotificationsAsync(
        user.pushTokens.map(token => ({
          to: token,
          title: notification.title,
          body: notification.message,
          data: notification.data,
          priority: notification.priority === 'critical' ? 'high' : 'default',
        }))
      );
    },
  },
  {
    id: 'email',
    name: 'Email',
    isEnabled: true,
    send: async (notification, user) => {
      await emailService.send({
        to: user.email,
        template: `notification-${notification.type}`,
        data: notification,
      });
    },
  },
  {
    id: 'sms',
    name: 'SMS',
    isEnabled: true,
    send: async (notification, user) => {
      if (!user.phone || notification.priority !== 'critical') return;

      await smsService.send({
        to: user.phone,
        message: `${notification.title}: ${notification.message}`,
      });
    },
  },
];
```

### User Preferences

#### Preference Schema

```typescript
// User notification preferences stored in database
interface NotificationPreferences {
  userId: string;

  // Channel preferences
  channels: {
    in_app: { enabled: boolean };
    push: { enabled: boolean };
    email: { enabled: boolean; digest: 'immediate' | 'daily' | 'weekly' };
    sms: { enabled: boolean; criticalOnly: boolean };
  };

  // Category preferences
  categories: {
    rfq_updates: { enabled: boolean; channels: string[] };
    order_updates: { enabled: boolean; channels: string[] };
    quote_updates: { enabled: boolean; channels: string[] };
    system_updates: { enabled: boolean; channels: string[] };
    marketing: { enabled: boolean; channels: string[] };
  };

  // Timing preferences
  quietHours: {
    enabled: boolean;
    start: string;  // "22:00"
    end: string;    // "07:00"
    timezone: string;
    exceptCritical: boolean;
  };

  // Frequency limits
  frequencyLimits: {
    maxPushPerHour: number;      // Default: 10
    maxEmailPerDay: number;      // Default: 20
    maxSmsPerDay: number;        // Default: 5
  };
}
```

#### Preferences UI

```typescript
// components/settings/notification-preferences.tsx
export function NotificationPreferences() {
  const { data: prefs, isLoading } = useNotificationPreferences();
  const updatePrefs = useUpdateNotificationPreferences();

  return (
    <div className="space-y-6">
      {/* Channel toggles */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Channels</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Push Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Receive alerts on your mobile device
              </p>
            </div>
            <Switch
              checked={prefs?.channels.push.enabled}
              onCheckedChange={(enabled) =>
                updatePrefs.mutate({ channels: { push: { enabled } } })
              }
            />
          </div>
          {/* Similar for email, sms */}
        </CardContent>
      </Card>

      {/* Category preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Types</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>In-App</TableHead>
                <TableHead>Push</TableHead>
                <TableHead>Email</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(prefs?.categories || {}).map(([category, settings]) => (
                <TableRow key={category}>
                  <TableCell>{formatCategoryName(category)}</TableCell>
                  {['in_app', 'push', 'email'].map((channel) => (
                    <TableCell key={channel}>
                      <Checkbox
                        checked={settings.channels.includes(channel)}
                        onCheckedChange={(checked) =>
                          updateCategoryChannel(category, channel, checked)
                        }
                      />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Quiet hours */}
      <Card>
        <CardHeader>
          <CardTitle>Quiet Hours</CardTitle>
          <CardDescription>
            Pause non-critical notifications during specific hours
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Enable Quiet Hours</Label>
            <Switch
              checked={prefs?.quietHours.enabled}
              onCheckedChange={(enabled) =>
                updatePrefs.mutate({ quietHours: { enabled } })
              }
            />
          </div>
          {prefs?.quietHours.enabled && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Start Time</Label>
                  <TimeInput
                    value={prefs.quietHours.start}
                    onChange={(start) =>
                      updatePrefs.mutate({ quietHours: { start } })
                    }
                  />
                </div>
                <div>
                  <Label>End Time</Label>
                  <TimeInput
                    value={prefs.quietHours.end}
                    onChange={(end) =>
                      updatePrefs.mutate({ quietHours: { end } })
                    }
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={prefs.quietHours.exceptCritical}
                  onCheckedChange={(checked) =>
                    updatePrefs.mutate({ quietHours: { exceptCritical: checked } })
                  }
                />
                <Label>Allow critical notifications during quiet hours</Label>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

### Reliability Guarantees

#### Delivery Guarantees by Channel

| Channel | Guarantee | Retry Policy | Fallback |
|---------|-----------|--------------|----------|
| In-App | At-least-once | 3 retries, 1s backoff | Store for later |
| Push | Best-effort | 3 retries | Queue for next connect |
| Email | At-least-once | 5 retries, exponential | Alert after 24h fail |
| SMS | At-least-once | 3 retries | Email fallback |

#### Implementation

```typescript
// lib/notifications/delivery-service.ts
class NotificationDeliveryService {
  async deliver(notification: Notification, user: User): Promise<DeliveryResult> {
    const prefs = await this.getPreferences(user.id);
    const channels = this.getEnabledChannels(notification.type, prefs);

    const results: ChannelResult[] = [];

    for (const channel of channels) {
      try {
        // Check quiet hours
        if (this.isQuietHours(prefs) && notification.priority !== 'critical') {
          results.push({ channel: channel.id, status: 'deferred', reason: 'quiet_hours' });
          await this.queueForLater(notification, user, channel);
          continue;
        }

        // Check rate limits
        if (await this.isRateLimited(user.id, channel.id)) {
          results.push({ channel: channel.id, status: 'rate_limited' });
          continue;
        }

        // Attempt delivery with retry
        await this.deliverWithRetry(notification, user, channel);
        results.push({ channel: channel.id, status: 'delivered' });

      } catch (error) {
        results.push({ channel: channel.id, status: 'failed', error: error.message });
        await this.logFailure(notification, channel, error);
      }
    }

    return { notificationId: notification.id, channels: results };
  }

  private async deliverWithRetry(
    notification: Notification,
    user: User,
    channel: NotificationChannel,
    attempt = 1
  ): Promise<void> {
    const maxRetries = channel.id === 'email' ? 5 : 3;
    const baseDelay = 1000;

    try {
      await channel.send(notification, user);
    } catch (error) {
      if (attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt - 1);
        await sleep(delay);
        return this.deliverWithRetry(notification, user, channel, attempt + 1);
      }
      throw error;
    }
  }
}
```

### Batching & Aggregation

#### Batching Rules

| Notification Type | Batch Window | Max Batch Size | Aggregation |
|------------------|--------------|----------------|-------------|
| New RFQs | 5 minutes | 10 | "You have X new RFQs" |
| Quote updates | 10 minutes | 20 | "X quotes updated" |
| Order status | No batching | 1 | Individual |
| System alerts | 1 hour | 50 | Summary digest |

#### Batch Implementation

```typescript
// lib/notifications/batch-processor.ts
class NotificationBatchProcessor {
  private batchConfig: Record<string, BatchConfig> = {
    NEW_RFQ: { windowMs: 5 * 60 * 1000, maxSize: 10 },
    QUOTE_UPDATE: { windowMs: 10 * 60 * 1000, maxSize: 20 },
    SYSTEM_ALERT: { windowMs: 60 * 60 * 1000, maxSize: 50 },
  };

  async queueForBatch(notification: Notification, userId: string): Promise<void> {
    const config = this.batchConfig[notification.type];
    if (!config) {
      // No batching - deliver immediately
      return this.deliveryService.deliver(notification);
    }

    const batchKey = `batch:${userId}:${notification.type}`;
    await redis.rpush(batchKey, JSON.stringify(notification));
    await redis.expire(batchKey, config.windowMs / 1000);

    // Schedule batch processing
    const count = await redis.llen(batchKey);
    if (count >= config.maxSize) {
      await this.processBatch(userId, notification.type);
    } else if (count === 1) {
      // First item - schedule timer
      setTimeout(() => this.processBatch(userId, notification.type), config.windowMs);
    }
  }

  private async processBatch(userId: string, type: string): Promise<void> {
    const batchKey = `batch:${userId}:${type}`;
    const items = await redis.lrange(batchKey, 0, -1);
    await redis.del(batchKey);

    if (items.length === 0) return;

    const notifications = items.map(item => JSON.parse(item));
    const aggregated = this.aggregate(notifications, type);

    await this.deliveryService.deliver(aggregated);
  }

  private aggregate(notifications: Notification[], type: string): Notification {
    // Create summary notification
    const count = notifications.length;
    const templates = {
      NEW_RFQ: {
        title: 'New RFQ Opportunities',
        message: `You have ${count} new RFQs matching your categories`,
      },
      QUOTE_UPDATE: {
        title: 'Quote Updates',
        message: `${count} quotes have been updated`,
      },
    };

    return {
      ...notifications[0],
      ...templates[type],
      data: {
        count,
        items: notifications.map(n => n.data),
      },
    };
  }
}
```

### Deduplication

#### Deduplication Rules

| Scope | Window | Key | Action |
|-------|--------|-----|--------|
| Same notification | 5 minutes | `{userId}:{type}:{entityId}` | Skip duplicate |
| Similar content | 1 minute | `{userId}:{hash(message)}` | Skip duplicate |
| Rapid updates | 30 seconds | `{userId}:{entityId}` | Coalesce to latest |

```typescript
// lib/notifications/deduplication.ts
class NotificationDeduplicator {
  async shouldDeliver(notification: Notification, userId: string): Promise<boolean> {
    // Check for exact duplicate
    const exactKey = `dedup:${userId}:${notification.type}:${notification.data.entityId}`;
    const exists = await redis.exists(exactKey);
    if (exists) {
      return false; // Skip duplicate
    }

    // Check for content similarity
    const contentHash = this.hashContent(notification.message);
    const contentKey = `dedup:content:${userId}:${contentHash}`;
    const contentExists = await redis.exists(contentKey);
    if (contentExists) {
      return false; // Skip similar content
    }

    // Mark as seen
    await redis.setex(exactKey, 300, '1');     // 5 minutes
    await redis.setex(contentKey, 60, '1');    // 1 minute

    return true;
  }

  async coalesceRapidUpdates(notification: Notification, userId: string): Promise<Notification | null> {
    const coalesceKey = `coalesce:${userId}:${notification.data.entityId}`;
    const pending = await redis.get(coalesceKey);

    if (pending) {
      // Update the pending notification with latest data
      const updated = { ...JSON.parse(pending), ...notification, updatedAt: Date.now() };
      await redis.setex(coalesceKey, 30, JSON.stringify(updated));
      return null; // Don't deliver yet
    }

    // Store and schedule delivery
    await redis.setex(coalesceKey, 30, JSON.stringify(notification));
    setTimeout(() => this.deliverCoalesced(coalesceKey), 30000);

    return null;
  }
}
```

### Offline & Muted User Experience

#### Fallback Strategy

| Scenario | Behavior | User Experience |
|----------|----------|-----------------|
| User offline (web) | Store notification | Badge + list on reconnect |
| User offline (mobile) | Push notification queued | Delivered when online |
| App backgrounded | Push notification | System notification |
| Push disabled | Email fallback | Email within 5 min |
| All channels disabled | Store only | In-app list when opened |
| Quiet hours | Queue non-critical | Batch deliver after quiet hours |

#### Implementation

```typescript
// Offline notification queue
class OfflineNotificationQueue {
  async queueForOfflineUser(notification: Notification, userId: string): Promise<void> {
    const queueKey = `offline:${userId}`;

    // Store notification
    await redis.lpush(queueKey, JSON.stringify({
      ...notification,
      queuedAt: Date.now(),
    }));

    // Limit queue size (keep latest 100)
    await redis.ltrim(queueKey, 0, 99);

    // Set TTL (7 days)
    await redis.expire(queueKey, 7 * 24 * 60 * 60);
  }

  async deliverQueuedNotifications(userId: string): Promise<number> {
    const queueKey = `offline:${userId}`;
    const notifications = await redis.lrange(queueKey, 0, -1);

    if (notifications.length === 0) return 0;

    // Clear queue
    await redis.del(queueKey);

    // Deliver as batch summary
    const parsed = notifications.map(n => JSON.parse(n));
    await this.deliverySummary(userId, parsed);

    return notifications.length;
  }
}

// Socket connection handler
socket.on('connect', async () => {
  const userId = socket.data.user.id;

  // Deliver any queued notifications
  const count = await offlineQueue.deliverQueuedNotifications(userId);

  if (count > 0) {
    socket.emit('queued_notifications', { count });
  }

  // Send current unread count
  const unread = await notificationService.getUnreadCount(userId);
  socket.emit('unread_count', { count: unread });
});
```

### Open Questions - Resolved

- **Q:** What is the fallback experience for offline or muted users?
  - **A:** We implement a comprehensive fallback strategy:
    1. **Offline users**: Notifications queued in Redis (7-day retention, max 100 per user); delivered as summary when user reconnects
    2. **Push disabled**: Email fallback within 5 minutes for high-priority notifications
    3. **Email disabled**: In-app only; badge count increases; full list available when app opened
    4. **All channels muted**: Notifications stored in database; visible in notification center when user unmutes or opens app
    5. **Quiet hours**: Non-critical notifications queued; delivered as batch when quiet hours end; critical notifications (e.g., 1-hour RFQ deadline) bypass quiet hours per user preference
    6. **Reconnection UX**: Socket reconnect triggers immediate delivery of queued notifications with summary toast ("You have X notifications while you were away")

---

## References
- [Socket.io Documentation](https://socket.io/docs/v4/)
- [NestJS WebSockets](https://docs.nestjs.com/websockets/gateways)
- [Socket.io Redis Adapter](https://socket.io/docs/v4/redis-adapter/)
- [Expo Push Notifications](https://docs.expo.dev/push-notifications/overview/)
