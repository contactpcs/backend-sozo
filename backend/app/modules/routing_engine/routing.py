"""Routing Engine - Pure domain logic."""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import logging


logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Routing decision result."""
    
    recommended_center_id: str
    alternative_centers: List[str]
    rationale: str
    routing_factors: Dict[str, Any]
    priority_level: str  # URGENT, HIGH, STANDARD, LOW
    confidence_score: float  # 0-100


class RoutingEngine:
    """
    Patient routing and assignment engine.
    
    Pure domain logic - Determines optimal center/clinician assignment
    based on patient characteristics, capacity, and clinical needs.
    """
    
    def __init__(self, version: str = "1.0.0"):
        """Initialize routing engine."""
        self.version = version
    
    def route_patient(
        self,
        patient_data: Dict[str, Any],
        available_centers: List[Dict[str, Any]]
    ) -> RoutingDecision:
        """
        Determine optimal center routing for patient.
        
        Args:
            patient_data: Patient characteristics and clinical data
            available_centers: List of available centers with info
        
        Returns:
            RoutingDecision with recommended center and alternatives
        """
        if not available_centers:
            raise ValueError("No available centers for routing")
        
        # Score each center
        center_scores = []
        for center in available_centers:
            score = self._score_center_fit(patient_data, center)
            center_scores.append({
                "center_id": center["id"],
                "score": score,
                "center": center
            })
        
        # Sort by score
        center_scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Get best match
        best_match = center_scores[0]
        recommended_center_id = best_match["center_id"]
        
        # Get alternative options (next 2 best)
        alternative_centers = [
            cs["center_id"] for cs in center_scores[1:3]
        ]
        
        # Determine priority level
        priority_level = self._determine_priority(patient_data)
        
        # Generate rationale
        rationale = self._generate_routing_rationale(
            patient_data,
            best_match["center"],
            best_match["score"]
        )
        
        # Collect routing factors for transparency
        routing_factors = {
            "clinical_complexity": patient_data.get("prs_score", 0),
            "geographic_proximity": self._calculate_proximity_score(
                patient_data, best_match["center"]
            ),
            "center_capacity": best_match["center"].get("available_slots", 0),
            "specialty_match": self._calculate_specialty_match(
                patient_data, best_match["center"]
            ),
        }
        
        confidence = self._calculate_confidence(center_scores)
        
        return RoutingDecision(
            recommended_center_id=recommended_center_id,
            alternative_centers=alternative_centers,
            rationale=rationale,
            routing_factors=routing_factors,
            priority_level=priority_level,
            confidence_score=round(confidence, 2)
        )
    
    def _score_center_fit(
        self,
        patient_data: Dict[str, Any],
        center: Dict[str, Any]
    ) -> float:
        """Score how well a center fits patient needs."""
        score = 0.0
        
        # Capacity check (critical)
        available_slots = center.get("available_slots", 0)
        if available_slots <= 0:
            return -100  # Unavailable
        
        score += min(available_slots * 5, 15)  # Cap at 15 points
        
        # Geographic proximity (20% weight)
        proximity_score = self._calculate_proximity_score(patient_data, center)
        score += proximity_score * 0.20
        
        # Specialty match (25% weight)
        specialty_match = self._calculate_specialty_match(patient_data, center)
        score += specialty_match * 0.25
        
        # Clinician availability (20% weight)
        clinician_fit = self._calculate_clinician_availability(patient_data, center)
        score += clinician_fit * 0.20
        
        # Center performance (15% weight)
        performance_score = center.get("quality_score", 70)  # Default 70
        score += performance_score * 0.15
        
        # Patient language/cultural match (10% weight)
        cultural_fit = self._calculate_cultural_fit(patient_data, center)
        score += cultural_fit * 0.10
        
        # Insurance acceptance (10% weight)
        insurance_fit = self._calculate_insurance_fit(patient_data, center)
        score += insurance_fit * 0.10
        
        return score
    
    def _calculate_proximity_score(
        self,
        patient_data: Dict[str, Any],
        center: Dict[str, Any]
    ) -> float:
        """Calculate geographic proximity score (0-100)."""
        patient_zip = patient_data.get("zip_code")
        center_zip = center.get("zip_code")
        
        if not patient_zip or not center_zip:
            return 50  # Neutral
        
        # Simple postal code distance heuristic
        # In production, use actual GIS distance calculation
        distance_score = 100 - (abs(int(patient_zip) - int(center_zip)) // 1000)
        
        return max(0, min(distance_score, 100))
    
    def _calculate_specialty_match(
        self,
        patient_data: Dict[str, Any],
        center: Dict[str, Any]
    ) -> float:
        """Calculate specialty/condition match score (0-100)."""
        patient_specialties = set(patient_data.get("clinical_conditions", []))
        center_specialties = set(center.get("specialties", []))
        
        if not patient_specialties or not center_specialties:
            return 50
        
        # Jaccard similarity
        intersection = len(patient_specialties & center_specialties)
        union = len(patient_specialties | center_specialties)
        
        similarity = (intersection / union) * 100 if union > 0 else 0
        
        return similarity
    
    def _calculate_clinician_availability(
        self,
        patient_data: Dict[str, Any],
        center: Dict[str, Any]
    ) -> float:
        """Calculate clinician availability score (0-100)."""
        available_clinicians = center.get("available_clinicians", 0)
        
        if available_clinicians > 5:
            return 100
        elif available_clinicians > 2:
            return 75
        elif available_clinicians > 0:
            return 50
        else:
            return 0
    
    def _calculate_cultural_fit(
        self,
        patient_data: Dict[str, Any],
        center: Dict[str, Any]
    ) -> float:
        """Calculate cultural/language fit (0-100)."""
        patient_language = patient_data.get("preferred_language", "en")
        center_languages = center.get("supported_languages", ["en"])
        
        if patient_language in center_languages:
            return 100
        
        # Check if translation available
        if center.get("has_interpreters", False):
            return 75
        
        return 50
    
    def _calculate_insurance_fit(
        self,
        patient_data: Dict[str, Any],
        center: Dict[str, Any]
    ) -> float:
        """Calculate insurance acceptance (0-100)."""
        patient_insurance = patient_data.get("insurance_plan")
        center_insurances = center.get("accepted_insurance", [])
        
        if patient_insurance in center_insurances:
            return 100
        
        # Check for uninsured acceptance
        if patient_insurance is None and center.get("accepts_uninsured", False):
            return 90
        
        return 25
    
    def _determine_priority(self, patient_data: Dict[str, Any]) -> str:
        """Determine routing priority level."""
        prs_score = patient_data.get("prs_score", 0)
        
        if prs_score >= 75:
            return "URGENT"
        elif prs_score >= 60:
            return "HIGH"
        elif prs_score >= 40:
            return "STANDARD"
        else:
            return "LOW"
    
    def _generate_routing_rationale(
        self,
        patient_data: Dict[str, Any],
        recommended_center: Dict[str, Any],
        score: float
    ) -> str:
        """Generate explanation for routing decision."""
        factors = []
        
        if score > 80:
            factors.append("excellent fit")
        elif score > 60:
            factors.append("good fit")
        
        if patient_data.get("clinical_conditions"):
            factors.append(
                f"specializes in {', '.join(patient_data['clinical_conditions'][:2])}"
            )
        
        if recommended_center.get("has_interpreters"):
            factors.append("language support available")
        
        return (
            f"Recommended center based on {', '.join(factors)}. "
            f"Routing score: {score:.1f}"
        )
    
    def _calculate_confidence(self, center_scores: List[Dict]) -> float:
        """Calculate routing confidence based on score spread."""
        if len(center_scores) < 2:
            return 100
        
        top_score = center_scores[0]["score"]
        second_score = center_scores[1]["score"]
        
        if top_score == 0:
            return 0
        
        # Higher gap = higher confidence
        gap = top_score - second_score
        confidence = min((gap / top_score) * 100, 100)
        
        return confidence
