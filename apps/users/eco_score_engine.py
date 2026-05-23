from django.utils import timezone
from apps.core.constants import ECO_SCORE_MIN, ECO_SCORE_MAX, SCORE_DELTAS, ECO_SCORE_TIERS
from apps.users.models import EcoScoreEvent

def calculate_tier(score):
    """Calculate the tier label based on the score."""
    for tier, data in ECO_SCORE_TIERS.items():
        if data["min"] <= score <= data["max"]:
            return tier
    return "suspended" # Fallback if score is outside range (shouldn't happen)

def apply_score_event(user, event_type, related_object=None, admin=None, override_reason=None):
    """
    Core function to apply an Eco Score event.
    """
    user_type = user.user_type
    
    if user_type not in SCORE_DELTAS or event_type not in SCORE_DELTAS[user_type]:
        # Invalid event type for this user
        return None
        
    delta = SCORE_DELTAS[user_type][event_type]
    
    profile = user.profile
    if not profile:
        return None

    current_score = profile.eco_score
    new_score = max(ECO_SCORE_MIN, min(ECO_SCORE_MAX, current_score + delta))
    
    reason = override_reason or f"Event: {event_type}"
    
    related_type = ""
    related_id = None
    if related_object:
        related_type = related_object.__class__.__name__.lower()
        related_id = related_object.id
        
    # Prevent duplicate events for the same object
    if related_id:
        exists = EcoScoreEvent.objects.filter(
            user=user, 
            event_type=event_type, 
            related_object_id=related_id
        ).exists()
        if exists:
            return None
            
    event = EcoScoreEvent.objects.create(
        user=user,
        event_type=event_type,
        delta=delta,
        score_before=current_score,
        score_after=new_score,
        reason=reason,
        related_object_type=related_type,
        related_object_id=related_id,
        created_by="admin" if admin else "system",
        admin_note=override_reason if admin else ""
    )
    
    # Update profile
    profile.eco_score = new_score
    profile.eco_tier = calculate_tier(new_score)
    profile.eco_score_updated_at = timezone.now()
    profile.save(update_fields=["eco_score", "eco_tier", "eco_score_updated_at", "updated_at"])
    
    return event

def record_pickup_completion(reservation):
    """Record successful pickup for both consumer and merchant."""
    # Consumer always gets standard +5 pickup_completed
    apply_score_event(
        user=reservation.consumer,
        event_type="pickup_completed",
        related_object=reservation
    )
    
    # Merchant
    apply_score_event(
        user=reservation.listing.merchant,
        event_type="pickup_fulfilled",
        related_object=reservation
    )

def record_no_show(reservation):
    """Record no-show penalty."""
    apply_score_event(
        user=reservation.consumer,
        event_type="no_show",
        related_object=reservation
    )
    if reservation.consumer.is_charity:
        apply_score_event(
            user=reservation.consumer,
            event_type="no_show",
            related_object=reservation
        )

def record_cancellation(reservation, cancelled_at):
    """Record cancellation penalty based on timing."""
    # Free cancellation within 15 minutes of reservation
    elapsed_since_reservation = (cancelled_at - reservation.created_at).total_seconds()
    
    if elapsed_since_reservation <= 15 * 60:
        # Free cancellation window (15 mins after reservation)
        return None
    else:
        # After 30 minutes, small penalty
        event_type = "cancellation_late"
        
    return apply_score_event(
        user=reservation.consumer,
        event_type=event_type,
        related_object=reservation
    )
