"""
Advanced Negotiation Analysis and Feedback Engine
Integrates with Django views to provide real-time negotiation analysis
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .negotiation_analyzer import NegotiationAnalyzer, NegotiationAnalysis, NegotiationStrategy, CommunicationTone

@dataclass
class ScenarioContext:
    scenario_id: str
    scenario_type: str
    difficulty_level: str
    stage: int
    employer_constraints: List[str]
    market_context: Dict[str, Any]
    expected_salary_range: Dict[str, float]

@dataclass
class FeedbackResponse:
    analysis: NegotiationAnalysis
    contextual_feedback: str
    employer_response: str
    next_stage_available: bool
    improvement_tips: List[str]
    scenario_progress: Dict[str, Any]

class NegotiationEngine:
    def __init__(self):
        self.analyzer = NegotiationAnalyzer()
        self.scenario_contexts = self._load_scenario_contexts()
        self.employer_response_templates = self._load_response_templates()
        
    def _load_scenario_contexts(self) -> Dict[str, ScenarioContext]:
        """Load predefined scenario contexts with market data"""
        return {
            'tech-startup': ScenarioContext(
                scenario_id='tech-startup',
                scenario_type='startup',
                difficulty_level='intermediate',
                stage=1,
                employer_constraints=['budget_limited', 'equity_heavy', 'growth_focused'],
                market_context={
                    'industry': 'technology',
                    'location': 'kathmandu',
                    'company_size': 'startup',
                    'growth_stage': 'series_a'
                },
                expected_salary_range={'min': 80000, 'max': 120000, 'currency': 'NPR'}
            ),
            'corporate-offer': ScenarioContext(
                scenario_id='corporate-offer',
                scenario_type='corporate',
                difficulty_level='beginner',
                stage=1,
                employer_constraints=['structured_bands', 'benefits_rich', 'process_oriented'],
                market_context={
                    'industry': 'corporate',
                    'location': 'kathmandu',
                    'company_size': 'large',
                    'stability': 'high'
                },
                expected_salary_range={'min': 100000, 'max': 150000, 'currency': 'NPR'}
            ),
            'remote-international': ScenarioContext(
                scenario_id='remote-international',
                scenario_type='remote',
                difficulty_level='advanced',
                stage=1,
                employer_constraints=['cost_arbitrage', 'performance_based', 'timezone_overlap'],
                market_context={
                    'industry': 'technology',
                    'location': 'remote',
                    'company_size': 'medium',
                    'market': 'international'
                },
                expected_salary_range={'min': 2500, 'max': 4000, 'currency': 'USD'}
            ),
            'low-offer': ScenarioContext(
                scenario_id='low-offer',
                scenario_type='challenging',
                difficulty_level='advanced',
                stage=1,
                employer_constraints=['tight_budget', 'learning_focused', 'growth_potential'],
                market_context={
                    'industry': 'general',
                    'location': 'kathmandu',
                    'company_size': 'small',
                    'budget_constraints': 'high'
                },
                expected_salary_range={'min': 60000, 'max': 90000, 'currency': 'NPR'}
            ),
            'budget-constraints': ScenarioContext(
                scenario_id='budget-constraints',
                scenario_type='constraint_based',
                difficulty_level='intermediate',
                stage=1,
                employer_constraints=['budget_tight', 'creative_compensation', 'future_reviews'],
                market_context={
                    'industry': 'general',
                    'location': 'kathmandu',
                    'company_size': 'medium',
                    'flexibility': 'moderate'
                },
                expected_salary_range={'min': 90000, 'max': 130000, 'currency': 'NPR'}
            ),
            'multiple-offers': ScenarioContext(
                scenario_id='multiple-offers',
                scenario_type='competitive',
                difficulty_level='expert',
                stage=1,
                employer_constraints=['competitive_market', 'retention_focused', 'value_based'],
                market_context={
                    'industry': 'technology',
                    'location': 'kathmandu',
                    'company_size': 'large',
                    'competition': 'high'
                },
                expected_salary_range={'min': 120000, 'max': 180000, 'currency': 'NPR'}
            )
        }
    
    def _load_response_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """Load employer response templates based on user strategies"""
        return {
            'positive_responses': {
                'market_research': [
                    "I appreciate that you've done your research. Let me see what flexibility we have within our budget constraints.",
                    "Your market research is thorough. We value candidates who come prepared with data.",
                    "Those numbers align with what we've seen in the market. Let's discuss how we can work within that range."
                ],
                'value_proposition': [
                    "Your experience and skills are exactly what we're looking for. Let me discuss this with the team.",
                    "I can see the value you'd bring to our organization. We should be able to find a way to make this work.",
                    "Your track record speaks for itself. We're definitely interested in moving forward."
                ],
                'collaborative': [
                    "I appreciate your collaborative approach. Let's work together to find a solution that works for both parties.",
                    "That's exactly the kind of partnership mindset we value. Let's explore our options.",
                    "Your willingness to work with us is refreshing. We should be able to find common ground."
                ]
            },
            'neutral_responses': {
                'default': [
                    "Thank you for sharing your thoughts. Let me take this back to the team and see what we can do.",
                    "I understand your position. We'll need to review our options and get back to you.",
                    "That's helpful feedback. We'll consider this as we finalize our offer."
                ],
                'budget_constraints': [
                    "While we have budget constraints, we're committed to finding the right person for this role.",
                    "Our budget is limited, but we're open to creative compensation structures.",
                    "We may not be able to meet that exact figure, but let's discuss other ways to bridge the gap."
                ]
            },
            'challenging_responses': {
                'aggressive_approach': [
                    "I understand you have strong feelings about this, but we need to work within our established parameters.",
                    "We value your enthusiasm, but we also need to be realistic about our constraints.",
                    "Let's take a step back and focus on finding a mutually beneficial solution."
                ],
                'unrealistic_expectations': [
                    "That's significantly above our budget range. Let's discuss what's realistic for this position.",
                    "We need to align expectations with market realities and our company's compensation structure.",
                    "While we appreciate your ambition, we need to find a number that works for both parties."
                ]
            }
        }

    def analyze_negotiation_response(self, user_response: str, scenario_id: str, 
                                   stage: int = 1, context: Dict[str, Any] = None) -> FeedbackResponse:
        """
        Comprehensive analysis of user negotiation response with contextual feedback
        """
        # Get scenario context
        scenario_context = self.scenario_contexts.get(scenario_id)
        if not scenario_context:
            raise ValueError(f"Unknown scenario: {scenario_id}")
        
        # Perform core analysis
        analysis = self.analyzer.analyze_response(user_response, context)
        
        # Generate contextual feedback
        contextual_feedback = self._generate_contextual_feedback(
            analysis, scenario_context, user_response
        )
        
        # Generate employer response
        employer_response = self._generate_employer_response(
            analysis, scenario_context, user_response
        )
        
        # Determine if next stage is available
        next_stage_available = self._should_advance_stage(analysis, scenario_context)
        
        # Generate improvement tips
        improvement_tips = self._generate_improvement_tips(
            analysis, scenario_context, user_response
        )
        
        # Calculate scenario progress
        scenario_progress = self._calculate_scenario_progress(
            analysis, scenario_context, stage
        )
        
        return FeedbackResponse(
            analysis=analysis,
            contextual_feedback=contextual_feedback,
            employer_response=employer_response,
            next_stage_available=next_stage_available,
            improvement_tips=improvement_tips,
            scenario_progress=scenario_progress
        )

    def _generate_contextual_feedback(self, analysis: NegotiationAnalysis, 
                                    scenario_context: ScenarioContext, 
                                    user_response: str) -> str:
        """Generate feedback specific to the scenario context"""
        feedback_parts = []
        
        # Scenario-specific feedback
        if scenario_context.scenario_type == 'startup':
            if NegotiationStrategy.MARKET_RESEARCH in analysis.strategies_detected:
                feedback_parts.append("✅ Great use of market research - startups respect data-driven candidates.")
            if NegotiationStrategy.ALTERNATIVE_COMPENSATION in analysis.strategies_detected:
                feedback_parts.append("✅ Excellent focus on equity and benefits - perfect for startup negotiations.")
            else:
                feedback_parts.append("💡 Consider discussing equity options - startups often compensate with ownership.")
        
        elif scenario_context.scenario_type == 'corporate':
            if analysis.professionalism_score > 80:
                feedback_parts.append("✅ Professional tone is perfect for corporate environments.")
            if NegotiationStrategy.VALUE_PROPOSITION in analysis.strategies_detected:
                feedback_parts.append("✅ Strong value proposition - corporations value proven results.")
        
        elif scenario_context.scenario_type == 'remote':
            if 'timezone' in user_response.lower() or 'communication' in user_response.lower():
                feedback_parts.append("✅ Addressing remote work considerations shows professionalism.")
            else:
                feedback_parts.append("💡 Consider mentioning timezone flexibility and communication skills.")
        
        # Difficulty-specific feedback
        if scenario_context.difficulty_level == 'expert' and len(analysis.strategies_detected) < 3:
            feedback_parts.append("⚠️ Expert scenarios require multiple negotiation strategies.")
        
        # Salary range analysis
        salary_mentioned = self._extract_salary_from_response(user_response)
        if salary_mentioned:
            range_feedback = self._analyze_salary_positioning(
                salary_mentioned, scenario_context.expected_salary_range
            )
            feedback_parts.append(range_feedback)
        
        return " ".join(feedback_parts) if feedback_parts else "Keep practicing to improve your negotiation skills!"

    def _generate_employer_response(self, analysis: NegotiationAnalysis,
                                  scenario_context: ScenarioContext,
                                  user_response: str) -> str:
        """Generate realistic employer response based on user's approach"""
        
        # Determine response category based on analysis
        if analysis.overall_score >= 80 and analysis.professionalism_score >= 75:
            response_category = 'positive_responses'
        elif analysis.overall_score < 50 or analysis.professionalism_score < 60:
            response_category = 'challenging_responses'
        else:
            response_category = 'neutral_responses'
        
        # Select specific response type
        if NegotiationStrategy.MARKET_RESEARCH in analysis.strategies_detected:
            response_type = 'market_research'
        elif NegotiationStrategy.VALUE_PROPOSITION in analysis.strategies_detected:
            response_type = 'value_proposition'
        elif NegotiationStrategy.COLLABORATIVE in analysis.strategies_detected:
            response_type = 'collaborative'
        elif analysis.communication_tone == CommunicationTone.AGGRESSIVE:
            response_type = 'aggressive_approach'
        elif self._is_salary_unrealistic(user_response, scenario_context):
            response_type = 'unrealistic_expectations'
        else:
            response_type = 'default'
        
        # Get response templates
        templates = self.employer_response_templates.get(response_category, {})
        responses = templates.get(response_type, templates.get('default', [
            "Thank you for your response. Let me discuss this with the team."
        ]))
        
        # Select response based on scenario constraints
        import random
        selected_response = random.choice(responses)
        
        # Add scenario-specific context
        if scenario_context.scenario_type == 'startup' and 'budget' in selected_response:
            selected_response += " As a startup, we're also excited to offer equity participation in our growth."
        elif scenario_context.scenario_type == 'corporate' and 'team' in selected_response:
            selected_response += " We have established processes for salary reviews and career advancement."
        
        return selected_response

    def _should_advance_stage(self, analysis: NegotiationAnalysis,
                            scenario_context: ScenarioContext) -> bool:
        """Determine if user should advance to next negotiation stage"""
        # Minimum requirements for stage advancement
        min_score_threshold = 60
        min_strategies = 1
        
        has_min_score = analysis.overall_score >= min_score_threshold
        has_strategies = len(analysis.strategies_detected) >= min_strategies
        is_professional = analysis.professionalism_score >= 70
        
        return has_min_score and has_strategies and is_professional

    def _generate_improvement_tips(self, analysis: NegotiationAnalysis,
                                 scenario_context: ScenarioContext,
                                 user_response: str) -> List[str]:
        """Generate specific improvement tips based on analysis and context"""
        tips = []
        
        # Strategy-specific tips
        if NegotiationStrategy.MARKET_RESEARCH not in analysis.strategies_detected:
            tips.append(f"Research salary ranges for {scenario_context.market_context.get('industry', 'your industry')} positions in {scenario_context.market_context.get('location', 'your area')}")
        
        if NegotiationStrategy.VALUE_PROPOSITION not in analysis.strategies_detected:
            tips.append("Highlight specific achievements and skills that justify your salary request")
        
        # Scenario-specific tips
        if scenario_context.scenario_type == 'startup':
            if NegotiationStrategy.ALTERNATIVE_COMPENSATION not in analysis.strategies_detected:
                tips.append("Discuss equity options and growth opportunities in startup negotiations")
        
        elif scenario_context.scenario_type == 'remote':
            if 'timezone' not in user_response.lower():
                tips.append("Mention your timezone flexibility and communication skills for remote positions")
        
        # Communication tips
        if analysis.confidence_level < 70:
            tips.append("Use more confident language and avoid uncertain phrases like 'maybe' or 'I think'")
        
        if analysis.professionalism_score < 75:
            tips.append("Maintain a more professional tone with phrases like 'I appreciate' and 'thank you'")
        
        # Tactical tips
        if not re.search(r'\?', user_response):
            tips.append("Ask clarifying questions about benefits, growth opportunities, or timeline")
        
        return tips[:5]  # Limit to top 5 tips

    def _calculate_scenario_progress(self, analysis: NegotiationAnalysis,
                                   scenario_context: ScenarioContext,
                                   current_stage: int) -> Dict[str, Any]:
        """Calculate progress through the negotiation scenario"""
        
        total_stages = 3  # Most scenarios have 3 stages
        progress_percentage = (current_stage / total_stages) * 100
        
        # Calculate readiness for next stage
        readiness_score = (
            analysis.overall_score * 0.4 +
            analysis.professionalism_score * 0.3 +
            len(analysis.strategies_detected) * 10 * 0.3
        )
        
        return {
            'current_stage': current_stage,
            'total_stages': total_stages,
            'progress_percentage': min(progress_percentage, 100),
            'readiness_score': min(readiness_score, 100),
            'strategies_used': len(analysis.strategies_detected),
            'scenario_difficulty': scenario_context.difficulty_level,
            'next_stage_unlocked': readiness_score >= 70
        }

    def _extract_salary_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract salary information from user response"""
        # Look for NPR amounts
        npr_match = re.search(r'NPR\s*[\d,]+', response, re.IGNORECASE)
        if npr_match:
            amount_str = re.sub(r'[^\d]', '', npr_match.group())
            return {'amount': int(amount_str), 'currency': 'NPR'}
        
        # Look for USD amounts
        usd_match = re.search(r'(\$|USD)\s*[\d,]+', response, re.IGNORECASE)
        if usd_match:
            amount_str = re.sub(r'[^\d]', '', usd_match.group())
            return {'amount': int(amount_str), 'currency': 'USD'}
        
        return None

    def _analyze_salary_positioning(self, salary_mentioned: Dict[str, Any],
                                  expected_range: Dict[str, float]) -> str:
        """Analyze how user's salary request compares to expected range"""
        if salary_mentioned['currency'] != expected_range['currency']:
            return "💡 Consider using the same currency as the job posting for clarity."
        
        amount = salary_mentioned['amount']
        min_range = expected_range['min']
        max_range = expected_range['max']
        
        if amount < min_range:
            return f"⚠️ Your request ({amount:,}) is below the expected range ({min_range:,}-{max_range:,}). Consider aiming higher."
        elif amount > max_range * 1.2:  # 20% above max
            return f"⚠️ Your request ({amount:,}) is significantly above the expected range ({min_range:,}-{max_range:,}). Consider market realities."
        elif amount > max_range:
            return f"💡 Your request ({amount:,}) is above the range ({min_range:,}-{max_range:,}) but could be justified with strong value proposition."
        else:
            return f"✅ Your request ({amount:,}) is within the expected range ({min_range:,}-{max_range:,})."

    def _is_salary_unrealistic(self, response: str, scenario_context: ScenarioContext) -> bool:
        """Check if salary request is unrealistic for the scenario"""
        salary_info = self._extract_salary_from_response(response)
        if not salary_info:
            return False
        
        expected_range = scenario_context.expected_salary_range
        if salary_info['currency'] != expected_range['currency']:
            return False
        
        # Consider unrealistic if more than 50% above max range
        return salary_info['amount'] > expected_range['max'] * 1.5

    def get_scenario_hints(self, scenario_id: str, stage: int = 1) -> List[str]:
        """Get contextual hints for a specific scenario and stage"""
        scenario_context = self.scenario_contexts.get(scenario_id)
        if not scenario_context:
            return []
        
        base_hints = [
            "Research market salary ranges for your position and location",
            "Prepare specific examples of your achievements and value",
            "Practice active listening and acknowledge employer constraints",
            "Ask questions about benefits, growth opportunities, and timeline"
        ]
        
        # Add scenario-specific hints
        if scenario_context.scenario_type == 'startup':
            base_hints.extend([
                "Discuss equity participation and growth potential",
                "Show enthusiasm for the company's mission and vision",
                "Be flexible with base salary in exchange for equity"
            ])
        elif scenario_context.scenario_type == 'corporate':
            base_hints.extend([
                "Emphasize your professional experience and stability",
                "Ask about career advancement and development programs",
                "Focus on total compensation package including benefits"
            ])
        elif scenario_context.scenario_type == 'remote':
            base_hints.extend([
                "Highlight your remote work experience and self-management skills",
                "Discuss timezone flexibility and communication preferences",
                "Emphasize your value despite geographic arbitrage"
            ])
        
        return base_hints[:6]  # Return top 6 hints

    def export_analysis_data(self, analysis: NegotiationAnalysis) -> Dict[str, Any]:
        """Export analysis data for frontend consumption"""
        return {
            'strategies': [strategy.value for strategy in analysis.strategies_detected],
            'strategy_explanations': {
                strategy.value: self.analyzer.get_strategy_explanation(strategy)
                for strategy in analysis.strategies_detected
            },
            'tone': analysis.communication_tone.value,
            'scores': {
                'confidence': round(analysis.confidence_level, 1),
                'professionalism': round(analysis.professionalism_score, 1),
                'persuasiveness': round(analysis.persuasiveness_score, 1),
                'emotional_intelligence': round(analysis.emotional_intelligence_score, 1),
                'overall': round(analysis.overall_score, 1)
            },
            'feedback': {
                'strengths': analysis.strengths,
                'weaknesses': analysis.weaknesses,
                'suggestions': analysis.suggestions,
                'key_phrases': analysis.key_phrases
            }
        }
