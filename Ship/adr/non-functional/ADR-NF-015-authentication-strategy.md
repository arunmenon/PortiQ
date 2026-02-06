# ADR-NF-015: Authentication Strategy

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Security

---

## Context

The platform requires secure authentication for B2B users across web and mobile applications with support for multi-tenant organizations.

### Business Context
Authentication requirements:
- Multiple user types (buyers, suppliers, admins)
- Organization-based access (multi-tenancy)
- Mobile app support (offline considerations)
- API access for integrations
- Session management across devices
- Audit trail for compliance

### Technical Context
- NestJS backend (ADR-NF-006)
- Next.js web frontend (ADR-UI-001)
- React Native mobile app (ADR-UI-006)
- Multi-tenant data model (ADR-FN-023)
- API-first architecture (ADR-NF-007)

### Assumptions
- JWT-based authentication preferred for stateless APIs
- Refresh token rotation for security
- OAuth2 for external integrations
- Password-based auth for MVP, SSO later
- Mobile needs long-lived but secure sessions

---

## Decision Drivers

- Security best practices
- Stateless API compatibility
- Mobile offline support
- Developer experience
- Scalability
- Compliance requirements

---

## Considered Options

### Option 1: JWT with Refresh Tokens
**Description:** Short-lived access tokens with rotating refresh tokens.

**Pros:**
- Stateless API servers
- Scalable horizontally
- Mobile-friendly
- Standard approach
- Can include claims for authorization

**Cons:**
- Token revocation complexity
- Token size can grow
- Need secure refresh token storage

### Option 2: Session-Based Auth
**Description:** Server-side sessions with cookies.

**Pros:**
- Simple revocation
- Smaller token size
- Traditional approach

**Cons:**
- Requires session store
- Harder to scale
- Cookie limitations for APIs
- Mobile complexity

### Option 3: AWS Cognito
**Description:** Managed authentication service.

**Pros:**
- Fully managed
- Built-in MFA
- Social login support
- Scales automatically

**Cons:**
- AWS lock-in
- Limited customization
- Cost at scale
- Complex user migration

### Option 4: Auth0
**Description:** Third-party identity platform.

**Pros:**
- Feature-rich
- Great documentation
- Enterprise features
- Social login

**Cons:**
- Expensive at scale
- External dependency
- Data residency concerns
- Vendor lock-in

---

## Decision

**Chosen Option:** JWT with Refresh Tokens (Custom Implementation)

We will implement JWT-based authentication with rotating refresh tokens using Passport.js in NestJS, storing minimal session data in Redis for token management.

### Rationale
JWT tokens align with our API-first architecture and enable horizontal scaling. Custom implementation provides full control over the authentication flow and avoids vendor lock-in. Redis-backed refresh tokens enable secure rotation and revocation. This approach works well for both web and mobile clients.

---

## Consequences

### Positive
- Stateless API servers
- Full control over auth flow
- No vendor lock-in
- Works across all clients
- Scalable architecture

### Negative
- Implementation complexity
- **Mitigation:** Use proven libraries (Passport.js, jose)
- Token management responsibility
- **Mitigation:** Redis for refresh token tracking

### Risks
- Token theft: Short access token lifetime, HTTPS only, secure storage
- Refresh token compromise: Rotation, device binding, anomaly detection
- Brute force: Rate limiting, account lockout

---

## Implementation Notes

### Token Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Token Flow                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Login Request                                                       │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Verify    │───▶│   Generate  │───▶│   Return Tokens          │ │
│  │ Credentials │    │   Tokens    │    │   - Access (15min)       │ │
│  └─────────────┘    └─────────────┘    │   - Refresh (7 days)     │ │
│                            │           └─────────────────────────┘  │
│                            ▼                                         │
│                     ┌─────────────┐                                  │
│                     │   Store in  │                                  │
│                     │    Redis    │                                  │
│                     │  (Refresh)  │                                  │
│                     └─────────────┘                                  │
│                                                                      │
│  Token Refresh                                                       │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Verify    │───▶│   Rotate    │───▶│   New Token Pair         │ │
│  │   Refresh   │    │   Token     │    │   (Old refresh revoked)  │ │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Auth Module Configuration

```typescript
// auth/auth.module.ts
import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';

@Module({
  imports: [
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: async (configService: ConfigService) => ({
        secret: configService.get('JWT_SECRET'),
        signOptions: {
          expiresIn: '15m',
          issuer: 'ship-chandlery',
          audience: 'ship-chandlery-api',
        },
      }),
      inject: [ConfigService],
    }),
  ],
  providers: [
    AuthService,
    JwtStrategy,
    LocalStrategy,
    RefreshTokenStrategy,
  ],
  controllers: [AuthController],
  exports: [AuthService],
})
export class AuthModule {}
```

### JWT Strategy

```typescript
// auth/strategies/jwt.strategy.ts
import { ExtractJwt, Strategy } from 'passport-jwt';
import { PassportStrategy } from '@nestjs/passport';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    private readonly configService: ConfigService,
    private readonly usersService: UsersService,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: configService.get('JWT_SECRET'),
      issuer: 'ship-chandlery',
      audience: 'ship-chandlery-api',
    });
  }

  async validate(payload: JwtPayload): Promise<AuthenticatedUser> {
    const user = await this.usersService.findById(payload.sub);

    if (!user || !user.isActive) {
      throw new UnauthorizedException('User not found or inactive');
    }

    return {
      id: user.id,
      email: user.email,
      organizationId: user.organizationId,
      organizationType: user.organization.type,
      roles: user.roles,
      permissions: await this.usersService.getPermissions(user.id),
    };
  }
}

interface JwtPayload {
  sub: string;          // User ID
  email: string;
  orgId: string;        // Organization ID
  orgType: string;      // buyer | supplier | admin
  roles: string[];
  iat: number;
  exp: number;
}
```

### Auth Service

```typescript
// auth/services/auth.service.ts
@Injectable()
export class AuthService {
  constructor(
    private readonly usersService: UsersService,
    private readonly jwtService: JwtService,
    private readonly refreshTokenService: RefreshTokenService,
    private readonly configService: ConfigService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  async login(loginDto: LoginDto, metadata: LoginMetadata): Promise<AuthTokens> {
    const user = await this.validateUser(loginDto.email, loginDto.password);

    if (!user) {
      await this.recordFailedAttempt(loginDto.email, metadata);
      throw new UnauthorizedException('Invalid credentials');
    }

    if (user.requiresMfa && !loginDto.mfaCode) {
      return { requiresMfa: true, mfaToken: await this.generateMfaToken(user) };
    }

    const tokens = await this.generateTokens(user, metadata);

    this.eventEmitter.emit('auth.login', {
      userId: user.id,
      email: user.email,
      ip: metadata.ip,
      userAgent: metadata.userAgent,
      timestamp: new Date(),
    });

    return tokens;
  }

  async validateUser(email: string, password: string): Promise<User | null> {
    const user = await this.usersService.findByEmail(email);

    if (!user) {
      // Timing attack mitigation
      await bcrypt.compare(password, '$2b$10$dummy.hash.for.timing');
      return null;
    }

    if (user.lockedUntil && user.lockedUntil > new Date()) {
      throw new UnauthorizedException('Account is locked');
    }

    const isValid = await bcrypt.compare(password, user.passwordHash);

    if (!isValid) {
      return null;
    }

    return user;
  }

  async generateTokens(user: User, metadata: LoginMetadata): Promise<AuthTokens> {
    const payload: JwtPayload = {
      sub: user.id,
      email: user.email,
      orgId: user.organizationId,
      orgType: user.organization.type,
      roles: user.roles.map(r => r.name),
    };

    const [accessToken, refreshToken] = await Promise.all([
      this.jwtService.signAsync(payload),
      this.refreshTokenService.create(user.id, metadata),
    ]);

    return {
      accessToken,
      refreshToken,
      expiresIn: 900, // 15 minutes
      tokenType: 'Bearer',
    };
  }

  async refreshTokens(refreshToken: string, metadata: LoginMetadata): Promise<AuthTokens> {
    const tokenData = await this.refreshTokenService.validate(refreshToken);

    if (!tokenData) {
      throw new UnauthorizedException('Invalid refresh token');
    }

    // Revoke old token (rotation)
    await this.refreshTokenService.revoke(refreshToken);

    const user = await this.usersService.findById(tokenData.userId);

    if (!user || !user.isActive) {
      throw new UnauthorizedException('User not found or inactive');
    }

    return this.generateTokens(user, metadata);
  }

  async logout(userId: string, refreshToken?: string): Promise<void> {
    if (refreshToken) {
      await this.refreshTokenService.revoke(refreshToken);
    } else {
      // Revoke all refresh tokens for user
      await this.refreshTokenService.revokeAllForUser(userId);
    }

    this.eventEmitter.emit('auth.logout', { userId, timestamp: new Date() });
  }

  async logoutAllDevices(userId: string): Promise<void> {
    await this.refreshTokenService.revokeAllForUser(userId);
    this.eventEmitter.emit('auth.logout_all', { userId, timestamp: new Date() });
  }

  private async recordFailedAttempt(email: string, metadata: LoginMetadata): Promise<void> {
    const key = `failed_attempts:${email}`;
    const attempts = await this.redis.incr(key);
    await this.redis.expire(key, 3600); // 1 hour window

    if (attempts >= 5) {
      await this.usersService.lockAccount(email, 15 * 60 * 1000); // 15 minutes
    }

    this.eventEmitter.emit('auth.failed_attempt', {
      email,
      attempts,
      ip: metadata.ip,
      timestamp: new Date(),
    });
  }
}
```

### Refresh Token Service

```typescript
// auth/services/refresh-token.service.ts
@Injectable()
export class RefreshTokenService {
  private readonly TOKEN_PREFIX = 'refresh_token:';
  private readonly USER_TOKENS_PREFIX = 'user_tokens:';
  private readonly TOKEN_TTL = 7 * 24 * 60 * 60; // 7 days

  constructor(
    @Inject('REDIS_CLIENT')
    private readonly redis: Redis,
    private readonly configService: ConfigService,
  ) {}

  async create(userId: string, metadata: LoginMetadata): Promise<string> {
    const token = crypto.randomBytes(64).toString('base64url');
    const hashedToken = this.hashToken(token);

    const tokenData: RefreshTokenData = {
      userId,
      deviceId: metadata.deviceId || crypto.randomUUID(),
      userAgent: metadata.userAgent,
      ip: metadata.ip,
      createdAt: new Date().toISOString(),
    };

    // Store token data
    await this.redis.setex(
      `${this.TOKEN_PREFIX}${hashedToken}`,
      this.TOKEN_TTL,
      JSON.stringify(tokenData)
    );

    // Track user's tokens
    await this.redis.sadd(`${this.USER_TOKENS_PREFIX}${userId}`, hashedToken);

    return token;
  }

  async validate(token: string): Promise<RefreshTokenData | null> {
    const hashedToken = this.hashToken(token);
    const data = await this.redis.get(`${this.TOKEN_PREFIX}${hashedToken}`);

    if (!data) {
      return null;
    }

    return JSON.parse(data);
  }

  async revoke(token: string): Promise<void> {
    const hashedToken = this.hashToken(token);
    const data = await this.validate(token);

    if (data) {
      await this.redis.del(`${this.TOKEN_PREFIX}${hashedToken}`);
      await this.redis.srem(`${this.USER_TOKENS_PREFIX}${data.userId}`, hashedToken);
    }
  }

  async revokeAllForUser(userId: string): Promise<void> {
    const tokens = await this.redis.smembers(`${this.USER_TOKENS_PREFIX}${userId}`);

    if (tokens.length > 0) {
      const pipeline = this.redis.pipeline();
      tokens.forEach(token => {
        pipeline.del(`${this.TOKEN_PREFIX}${token}`);
      });
      pipeline.del(`${this.USER_TOKENS_PREFIX}${userId}`);
      await pipeline.exec();
    }
  }

  async getActiveSessions(userId: string): Promise<SessionInfo[]> {
    const tokens = await this.redis.smembers(`${this.USER_TOKENS_PREFIX}${userId}`);
    const sessions: SessionInfo[] = [];

    for (const hashedToken of tokens) {
      const data = await this.redis.get(`${this.TOKEN_PREFIX}${hashedToken}`);
      if (data) {
        const tokenData = JSON.parse(data);
        sessions.push({
          deviceId: tokenData.deviceId,
          userAgent: tokenData.userAgent,
          ip: tokenData.ip,
          createdAt: tokenData.createdAt,
        });
      }
    }

    return sessions;
  }

  private hashToken(token: string): string {
    return crypto.createHash('sha256').update(token).digest('hex');
  }
}
```

### Auth Controller

```typescript
// auth/controllers/auth.controller.ts
@Controller('api/v1/auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Post('login')
  @HttpCode(200)
  @Throttle({ default: { limit: 5, ttl: 60000 } })
  async login(
    @Body() loginDto: LoginDto,
    @Req() req: Request,
  ): Promise<AuthTokens> {
    return this.authService.login(loginDto, {
      ip: req.ip,
      userAgent: req.headers['user-agent'],
      deviceId: req.headers['x-device-id'] as string,
    });
  }

  @Post('refresh')
  @HttpCode(200)
  async refresh(
    @Body() refreshDto: RefreshTokenDto,
    @Req() req: Request,
  ): Promise<AuthTokens> {
    return this.authService.refreshTokens(refreshDto.refreshToken, {
      ip: req.ip,
      userAgent: req.headers['user-agent'],
      deviceId: req.headers['x-device-id'] as string,
    });
  }

  @Post('logout')
  @UseGuards(JwtAuthGuard)
  @HttpCode(204)
  async logout(
    @CurrentUser() user: AuthenticatedUser,
    @Body() logoutDto: LogoutDto,
  ): Promise<void> {
    await this.authService.logout(user.id, logoutDto.refreshToken);
  }

  @Post('logout-all')
  @UseGuards(JwtAuthGuard)
  @HttpCode(204)
  async logoutAll(@CurrentUser() user: AuthenticatedUser): Promise<void> {
    await this.authService.logoutAllDevices(user.id);
  }

  @Get('sessions')
  @UseGuards(JwtAuthGuard)
  async getSessions(@CurrentUser() user: AuthenticatedUser): Promise<SessionInfo[]> {
    return this.authService.getActiveSessions(user.id);
  }

  @Post('register')
  @Throttle({ default: { limit: 3, ttl: 60000 } })
  async register(@Body() registerDto: RegisterDto): Promise<{ message: string }> {
    await this.authService.register(registerDto);
    return { message: 'Registration successful. Please verify your email.' };
  }

  @Post('forgot-password')
  @Throttle({ default: { limit: 3, ttl: 60000 } })
  @HttpCode(200)
  async forgotPassword(@Body() dto: ForgotPasswordDto): Promise<{ message: string }> {
    await this.authService.sendPasswordResetEmail(dto.email);
    return { message: 'If an account exists, a reset email has been sent.' };
  }

  @Post('reset-password')
  @HttpCode(200)
  async resetPassword(@Body() dto: ResetPasswordDto): Promise<{ message: string }> {
    await this.authService.resetPassword(dto.token, dto.newPassword);
    return { message: 'Password has been reset successfully.' };
  }
}
```

### Password Hashing

```typescript
// auth/utils/password.util.ts
import * as bcrypt from 'bcrypt';

export class PasswordUtil {
  private static readonly SALT_ROUNDS = 12;

  static async hash(password: string): Promise<string> {
    return bcrypt.hash(password, this.SALT_ROUNDS);
  }

  static async verify(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
  }

  static validate(password: string): ValidationResult {
    const errors: string[] = [];

    if (password.length < 8) {
      errors.push('Password must be at least 8 characters');
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter');
    }
    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter');
    }
    if (!/[0-9]/.test(password)) {
      errors.push('Password must contain at least one number');
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
      errors.push('Password must contain at least one special character');
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }
}
```

### Guards and Decorators

```typescript
// auth/guards/jwt-auth.guard.ts
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    return super.canActivate(context);
  }

  handleRequest(err: any, user: any, info: any) {
    if (err || !user) {
      throw err || new UnauthorizedException('Authentication required');
    }
    return user;
  }
}

// auth/guards/roles.guard.ts
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<string[]>('roles', [
      context.getHandler(),
      context.getClass(),
    ]);

    if (!requiredRoles) {
      return true;
    }

    const { user } = context.switchToHttp().getRequest();
    return requiredRoles.some(role => user.roles?.includes(role));
  }
}

// auth/decorators/roles.decorator.ts
export const Roles = (...roles: string[]) => SetMetadata('roles', roles);

// auth/decorators/current-user.decorator.ts
export const CurrentUser = createParamDecorator(
  (data: keyof AuthenticatedUser, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);
```

### Mobile Token Storage

```typescript
// React Native - Secure token storage
import * as SecureStore from 'expo-secure-store';

export const TokenStorage = {
  async setTokens(tokens: AuthTokens): Promise<void> {
    await SecureStore.setItemAsync('accessToken', tokens.accessToken);
    await SecureStore.setItemAsync('refreshToken', tokens.refreshToken);
  },

  async getAccessToken(): Promise<string | null> {
    return SecureStore.getItemAsync('accessToken');
  },

  async getRefreshToken(): Promise<string | null> {
    return SecureStore.getItemAsync('refreshToken');
  },

  async clearTokens(): Promise<void> {
    await SecureStore.deleteItemAsync('accessToken');
    await SecureStore.deleteItemAsync('refreshToken');
  },
};
```

### Dependencies
- ADR-NF-006: Modular Monolith vs Microservices
- ADR-NF-005: Caching Strategy (Redis)
- ADR-FN-023: Multi-Tenant User Model

### Migration Strategy
1. Set up Passport.js with JWT strategy
2. Implement refresh token service with Redis
3. Create auth controller endpoints
4. Add guards and decorators
5. Implement password reset flow
6. Set up audit logging
7. Configure rate limiting

---

## Identity Provider and MFA

### Identity Provider Strategy

| User Type | Identity Provider | Rationale |
|-----------|-------------------|-----------|
| Platform users (MVP) | Built-in (email/password) | Simplicity, full control |
| Enterprise SSO (future) | SAML/OIDC integration | Customer requirement |
| Admin users | Built-in + enforced MFA | Security |

**MVP Approach**: Built-in authentication with bcrypt password hashing, with hooks for future IdP integration.

### MFA Requirements

| User Role | MFA Required | Methods |
|-----------|--------------|---------|
| Platform admin | Yes (mandatory) | TOTP (Authenticator app) |
| Organization owner | Yes (mandatory) | TOTP, SMS (backup) |
| Organization admin | Configurable (org policy) | TOTP |
| Regular member | Optional (user choice) | TOTP |

```typescript
// MFA configuration per organization
interface OrganizationSecurityPolicy {
  mfaRequired: boolean;
  mfaEnforcedRoles: Role[];
  allowedMfaMethods: ('totp' | 'sms' | 'email')[];
  sessionTimeout: number; // minutes
}
```

### Session Lifetimes

| Token Type | Lifetime | Refresh | Revocable |
|------------|----------|---------|-----------|
| Access token | 15 minutes | Via refresh token | No (short-lived) |
| Refresh token | 7 days | On use (rotation) | Yes |
| MFA session | 30 days | Requires re-auth | Yes |
| Password reset | 1 hour | N/A | Single use |
| Email verification | 24 hours | Resend available | Single use |

## Tenant-Aware Authorization

### Multi-Tenant Auth Model

```
┌─────────────────────────────────────────────────────────────┐
│                      JWT Token Claims                        │
├─────────────────────────────────────────────────────────────┤
│ {                                                            │
│   "sub": "user-uuid",                                       │
│   "email": "user@example.com",                              │
│   "org_id": "org-uuid",           // Current org context    │
│   "org_role": "admin",            // Role in current org    │
│   "orgs": [                       // All org memberships    │
│     { "id": "org-1", "role": "owner" },                     │
│     { "id": "org-2", "role": "member" }                     │
│   ],                                                         │
│   "platform_role": "user",        // Platform-wide role     │
│   "permissions": ["rfq:create", "orders:view"]              │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
```

### Role Hierarchy

| Role | Scope | Description | Capabilities |
|------|-------|-------------|--------------|
| **Platform Admin** | Platform | System administrator | All operations, cross-tenant |
| **Broker** | Platform | Multi-tenant operator | View/act on behalf of multiple orgs |
| **Owner** | Organization | Org owner | Full org control, billing, delete |
| **Admin** | Organization | Org admin | User management, settings |
| **Member** | Organization | Standard user | Create RFQs, orders |
| **Viewer** | Organization | Read-only | View only, no actions |

### Broker Role Implementation

```typescript
// Broker can switch organization context
@Post('switch-organization')
@Roles('broker', 'platform_admin')
async switchOrganization(
  @CurrentUser() user: User,
  @Body('organizationId') orgId: string
): Promise<TokenPair> {
  // Verify broker has access to target org
  const access = await this.brokerService.verifyAccess(user.id, orgId);
  if (!access) throw new ForbiddenException();

  // Issue new tokens with different org context
  return this.authService.issueTokens(user, orgId);
}

// Audit all broker actions
@Injectable()
export class BrokerAuditInterceptor {
  intercept(context: ExecutionContext, next: CallHandler) {
    const user = context.switchToHttp().getRequest().user;
    if (user.platformRole === 'broker') {
      this.auditService.log({
        actor: user.id,
        actingAs: 'broker',
        targetOrg: user.orgId,
        action: context.getHandler().name,
        timestamp: new Date(),
      });
    }
    return next.handle();
  }
}
```

## Service-to-Service Authentication

### Internal Service Auth

| Communication | Auth Method | Token Lifetime |
|---------------|-------------|----------------|
| API → Background Worker | Shared secret (internal) | N/A (same service) |
| API → External Service | API key + HMAC | Per request |
| Webhook delivery | HMAC signature | Per request |
| Scheduled jobs | Service account token | 1 hour |

### Service Account Tokens

```typescript
// Service account for internal operations
interface ServiceAccount {
  id: string;
  name: string;  // e.g., 'document-processor', 'scheduler'
  permissions: string[];  // Scoped permissions
  apiKey: string;  // Hashed, rotated quarterly
}

// Service-to-service JWT
const serviceToken = jwt.sign({
  sub: 'service:document-processor',
  type: 'service',
  permissions: ['documents:process', 'products:read'],
  iat: now,
  exp: now + 3600,  // 1 hour
}, SERVICE_SECRET);
```

### Token Exchange (For Delegated Actions)

```typescript
// Exchange user token for scoped service token
@Post('token/exchange')
async exchangeToken(
  @CurrentUser() user: User,
  @Body() dto: TokenExchangeDto
): Promise<{ token: string }> {
  // Validate requested scope is subset of user permissions
  const allowedScopes = this.scopeService.filterScopes(
    dto.requestedScopes,
    user.permissions
  );

  // Issue short-lived scoped token
  return {
    token: this.authService.issueServiceToken({
      subject: user.id,
      delegatedTo: dto.targetService,
      scopes: allowedScopes,
      expiresIn: '5m',  // Short lifetime
    })
  };
}
```

---

## References
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
