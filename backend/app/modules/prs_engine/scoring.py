"""PRS Scoring Engine - Pure domain logic."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging


logger = logging.getLogger(__name__)


@dataclass
class PRSScore:
    """PRS scoring result."""
    
    total_score: float
    clinical_risk_score: float
    psychosocial_risk_score: float
    social_determinant_score: float
    category: str  # LOW, MEDIUM, HIGH, CRITICAL
    explanation: str
    recommendations: list[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_score": self.total_score,
            "clinical_risk_score": self.clinical_risk_score,
            "psychosocial_risk_score": self.psychosocial_risk_score,
            "social_determinant_score": self.social_determinant_score,
            "category": self.category,
            "explanation": self.explanation,
            "recommendations": self.recommendations,
        }


class PRSScoringEngine:
    """
    PRS (Patient Risk Score) calculation engine.
    
    Pure domain logic - no FastAPI, no SQLAlchemy.
    Deterministic, versionable, testable in isolation.
    """
    
    # Scoring weights
    CLINICAL_RISK_WEIGHT = 0.40
    PSYCHOSOCIAL_RISK_WEIGHT = 0.35
    SOCIAL_DETERMINANT_WEIGHT = 0.25
    
    # Risk thresholds
    CRITICAL_THRESHOLD = 75.0
    HIGH_THRESHOLD = 60.0
    MEDIUM_THRESHOLD = 40.0
    
    def __init__(self, version: str = "1.0.0"):
        """Initialize scoring engine with version."""
        self.version = version
    
    def calculate_prs(
        self,
        clinical_data: Dict[str, Any],
        psychosocial_data: Dict[str, Any],
        social_determinant_data: Dict[str, Any]
    ) -> PRSScore:
        """
        Calculate comprehensive PRS score.
        
        Args:
            clinical_data: Clinical assessment data
            psychosocial_data: Psychosocial assessment data
            social_determinant_data: Social determinants data
        
        Returns:
            PRSScore with breakdown and recommendations
        """
        # Calculate component scores
        clinical_score = self._calculate_clinical_risk(clinical_data)
        psychosocial_score = self._calculate_psychosocial_risk(psychosocial_data)
        social_score = self._calculate_social_determinant_risk(social_determinant_data)
        
        # Weighted total
        total_score = (
            clinical_score * self.CLINICAL_RISK_WEIGHT +
            psychosocial_score * self.PSYCHOSOCIAL_RISK_WEIGHT +
            social_score * self.SOCIAL_DETERMINANT_WEIGHT
        )
        
        # Clamp score between 0-100
        total_score = max(0, min(100, total_score))
        
        # Determine category
        category = self._determine_category(total_score)
        
        # Generate explanation and recommendations
        explanation = self._generate_explanation(
            total_score,
            clinical_score,
            psychosocial_score,
            social_score
        )
        
        recommendations = self._generate_recommendations(
            category,
            clinical_score,
            psychosocial_score,
            social_score
        )
        
        return PRSScore(
            total_score=round(total_score, 2),
            clinical_risk_score=round(clinical_score, 2),
            psychosocial_risk_score=round(psychosocial_score, 2),
            social_determinant_score=round(social_score, 2),
            category=category,
            explanation=explanation,
            recommendations=recommendations
        )
    
    def _calculate_clinical_risk(self, data: Dict[str, Any]) -> float:
        """Calculate clinical risk component (0-100)."""
        score = 0.0
        
        # Chronic conditions
        chronic_conditions = data.get("chronic_conditions", [])
        score += len(chronic_conditions) * 5  # Each condition adds 5 points
        
        # Medications
        medications = data.get("active_medications", 0)
        score += min(medications * 2, 20)  # Cap at 20 points
        
        # Comorbidities
        if data.get("has_diabetes", False):
            score += 15
        if data.get("has_hypertension", False):
            score += 10
        if data.get("has_copd", False):
            score += 12
        if data.get("has_heart_disease", False):
            score += 18
        
        # Recent hospitalizations
        recent_hospitalizations = data.get("hospitalizations_12mo", 0)
        score += min(recent_hospitalizations * 10, 25)
        
        # Recent ED visits
        ed_visits = data.get("ed_visits_12mo", 0)
        score += min(ed_visits * 5, 20)
        
        # Functional status
        functional_status = data.get("functional_status_score", 0)  # 0-10
        score += functional_status * 3
        
        return min(score, 100)
    
    def _calculate_psychosocial_risk(self, data: Dict[str, Any]) -> float:
        """Calculate psychosocial risk component (0-100)."""
        score = 0.0
        
        # Mental health conditions
        if data.get("has_depression", False):
            score += 15
        if data.get("has_anxiety", False):
            score += 12
        if data.get("has_bipolar", False):
            score += 18
        if data.get("has_schizophrenia", False):
            score += 20
        
        # Substance use
        if data.get("active_substance_use", False):
            score += 25
        if data.get("past_substance_use", False):
            score += 15
        
        # Suicide/self-harm risk
        if data.get("suicide_risk_level") == "high":
            score += 30
        elif data.get("suicide_risk_level") == "moderate":
            score += 20
        
        # Cognitive impairment
        cognitive_score = data.get("cognitive_impairment_score", 0)  # 0-10
        score += cognitive_score * 3
        
        # Social support
        social_support = data.get("social_support_score", 5)  # 0-10, higher is better
        score -= (10 - social_support) * 2  # Lower support increases risk
        
        # Stress level
        stress_level = data.get("stress_level_score", 5)  # 0-10
        score += stress_level * 2
        
        return min(max(score, 0), 100)
    
    def _calculate_social_determinant_risk(self, data: Dict[str, Any]) -> float:
        """Calculate social determinants risk component (0-100)."""
        score = 0.0
        
        # Housing instability
        if data.get("housing_status") == "homeless":
            score += 25
        elif data.get("housing_status") == "unstable":
            score += 15
        
        # Food insecurity
        if data.get("food_insecure", False):
            score += 15
        
        # Financial hardship
        if data.get("financial_hardship_score"):
            score += data["financial_hardship_score"] * 2
        
        # Transportation barriers
        if data.get("transportation_barriers", False):
            score += 10
        
        # Education level (inverse relationship)
        education_years = data.get("education_years", 12)
        if education_years < 8:
            score += 15
        elif education_years < 12:
            score += 10
        
        # Employment status
        if data.get("employment_status") == "unemployed":
            score += 12
        elif data.get("employment_status") == "part_time":
            score += 5
        
        # Healthcare access barriers
        healthcare_barriers = data.get("healthcare_barriers", [])
        score += len(healthcare_barriers) * 5
        
        # Social isolation
        if data.get("social_isolation", False):
            score += 12
        
        # Language/literacy barriers
        if data.get("language_barriers", False):
            score += 10
        
        return min(score, 100)
    
    def _determine_category(self, score: float) -> str:
        """Determine risk category from score."""
        if score >= self.CRITICAL_THRESHOLD:
            return "CRITICAL"
        elif score >= self.HIGH_THRESHOLD:
            return "HIGH"
        elif score >= self.MEDIUM_THRESHOLD:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_explanation(
        self,
        total: float,
        clinical: float,
        psychosocial: float,
        social: float
    ) -> str:
        """Generate explanatory text for the score."""
        components = []
        
        if clinical > 60:
            components.append("significant clinical complexity")
        
        if psychosocial > 60:
            components.append("marked psychosocial challenges")
        
        if social > 60:
            components.append("substantial social determinants barriers")
        
        if not components:
            return f"Overall score of {total:.1f} indicates low to moderate risk"
        
        return (
            f"Patient presents with {', '.join(components)} "
            f"resulting in overall PRS score of {total:.1f}"
        )
    
    def _generate_recommendations(
        self,
        category: str,
        clinical: float,
        psychosocial: float,
        social: float
    ) -> list[str]:
        """Generate actionable recommendations based on scores."""
        recommendations = []
        
        # Category-level recommendations
        if category == "CRITICAL":
            recommendations.append("Urgent comprehensive care plan needed")
            recommendations.append("Consider intensive case management")
            recommendations.append("Assess immediate safety concerns")
        elif category == "HIGH":
            recommendations.append("Develop structured care coordination plan")
            recommendations.append("Assign dedicated care manager")
            recommendations.append("Schedule frequent follow-ups")
        elif category == "MEDIUM":
            recommendations.append("Implement disease/condition management programs")
            recommendations.append("Regular monitoring recommended")
        
        # Component-specific recommendations
        if clinical > 70:
            recommendations.append("Optimize medication management")
            recommendations.append("Consider specialist referrals")
        
        if psychosocial > 70:
            recommendations.append("Integrate behavioral health services")
            recommendations.append("Refer to mental health specialist")
        
        if social > 70:
            recommendations.append("Connect with community resources")
            recommendations.append("Assess for social service needs")
            recommendations.append("Partner with social workers")
        
        return recommendations
