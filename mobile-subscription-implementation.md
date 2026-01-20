# Antigravity Subscription System – Mobile (Flutter)

## Tech Stack

* Flutter
* in_app_purchase package
* Antigravity FastAPI backend

---

## 1. Responsibilities of Mobile App

* Display subscription offerings
* Initiate Google Play subscription purchase
* Send purchase token to backend
* React to entitlement state returned by backend
* Never determine subscription validity locally

---

## 2. Dependencies

```yaml
dependencies:
  in_app_purchase: ^3.1.11
```

---

## 3. Product Configuration

* Product ID: `premium_monthly`
* Type: Subscription
* Store: Google Play only

---

## 4. Fetch Subscription Product

* Query Google Play for product details
* Display pricing and benefits dynamically

---

## 5. Purchase Flow

1. User taps **Subscribe**
2. Google Play purchase UI opens
3. Purchase completes
4. App receives:

   * purchaseToken
   * productId
5. Send purchaseToken to backend

---

## 6. Purchase Listener

* Listen to `purchaseStream`
* On `PurchaseStatus.purchased`:

  * Send token to backend
* On `PurchaseStatus.error`:

  * Show retry or error message

---

## 7. Backend Verification

* Mobile does not unlock features immediately
* Wait for backend confirmation
* Backend returns:

```json
{
  "is_premium": true,
  "expires_at": "2026-02-01T00:00:00Z"
}
```

---

## 8. UI State Management

* Cache entitlement state locally
* Refresh on:

  * App launch
  * App resume
  * Manual refresh

---

## 9. Restore Purchases

* Call `restorePurchases()`
* Forward restored tokens to backend
* Backend reconciles subscription state

---

## 10. Failure & Edge Handling

* Grace period → show warning banner
* Expired → restrict premium features
* Offline → fallback to last known valid state

---

## 11. Security Rules

* Never store entitlement permanently on device
* Never trust purchase without backend verification
* Never mock premium access in production

---

## 12. Outcome

* Mobile app remains thin and secure
* Google handles billing
* Backend controls access
