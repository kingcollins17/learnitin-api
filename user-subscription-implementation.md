# Antigravity Subscription System – Google Play Console Setup

## 1. Subscription Product Creation

* Navigate to **Monetize → Products → Subscriptions**
* Create subscription:

  * Product ID: `premium_monthly`
  * Billing period: Monthly
  * Base plan enabled

---

## 2. Pricing & Availability

* Set pricing per country
* Enable all target regions
* Optional: introductory pricing or free trial

---

## 3. Grace Period & Account Hold

Recommended:

* Grace period: Enabled
* Account hold: Enabled
* Retry period: Enabled

These reduce involuntary churn.

---

## 4. Licensing & Test Accounts

* Add license testers
* Use internal testing track
* Test:

  * Successful renewal
  * Failed payment
  * Cancellation
  * Expiration

---

## 5. Real-Time Developer Notifications (RTDN)

### Setup Steps

1. Create Google Cloud Pub/Sub topic
2. Link topic in Play Console
3. Grant Play Console publish permission
4. Forward Pub/Sub messages to backend webhook

---

## 6. Service Account Access

* Grant service account:

  * View financial data
  * Manage subscriptions
* Required for Google Play API verification

---

## 7. App Review Compliance

* Clearly describe subscription benefits
* Show pricing and renewal terms
* Provide in-app access to:

  * Manage subscription
  * Cancel subscription

---

## 8. Pre-Launch Checklist

* Subscription active
* Backend verification live
* Webhooks tested
* Restore flow validated

---

## 9. Outcome

* Google Play handles billing lifecycle
* Antigravity backend stays in sync automatically
* Subscription system passes Play review smoothly
