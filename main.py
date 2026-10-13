
import os
import hmac
from collections import defaultdict
from math import fsum

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Analytics API")

# Allow the exam page to call our API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyticsEvent(BaseModel):
    user: str
    amount: float
    ts: int | float


class AnalyticsRequest(BaseModel):
    events: list[AnalyticsEvent]


@app.get("/")
def home():
    return {"status": "ok", "service": "analytics-api"}


@app.post("/analytics")
def analytics(
    payload: AnalyticsRequest,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
):
    # 1. Check API key.
    expected_key = os.getenv("ANALYTICS_API_KEY", "")

    if (
        not expected_key
        or not x_api_key
        or not hmac.compare_digest(x_api_key, expected_key)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    # 2. Read the email associated with your exam login.
    email = os.getenv("STUDENT_EMAIL", "").strip()

    if not email:
        raise HTTPException(
            status_code=500,
            detail="Student email is not configured",
        )

    # 3. Keep positive amounts grouped by user.
    amounts_by_user = defaultdict(list)

    for event in payload.events:
        # Include every user, even if their amounts are negative.
        amounts_by_user[event.user]

        if event.amount > 0:
            amounts_by_user[event.user].append(event.amount)

    user_totals = {
        user: fsum(amounts)
        for user, amounts in amounts_by_user.items()
    }

    # 4. Sum positive event amounts only.
    revenue = fsum(
        event.amount
        for event in payload.events
        if event.amount > 0
    )

    # 5. Find the user with the highest positive-amount total.
    top_user = (
        max(user_totals, key=user_totals.get)
        if user_totals
        else ""
    )

    return {
        "email": email,
        "total_events": len(payload.events),
        "unique_users": len(amounts_by_user),
        "revenue": revenue,
        "top_user": top_user,
    }
