# Antigravity Subscription System – Backend Implementation

## Tech Stack

* FastAPI (Python)
* MySQL
* Google Play Developer API
* Google Pub/Sub (RTDN)

---

## 1. Responsibilities of Backend

* Verify Google Play subscription purchases
* Persist subscription state
* Enforce premium access
* React to renewals, cancellations, and expirations
* Act as the single source of truth for entitlements

---

## 2. Database Design

### Subscriptions Table

```sql
CREATE TABLE subscriptions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  product_id VARCHAR(100) NOT NULL,
  purchase_token VARCHAR(255) UNIQUE NOT NULL,
  status ENUM('active','expired','canceled','paused') NOT NULL,
  expiry_time DATETIME NOT NULL,
  auto_renew BOOLEAN NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX idx_user_id (user_id),
  INDEX idx_status (status)
);
```

---

## 3. Google Play API Setup

* Create a Google Cloud service account
* Enable **Google Play Developer API**
* Grant service account access in Play Console
* Store credentials securely (env variables or secret manager)

---

## 4. Subscription Verification Flow

### Endpoint

`POST /subscriptions/verify`

### Request Payload

```json
{
  "product_id": "premium_monthly",
  "purchase_token": "token_from_flutter",
  "package_name": "com.antigravity.app"
}
```

### Verification Logic

* Call Google Play API:

```
GET /androidpublisher/v3/applications/{packageName}/purchases/subscriptions/{productId}/tokens/{token}
```

* Extract:

  * expiryTimeMillis
  * autoRenewing
  * paymentState
* Persist or update subscription record
* Return entitlement status

---

## 5. Real-Time Developer Notifications (RTDN)

### Webhook Endpoint

`POST /subscriptions/google/webhook`

### Supported Events

| Notification Type | Action              |
| ----------------- | ------------------- |
| 1                 | Renew subscription  |
| 3                 | Cancel subscription |
| 12                | Grace period        |
| 13                | Expired             |
| 4                 | On hold             |

### Processing Rules

* Always re-verify token with Google
* Update subscription status and expiry
* Never trust webhook payload blindly

---

## 6. Access Control Enforcement

### Middleware / Dependency

* Validate subscription status
* Ensure `expiry_time > now`
* Deny access if inactive

---

## 7. Restore & Resync Endpoint

`POST /subscriptions/resync`

Used when:

* User reinstalls app
* Webhook missed
* Manual recovery

---

## 8. Scaling & Reliability

* Idempotent verification logic
* Unique constraint on purchase_token
* Graceful handling of duplicate webhooks
* Logging for all subscription events

---

## 9. Security

* No client-side entitlement logic
* No billing handled manually
* Tokens verified server-side only

---

## 10. Outcome

* Backend always reflects Google’s billing state
* Subscription logic is scalable, auditable, and safe
