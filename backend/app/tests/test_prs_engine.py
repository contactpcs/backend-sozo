"""Test PRS scoring engine."""
import pytest
from app.modules.prs_engine.scoring import PRSScoringEngine


@pytest.fixture
def scoring_engine():
    """Create PRS scoring engine."""
    return PRSScoringEngine()


@pytest.mark.asyncio
async def test_prs_low_risk(scoring_engine):
    """Test low risk PRS calculation."""
    clinical = {
        "chronic_conditions": [],
        "active_medications": 0,
        "has_diabetes": False,
        "functional_status_score": 0,
        "hospitalizations_12mo": 0,
        "ed_visits_12mo": 0,
    }
    
    psychosocial = {
        "has_depression": False,
        "has_anxiety": False,
        "active_substance_use": False,
        "cognitive_impairment_score": 0,
        "social_support_score": 8,
        "stress_level_score": 2,
    }
    
    social = {
        "housing_status": "stable",
        "food_insecure": False,
        "employment_status": "employed",
        "education_years": 16,
    }
    
    result = scoring_engine.calculate_prs(clinical, psychosocial, social)
    
    assert result.total_score < 40
    assert result.category == "LOW"


@pytest.mark.asyncio
async def test_prs_critical_risk(scoring_engine):
    """Test critical risk PRS calculation."""
    clinical = {
        "chronic_conditions": ["diabetes", "hypertension", "copd"],
        "active_medications": 10,
        "has_diabetes": True,
        "has_hypertension": True,
        "has_copd": True,
        "has_heart_disease": True,
        "functional_status_score": 10,
        "hospitalizations_12mo": 5,
        "ed_visits_12mo": 8,
    }
    
    psychosocial = {
        "has_depression": True,
        "has_anxiety": True,
        "active_substance_use": True,
        "suicide_risk_level": "high",
        "cognitive_impairment_score": 8,
        "social_support_score": 2,
        "stress_level_score": 9,
    }
    
    social = {
        "housing_status": "homeless",
        "food_insecure": True,
        "employment_status": "unemployed",
        "education_years": 8,
    }
    
    result = scoring_engine.calculate_prs(clinical, psychosocial, social)
    
    assert result.total_score > 75
    assert result.category == "CRITICAL"
