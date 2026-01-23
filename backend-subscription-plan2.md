# Scalable Subscription System – Implementation Plan

This document is an **actionable implementation plan** for an AI coding agent to build a **Google Play–integrated subscription system** using **FastAPI, SQLModel, and MySQL**, enforcing monthly usage limits for free users and unlimited access for premium users.

---

## 1. Objectives

* Integrate **Google Play Subscriptions** (monthly, auto-renewing)
* Enforce **monthly usage limits** for free users
* Grant **unlimited access** to premium users
* Ensure **server-side verification** and scalability
* Handle renewals, cancellations, and expirations correctly

---

## 2. Feature Rules

### Free Users (per month)

| Feature           | Limit |
| ----------------- | ----- |
| Learning Journeys | 2     |
| Lessons           | 10    |
| Audio Lessons     | 5     |

### Premium Users

* Unlimited access to all features

---

## 3. System Architecture

### Source of Truth

* **Google Play** → Payments & subscription state
* **Backend** → Access control & usage enforcement

### Flow

1. User purchases subscription in Flutter
2. Purchase token sent to FastAPI backend
3. Backend verifies with Google Play Developer API
4. Backend updates subscription & user access
5. Backend enforces limits on every content request

---

## 4. Database Schema (SQLModel)

### 4.1 User Table

```python
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str
    is_premium: bool = False
    premium_expiry: datetime | None = None
```

---

### 4.2 Subscription Table

Stores Google Play subscription state.

```python
class Subscription(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    subscription_id: str  # e.g. premium_monthly
    purchase_token: str
    order_id: str

    status: str  # ACTIVE, EXPIRED, CANCELED, PAUSED
    start_time: datetime
    expiry_time: datetime
    auto_renewing: bool
    last_verified_at: datetime
```

Indexes required:

* purchase_token (unique)
* user_id

---

### 4.3 Monthly Usage Table

Tracks per-subscription monthly usage (NOT directly tied to user).

```python
class MonthlyUsage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    subscription_id: int = Field(foreign_key="subscription.id")
    year: int
    month: int

    learning_journeys_used: int = 0
    lessons_used: int = 0
    audio_lessons_used: int = 0
```

Constraints:

* Unique (subscription_id, year, month)

Rationale:

* Usage resets naturally when subscription changes
* Supports multiple subscriptions per user (future-proof)
* Prevents limit leakage across subscription states

---

## 5. Monthly Reset Strategy

* Do **not** use cron jobs
* On each request:

  * Resolve **active subscription** for user
  * Determine current UTC year/month
  * Fetch MonthlyUsage by (subscription_id, year, month)
  * If missing → create new row

This ensures:

* Correct resets per billing cycle
* Clean separation between free and premium usage
* O(1) scalability

---

## 6. Access Control Logic

### Central Access Check

All content endpoints must use this logic.

```python
def check_access(subscription, usage, feature):
    if subscription.status == "ACTIVE" and subscription.expiry_time > datetime.utcnow():
        return True

    limits = {
        "journey": 2,
        "lesson": 10,
        "audio": 5,
    }

    used = {
        "journey": usage.learning_journeys_used,
        "lesson": usage.lessons_used,
        "audio": usage.audio_lessons_used,
    }

    if used[feature] >= limits[feature]:
        raise HTTPException(
            status_code=403,
            detail="Monthly limit reached. Upgrade to premium."
        )

    return True
```

Increment usage **only after successful access**.

---

## 7. Google Play Subscription Verification

### 7.1 Client → Backend

Client sends:

```json
{
  "purchaseToken": "...",
  "subscriptionId": "premium_monthly"
}
```

---

### 7.2 Backend Verification

Use Google Play Developer API:

* `purchases.subscriptions.get`

Verify:

* paymentState
* expiryTimeMillis
* autoRenewing

---

### 7.3 Backend State Update

If valid:

* Set `user.is_premium = True`
* Set `user.premium_expiry = expiry_time`
* Save subscription record

---

## 8. Real-Time Developer Notifications (RTDN)

### Purpose

Keeps subscription state accurate without client interaction.

### Events Handled

* Renewal
* Cancellation
* Expiration
* Grace period
* Refund

---

### Webhook Endpoint

```
POST /webhooks/google-play
```

On event:

1. Decode notification
2. Fetch subscription via API
3. Update subscription + user access
4. Handle idempotency

---

## 9. API Integration Points

### Required Endpoints

* `POST /subscriptions/verify`
* `POST /webhooks/google-play`
* Feature endpoints (lessons, journeys, audio)

All feature endpoints must:

1. Load user
2. Resolve active subscription (or free-tier virtual subscription)
3. Load or create MonthlyUsage by subscription_id
4. Call access check
5. Increment usage

---

## 10. Security Requirements

* Never trust client subscription state
* Store Google service account securely
* Validate RTDN signatures
* Log all subscription state transitions
* Use UTC timestamps only

---

## 11. Scalability Notes

* MySQL supports millions of subscriptions
* Required indexes:

  * subscription_id
  * (subscription_id, year, month)
  * purchase_token

Future improvem

## 12. Deliverables for AI Agent

The AI agent should implement:

1. SQLModel database models
2. Subscription verification service
3. RTDN webhook handler
4. Monthly usage enforcement logic
5. Feature access middleware
6. Database migrations

---

## 13. Definition of Done

* Free user limits enforced correctly
* Premium users have unlimited access
* Subscription state updates automatically
* System resilient to reinstall, multi-device use
* No client-side trust assumptions

---

**End of implementation plan**
