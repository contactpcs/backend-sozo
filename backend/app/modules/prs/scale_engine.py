"""
PRS Scale Engine — Python port of prs-frontend-app/js/scaleEngine.js.

Handles all 11 scoring methods for 47 clinical assessment scales.
Each scoring handler receives (responses, scale_config) and returns a score dict.
"""

from __future__ import annotations
import math
import re
from typing import Any, Optional

# ─── Scoring Handler Registry ───

_scoring_handlers: dict[str, callable] = {}


def register_handler(scoring_type: str):
    def decorator(fn):
        _scoring_handlers[scoring_type] = fn
        return fn
    return decorator


# ─── Helper Functions ───

def get_option_points(question: dict, value: Any) -> float:
    """Get the point value for a selected option, respecting 'points' overrides."""
    for opt in question.get("options", []):
        if opt.get("value") == value:
            return opt.get("points", opt.get("value", 0))
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def is_scored_in_total(question: dict) -> bool:
    """Check if this question contributes to the total score."""
    if question.get("scoredInTotal") is False:
        return False
    if question.get("includeInScore") is False:
        return False
    return True


def check_conditional(conditional: dict, responses: dict[str, Any]) -> bool:
    """Evaluate a conditional display rule."""
    q_idx = str(conditional.get("questionIndex", ""))
    operator = conditional.get("operator", "")
    target = conditional.get("value")
    actual = responses.get(q_idx)
    if actual is None:
        return False
    ops = {
        ">": lambda a, b: float(a) > float(b),
        ">=": lambda a, b: float(a) >= float(b),
        "<": lambda a, b: float(a) < float(b),
        "<=": lambda a, b: float(a) <= float(b),
        "==": lambda a, b: a == b,
        "===": lambda a, b: a == b,
    }
    return ops.get(operator, lambda a, b: False)(actual, target)


def calculate_max_score(config: dict) -> float:
    """Derive max possible score from scale configuration."""
    if config.get("maxScore") is not None:
        return float(config["maxScore"])
    questions = config.get("questions", [])
    total = 0.0
    for q in questions:
        if not is_scored_in_total(q):
            continue
        opts = q.get("options", [])
        if opts:
            max_val = max(
                opt.get("points", opt.get("value", 0)) for opt in opts
            )
            total += max_val
        elif q.get("max") is not None:
            total += float(q["max"])
    return total


def categorize_value(value: float, ranges: list[dict]) -> int:
    """Categorize a value into a range and return the mapped score."""
    for r in ranges:
        r_min = r.get("min", r.get("minValue", float("-inf")))
        r_max = r.get("max", r.get("maxValue", float("inf")))
        if r_min <= value <= r_max:
            return r.get("score", r.get("value", 0))
    return 0


def calculate_hours_in_bed(bedtime: str, waketime: str) -> float:
    """Parse time strings and calculate hours in bed (handles midnight crossing)."""
    def parse_time(t: str) -> float:
        t = t.strip().upper()
        match = re.match(r"(\d{1,2}):?(\d{2})?\s*(AM|PM)?", t)
        if not match:
            return 0.0
        hours = int(match.group(1))
        minutes = int(match.group(2) or 0)
        period = match.group(3)
        if period == "PM" and hours != 12:
            hours += 12
        elif period == "AM" and hours == 12:
            hours = 0
        return hours + minutes / 60.0

    bed = parse_time(bedtime)
    wake = parse_time(waketime)
    diff = wake - bed
    if diff <= 0:
        diff += 24
    return diff if diff > 0 else 8.0


def get_severity_classification(
    total: float, severity_bands: list[dict]
) -> Optional[dict]:
    """Map a score to its severity band."""
    for band in severity_bands:
        band_min = band.get("min", band.get("minScore", 0))
        band_max = band.get("max", band.get("maxScore", float("inf")))
        if band_min <= total <= band_max:
            return {
                "level": band.get("level", ""),
                "label": band.get("label", ""),
                "description": band.get("description", ""),
                "color": band.get("color"),
                "recommendation": band.get("recommendation"),
            }
    return None


# ─── Scoring Handlers ───

@register_handler("sum")
@register_handler("sum-numeric")
def score_sum(responses: dict, config: dict) -> dict:
    """Simple sum of all scored question values."""
    questions = config.get("questions", [])
    total = 0.0
    question_scores = {}
    for q in questions:
        idx = str(q.get("index", q.get("id", 0)))
        val = responses.get(idx)
        if val is None:
            continue
        if not is_scored_in_total(q):
            question_scores[idx] = {"value": val, "points": 0, "scored": False}
            continue
        conditional = q.get("conditional")
        if conditional and not check_conditional(conditional, responses):
            continue
        points = get_option_points(q, val)
        total += points
        question_scores[idx] = {"value": val, "points": points, "scored": True}

    max_possible = calculate_max_score(config)
    return {
        "total": total,
        "max_possible": max_possible,
        "question_scores": question_scores,
    }


@register_handler("subscale-sum")
@register_handler("subscale-severity")
def score_subscale(responses: dict, config: dict) -> dict:
    """Subscale scoring with per-subscale totals and optional multipliers (DASS-21)."""
    questions = config.get("questions", [])
    subscales = config.get("subscales", [])
    subscale_scores = {}
    grand_total = 0.0
    max_possible = 0.0

    for sub in subscales:
        sub_id = sub.get("id", sub.get("name", ""))
        items = sub.get("items", sub.get("questionIndices", []))
        multiplier = sub.get("multiplier", 1)
        raw_sum = 0.0
        answered = 0

        for item_id in items:
            q = next(
                (qq for qq in questions if qq.get("id") == item_id or qq.get("index") == item_id),
                None
            )
            val = responses.get(str(item_id))
            if val is None:
                idx_key = str(item_id - 1) if isinstance(item_id, int) and item_id > 0 else str(item_id)
                val = responses.get(idx_key)
            if val is None:
                continue
            answered += 1
            if q:
                raw_sum += get_option_points(q, val)
            else:
                raw_sum += float(val) if isinstance(val, (int, float)) else 0

        final_score = raw_sum * multiplier
        sub_max = sub.get("maxScore", len(items) * 3) * multiplier

        sub_severity = None
        sub_severity_bands = config.get("subscaleSeverityBands", {}).get(sub_id)
        if sub_severity_bands:
            sub_severity = get_severity_classification(final_score, sub_severity_bands)

        subscale_scores[sub_id] = {
            "name": sub.get("name", sub_id),
            "raw_sum": raw_sum,
            "multiplier": multiplier,
            "score": final_score,
            "max_score": sub_max,
            "items_answered": answered,
            "severity": sub_severity,
        }
        grand_total += final_score
        max_possible += sub_max

    has_subscale_severity = bool(config.get("subscaleSeverityBands"))
    return {
        "total": grand_total,
        "max_possible": max_possible,
        "subscale_scores": subscale_scores,
        "has_subscale_severity": has_subscale_severity,
    }


@register_handler("weighted-binary")
def score_weighted_binary(responses: dict, config: dict) -> dict:
    """Binary scoring with point weights and cutoff (LANSS, DN4)."""
    questions = config.get("questions", [])
    total = 0.0
    question_scores = {}

    for q in questions:
        idx = str(q.get("index", 0))
        val = responses.get(idx)
        if val is None:
            continue
        points = get_option_points(q, val)
        total += points
        question_scores[idx] = {"value": val, "points": points}

    max_possible = calculate_max_score(config)
    cutoff = config.get("cutoff", config.get("cutoffScore"))
    is_positive = total >= cutoff if cutoff is not None else None

    return {
        "total": total,
        "max_possible": max_possible,
        "question_scores": question_scores,
        "cutoff": cutoff,
        "is_positive": is_positive,
    }


@register_handler("weighted-domain-sum")
def score_weighted_domain(responses: dict, config: dict) -> dict:
    """Domain-based scoring with per-domain multipliers (COMPASS-31)."""
    questions = config.get("questions", [])
    domains = config.get("domains", {})
    domain_scores = {}
    grand_total = 0.0
    max_possible = 0.0

    for domain_id, domain_def in domains.items():
        items = domain_def.get("items", domain_def.get("questionIndices", []))
        multiplier = domain_def.get("multiplier", domain_def.get("weight", 1))
        raw_sum = 0.0

        for item_idx in items:
            val = responses.get(str(item_idx))
            if val is None:
                continue
            q = next((qq for qq in questions if qq.get("index") == item_idx), None)
            if q:
                conditional = q.get("conditional")
                if conditional and not check_conditional(conditional, responses):
                    continue
                raw_sum += get_option_points(q, val)
            else:
                raw_sum += float(val) if isinstance(val, (int, float)) else 0

        weighted = raw_sum * multiplier
        domain_max = domain_def.get("maxWeighted", domain_def.get("maxScore", len(items) * 3 * multiplier))

        domain_scores[domain_id] = {
            "name": domain_def.get("name", domain_id),
            "raw_sum": raw_sum,
            "multiplier": multiplier,
            "score": weighted,
            "max_score": domain_max,
        }
        grand_total += weighted
        max_possible += domain_max

    return {
        "total": grand_total,
        "max_possible": max_possible,
        "domain_scores": domain_scores,
    }


@register_handler("fiqr-weighted")
def score_fiqr(responses: dict, config: dict) -> dict:
    """FIQR scoring: Function(÷3) + Overall(÷1) + Symptoms(÷2) = 0-100."""
    questions = config.get("questions", [])
    domains = config.get("domains", {})

    divisor_map = {
        "function": 3.0,
        "overall": 1.0,
        "symptoms": 2.0,
    }
    max_map = {
        "function": 30.0,
        "overall": 20.0,
        "symptoms": 50.0,
    }

    domain_scores = {}
    grand_total = 0.0

    for domain_id, domain_def in domains.items():
        items = domain_def.get("items", domain_def.get("questionIndices", []))
        divisor = domain_def.get("divisor", divisor_map.get(domain_id, 1))
        raw_sum = 0.0

        for item_idx in items:
            val = responses.get(str(item_idx))
            if val is not None:
                q = next((qq for qq in questions if qq.get("index") == item_idx), None)
                raw_sum += get_option_points(q, val) if q else float(val)

        weighted = raw_sum / divisor
        domain_max = domain_def.get("maxWeighted", max_map.get(domain_id, 30))

        domain_scores[domain_id] = {
            "name": domain_def.get("name", domain_id),
            "raw_sum": raw_sum,
            "divisor": divisor,
            "score": round(weighted, 2),
            "max_score": domain_max,
        }
        grand_total += weighted

    return {
        "total": round(grand_total, 2),
        "max_possible": 100.0,
        "domain_scores": domain_scores,
    }


@register_handler("component-sum")
def score_component(responses: dict, config: dict) -> dict:
    """Component-based scoring with complex sub-rules (PSQI)."""
    components = config.get("components", [])
    questions = config.get("questions", [])
    component_scores = {}
    grand_total = 0.0

    for comp in components:
        comp_id = comp.get("id", "")
        q_indices = comp.get("questionIndices", comp.get("items", []))
        scoring_rules = comp.get("scoringRules", {})
        rule_type = scoring_rules.get("type", "sum")

        if rule_type == "categorize":
            idx = q_indices[0] if q_indices else None
            val = responses.get(str(idx)) if idx is not None else None
            if val is not None:
                comp_score = categorize_value(float(val), scoring_rules.get("ranges", []))
            else:
                comp_score = 0

        elif rule_type == "sum-then-categorize":
            raw_sum = 0.0
            for qi in q_indices:
                val = responses.get(str(qi))
                if val is not None:
                    raw_sum += float(val)
            comp_score = categorize_value(raw_sum, scoring_rules.get("ranges", []))

        elif rule_type == "efficiency-calculation":
            bedtime_idx = scoring_rules.get("bedtimeQuestion")
            waketime_idx = scoring_rules.get("waketimeQuestion")
            sleep_duration_idx = scoring_rules.get("sleepDurationQuestion")

            bedtime = responses.get(str(bedtime_idx), "11:00 PM")
            waketime = responses.get(str(waketime_idx), "7:00 AM")
            hours_in_bed = calculate_hours_in_bed(str(bedtime), str(waketime))

            sleep_hours = responses.get(str(sleep_duration_idx))
            if sleep_hours is not None:
                sleep_hours = float(sleep_hours)
            else:
                sleep_hours = 7.0

            efficiency = (sleep_hours / hours_in_bed * 100) if hours_in_bed > 0 else 0
            comp_score = categorize_value(efficiency, scoring_rules.get("ranges", []))

        else:
            raw_sum = 0.0
            for qi in q_indices:
                val = responses.get(str(qi))
                if val is not None:
                    q = next((qq for qq in questions if qq.get("index") == qi), None)
                    raw_sum += get_option_points(q, val) if q else float(val)
            comp_score = min(raw_sum, comp.get("maxScore", 3))

        max_comp = comp.get("maxScore", 3)
        component_scores[comp_id] = {
            "name": comp.get("name", comp_id),
            "score": comp_score,
            "max_score": max_comp,
        }
        grand_total += comp_score

    max_possible = sum(c.get("maxScore", 3) for c in components)
    return {
        "total": grand_total,
        "max_possible": max_possible,
        "component_scores": component_scores,
        "component_count": len(components),
    }


@register_handler("profile-and-vas")
def score_profile_vas(responses: dict, config: dict) -> dict:
    """Health state profile + VAS score (EQ-5D-5L)."""
    questions = config.get("questions", [])
    profile_parts = []
    dimension_scores = {}
    vas_score = None

    for q in questions:
        idx = str(q.get("index", 0))
        val = responses.get(idx)
        q_type = q.get("type", "")

        if q_type in ("vas", "nrs") or q.get("isVAS"):
            vas_score = float(val) if val is not None else None
            continue

        if val is not None:
            profile_parts.append(str(int(val) if isinstance(val, (int, float)) else val))
            dim_name = q.get("dimension", q.get("label", f"D{len(profile_parts)}"))
            dimension_scores[dim_name] = {
                "value": val,
                "max": len(q.get("options", [])),
            }
        else:
            profile_parts.append("0")

    health_state = "".join(profile_parts)
    total = sum(int(p) for p in profile_parts if p.isdigit())
    max_possible = len(profile_parts) * 5

    return {
        "total": total,
        "max_possible": max_possible,
        "health_state_profile": health_state,
        "dimension_scores": dimension_scores,
        "vas_score": vas_score,
        "is_profile_based": True,
    }


@register_handler("reverse-scored")
def score_reverse(responses: dict, config: dict) -> dict:
    """Reverse scoring for designated items (RAADS-14)."""
    questions = config.get("questions", [])
    reverse_items = set(config.get("reverseItems", []))
    max_item_score = config.get("maxItemScore", 3)
    total = 0.0
    question_scores = {}

    for q in questions:
        idx = q.get("index", 0)
        val = responses.get(str(idx))
        if val is None:
            continue
        if not is_scored_in_total(q):
            continue

        points = get_option_points(q, val)
        if idx in reverse_items:
            points = max_item_score - points

        total += points
        question_scores[str(idx)] = {
            "value": val,
            "points": points,
            "reversed": idx in reverse_items,
        }

    max_possible = calculate_max_score(config)
    return {
        "total": total,
        "max_possible": max_possible,
        "question_scores": question_scores,
        "reverse_items": list(reverse_items),
    }


@register_handler("clinician")
def score_clinician(responses: dict, config: dict) -> dict:
    """Clinician-rated scale scoring (EDSS, MADRS, MAS, MRC, KPS)."""
    questions = config.get("questions", [])
    total = 0.0
    question_scores = {}

    for q in questions:
        idx = str(q.get("index", 0))
        val = responses.get(idx)
        if val is None:
            continue
        points = get_option_points(q, val)
        total += points
        question_scores[idx] = {"value": val, "points": points}

    max_possible = calculate_max_score(config)
    return {
        "total": total,
        "max_possible": max_possible,
        "question_scores": question_scores,
        "is_clinician": True,
    }


@register_handler("average")
def score_average(responses: dict, config: dict) -> dict:
    """Mean/average scoring."""
    questions = config.get("questions", [])
    values = []
    for q in questions:
        idx = str(q.get("index", 0))
        val = responses.get(idx)
        if val is not None and is_scored_in_total(q):
            values.append(get_option_points(q, val))

    count = len(values)
    total_sum = sum(values)
    avg = total_sum / count if count > 0 else 0.0
    max_possible = calculate_max_score(config)

    return {
        "total": round(avg, 2),
        "sum": total_sum,
        "count": count,
        "max_possible": max_possible,
    }


# ─── Risk Flag Detection ───

def check_risk_flags(
    scale_id: str, responses: dict, config: dict
) -> list[dict]:
    """Evaluate risk rules for a scale and return triggered flags."""
    rules = config.get("riskRules", [])
    flags = []

    for rule in rules:
        triggered = False

        # Question-level rule
        q_idx = rule.get("questionIndex")
        if q_idx is not None:
            val = responses.get(str(q_idx))
            if val is not None:
                threshold = rule.get("threshold", rule.get("value", 0))
                operator = rule.get("operator", ">=")
                # Also handle "condition" string like "value >= 2"
                condition_str = rule.get("condition")
                if condition_str:
                    try:
                        triggered = eval(
                            condition_str.replace("value", str(float(val))),
                            {"__builtins__": {}},
                        )
                    except Exception:
                        triggered = False
                else:
                    ops = {
                        ">=": lambda a, b: a >= b,
                        ">": lambda a, b: a > b,
                        "<=": lambda a, b: a <= b,
                        "<": lambda a, b: a < b,
                        "==": lambda a, b: a == b,
                    }
                    triggered = ops.get(operator, lambda a, b: False)(float(val), float(threshold))

        # Subscale-level rule
        subscale = rule.get("subscale")
        if subscale and not triggered:
            condition_str = rule.get("condition", "")
            # This will be evaluated after scoring with subscale scores
            # For now, flag for post-processing
            pass

        if triggered:
            flags.append({
                "scale_id": scale_id,
                "alert_type": rule.get("type", rule.get("id", "risk_flag")),
                "severity": rule.get("severity", "moderate"),
                "message": rule.get("message", "Risk flag triggered"),
                "recommendation": rule.get("recommendation"),
                "source_question_index": q_idx,
                "source_value": float(responses.get(str(q_idx), 0)) if q_idx is not None else None,
            })

    return flags


def check_subscale_risk_flags(
    scale_id: str, subscale_scores: dict, config: dict
) -> list[dict]:
    """Check risk rules that depend on subscale scores (post-scoring)."""
    rules = config.get("riskRules", [])
    flags = []

    for rule in rules:
        subscale = rule.get("subscale")
        if not subscale:
            continue

        sub_data = subscale_scores.get(subscale, {})
        score = sub_data.get("score", 0)
        condition_str = rule.get("condition", "")

        try:
            triggered = eval(
                condition_str.replace("score", str(float(score))),
                {"__builtins__": {}},
            )
        except Exception:
            triggered = False

        if triggered:
            flags.append({
                "scale_id": scale_id,
                "alert_type": rule.get("type", rule.get("id", "risk_flag")),
                "severity": rule.get("severity", "moderate"),
                "message": rule.get("message", "Risk flag triggered"),
                "recommendation": rule.get("recommendation"),
                "source_question_index": None,
                "source_value": score,
            })

    return flags


# ─── Main Scoring Function ───

def calculate_score(
    scale_id: str,
    responses: dict[str, Any],
    scale_config: dict,
) -> dict:
    """
    Main scoring entry point.
    Returns complete score data including severity and risk flags.
    """
    scoring_type = scale_config.get("scoringType", scale_config.get("scoringMethod", "sum"))
    handler = _scoring_handlers.get(scoring_type, score_sum)

    score_data = handler(responses, scale_config)
    score_data["scale_id"] = scale_id
    score_data["scoring_type"] = scoring_type

    # Percentage
    max_possible = score_data.get("max_possible", 0)
    total = score_data.get("total", 0)
    if max_possible > 0:
        score_data["percentage"] = round((total / max_possible) * 100, 1)
    else:
        score_data["percentage"] = 0.0

    # Severity classification
    severity_bands = scale_config.get("severityBands", [])
    if severity_bands:
        severity = get_severity_classification(total, severity_bands)
        score_data["severity"] = severity
    else:
        score_data["severity"] = None

    # Risk flags (question-level)
    flags = check_risk_flags(scale_id, responses, scale_config)

    # Risk flags (subscale-level)
    subscale_scores = score_data.get("subscale_scores")
    if subscale_scores:
        flags.extend(
            check_subscale_risk_flags(scale_id, subscale_scores, scale_config)
        )

    score_data["risk_flags"] = flags

    return score_data


def validate_responses(responses: dict, scale_config: dict) -> dict:
    """Check all required questions are answered."""
    questions = scale_config.get("questions", [])
    missing = []

    for q in questions:
        if not q.get("required", True):
            continue
        idx = str(q.get("index", q.get("id", 0)))
        conditional = q.get("conditional")
        if conditional and not check_conditional(conditional, responses):
            continue
        if responses.get(idx) is None:
            missing.append(idx)

    return {"is_valid": len(missing) == 0, "missing_questions": missing}


def get_scoring_types() -> list[str]:
    """Return all registered scoring types."""
    return list(_scoring_handlers.keys())
