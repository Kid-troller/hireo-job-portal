"""
Advanced Negotiation Analysis Engine
Analyzes user responses for negotiation strategies, tactics, and effectiveness
"""

import re
import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class NegotiationStrategy(Enum):
    ANCHORING = "anchoring"
    MARKET_RESEARCH = "market_research"
    VALUE_PROPOSITION = "value_proposition"
    COLLABORATIVE = "collaborative"
    COMPETITIVE = "competitive"
    EMOTIONAL_APPEAL = "emotional_appeal"
    LOGICAL_REASONING = "logical_reasoning"
    ALTERNATIVE_COMPENSATION = "alternative_compensation"
    TIMELINE_PRESSURE = "timeline_pressure"
    RELATIONSHIP_BUILDING = "relationship_building"

class CommunicationTone(Enum):
    PROFESSIONAL = "professional"
    ASSERTIVE = "assertive"
    COLLABORATIVE = "collaborative"
    DEFENSIVE = "defensive"
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"

@dataclass
class NegotiationAnalysis:
    strategies_detected: List[NegotiationStrategy]
    communication_tone: CommunicationTone
    confidence_level: float
    professionalism_score: float
    persuasiveness_score: float
    emotional_intelligence_score: float
    key_phrases: List[str]
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    overall_score: float

class NegotiationAnalyzer:
    def __init__(self):
        self.strategy_patterns = {
            NegotiationStrategy.ANCHORING: [
                r'based on my research.*(\$|NPR|USD)\s*[\d,]+',
                r'market rate.*(\$|NPR|USD)\s*[\d,]+',
                r'industry standard.*(\$|NPR|USD)\s*[\d,]+',
                r'expecting.*(\$|NPR|USD)\s*[\d,]+'
            ],
            NegotiationStrategy.MARKET_RESEARCH: [
                r'according to.*research',
                r'market data shows',
                r'industry reports',
                r'salary surveys',
                r'glassdoor|payscale|salary\.com',
                r'comparable positions'
            ],
            NegotiationStrategy.VALUE_PROPOSITION: [
                r'my experience in',
                r'i bring.*value',
                r'my skills in',
                r'proven track record',
                r'i have.*years of experience',
                r'expertise in',
                r'accomplished.*results'
            ],
            NegotiationStrategy.COLLABORATIVE: [
                r'let\'s work together',
                r'mutually beneficial',
                r'win-win',
                r'how can we',
                r'what would work for both',
                r'find a solution'
            ],
            NegotiationStrategy.COMPETITIVE: [
                r'other offers',
                r'competing offer',
                r'another company',
                r'better offer elsewhere',
                r'market competition'
            ],
            NegotiationStrategy.EMOTIONAL_APPEAL: [
                r'excited about',
                r'passionate about',
                r'dream job',
                r'perfect fit',
                r'love to work here'
            ],
            NegotiationStrategy.LOGICAL_REASONING: [
                r'because.*therefore',
                r'given that.*it follows',
                r'the reason is',
                r'logically speaking',
                r'it makes sense'
            ],
            NegotiationStrategy.ALTERNATIVE_COMPENSATION: [
                r'equity|stock options',
                r'benefits package',
                r'professional development',
                r'flexible.*work',
                r'additional.*vacation',
                r'performance bonus',
                r'signing bonus'
            ],
            NegotiationStrategy.TIMELINE_PRESSURE: [
                r'need to decide by',
                r'other offer expires',
                r'timeline for decision',
                r'deadline approaching'
            ],
            NegotiationStrategy.RELATIONSHIP_BUILDING: [
                r'appreciate.*opportunity',
                r'thank you for',
                r'understand your position',
                r'respect.*constraints',
                r'value.*relationship'
            ]
        }
        
        self.tone_indicators = {
            CommunicationTone.PROFESSIONAL: [
                r'thank you', r'appreciate', r'understand', r'respect',
                r'would like to discuss', r'i believe', r'in my opinion'
            ],
            CommunicationTone.ASSERTIVE: [
                r'i expect', r'i require', r'i need', r'must have',
                r'non-negotiable', r'firm on'
            ],
            CommunicationTone.COLLABORATIVE: [
                r'together', r'partnership', r'mutual', r'both parties',
                r'work with you', r'find a way'
            ],
            CommunicationTone.DEFENSIVE: [
                r'but i', r'however', r'you don\'t understand',
                r'that\'s not fair', r'i deserve'
            ],
            CommunicationTone.CONFIDENT: [
                r'i\'m confident', r'i know', r'i\'m certain',
                r'without a doubt', r'clearly'
            ],
            CommunicationTone.UNCERTAIN: [
                r'i think maybe', r'perhaps', r'i\'m not sure',
                r'might be', r'possibly'
            ]
        }
        
        self.positive_phrases = [
            'market research', 'value proposition', 'mutual benefit',
            'professional development', 'long-term growth', 'team contribution',
            'industry standards', 'competitive offer', 'skill set',
            'track record', 'proven results', 'expertise'
        ]
        
        self.negative_indicators = [
            'demand', 'insist', 'refuse', 'unacceptable',
            'ridiculous', 'unfair', 'disappointed', 'frustrated'
        ]

    def analyze_response(self, response: str, context: Dict[str, Any] = None) -> NegotiationAnalysis:
        """
        Comprehensive analysis of negotiation response
        """
        response_lower = response.lower()
        
        # Detect strategies
        strategies = self._detect_strategies(response_lower)
        
        # Analyze communication tone
        tone = self._analyze_tone(response_lower)
        
        # Calculate scores
        confidence_level = self._calculate_confidence(response_lower)
        professionalism_score = self._calculate_professionalism(response_lower)
        persuasiveness_score = self._calculate_persuasiveness(response_lower, strategies)
        emotional_intelligence_score = self._calculate_emotional_intelligence(response_lower)
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases(response)
        
        # Generate feedback
        strengths = self._identify_strengths(strategies, tone, response_lower)
        weaknesses = self._identify_weaknesses(response_lower, strategies)
        suggestions = self._generate_suggestions(weaknesses, strategies, tone)
        
        # Calculate overall score
        overall_score = (confidence_level + professionalism_score + 
                        persuasiveness_score + emotional_intelligence_score) / 4
        
        return NegotiationAnalysis(
            strategies_detected=strategies,
            communication_tone=tone,
            confidence_level=confidence_level,
            professionalism_score=professionalism_score,
            persuasiveness_score=persuasiveness_score,
            emotional_intelligence_score=emotional_intelligence_score,
            key_phrases=key_phrases,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            overall_score=overall_score
        )

    def _detect_strategies(self, response: str) -> List[NegotiationStrategy]:
        """Detect negotiation strategies used in the response"""
        detected_strategies = []
        
        for strategy, patterns in self.strategy_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response, re.IGNORECASE):
                    detected_strategies.append(strategy)
                    break
        
        return detected_strategies

    def _analyze_tone(self, response: str) -> CommunicationTone:
        """Analyze the communication tone of the response"""
        tone_scores = {}
        
        for tone, indicators in self.tone_indicators.items():
            score = sum(1 for indicator in indicators 
                       if re.search(indicator, response, re.IGNORECASE))
            if score > 0:
                tone_scores[tone] = score
        
        if not tone_scores:
            return CommunicationTone.PROFESSIONAL
        
        return max(tone_scores.keys(), key=lambda k: tone_scores[k])

    def _calculate_confidence(self, response: str) -> float:
        """Calculate confidence level based on language patterns"""
        confidence_indicators = [
            r'i\'m confident', r'i believe', r'i know', r'clearly',
            r'definitely', r'certainly', r'without doubt'
        ]
        
        uncertainty_indicators = [
            r'maybe', r'perhaps', r'i think', r'possibly',
            r'might be', r'not sure', r'i guess'
        ]
        
        confidence_score = sum(1 for pattern in confidence_indicators
                             if re.search(pattern, response, re.IGNORECASE))
        
        uncertainty_score = sum(1 for pattern in uncertainty_indicators
                              if re.search(pattern, response, re.IGNORECASE))
        
        # Base score of 60, adjust based on indicators
        base_score = 60
        confidence_adjustment = confidence_score * 10
        uncertainty_penalty = uncertainty_score * 8
        
        # Word count bonus (longer responses tend to show more confidence)
        word_count = len(response.split())
        length_bonus = min(word_count / 5, 20)  # Max 20 points for length
        
        final_score = base_score + confidence_adjustment - uncertainty_penalty + length_bonus
        return min(max(final_score, 0), 100)

    def _calculate_professionalism(self, response: str) -> float:
        """Calculate professionalism score"""
        professional_indicators = [
            r'thank you', r'appreciate', r'understand', r'respect',
            r'please', r'would like', r'could we', r'i believe'
        ]
        
        unprofessional_indicators = [
            r'demand', r'insist', r'ridiculous', r'unfair',
            r'stupid', r'crazy', r'outrageous'
        ]
        
        professional_score = sum(1 for pattern in professional_indicators
                               if re.search(pattern, response, re.IGNORECASE))
        
        unprofessional_score = sum(1 for pattern in unprofessional_indicators
                                 if re.search(pattern, response, re.IGNORECASE))
        
        # Check for proper grammar indicators
        has_proper_capitalization = response[0].isupper() if response else False
        has_punctuation = any(p in response for p in '.!?')
        
        base_score = 70
        professional_bonus = professional_score * 8
        unprofessional_penalty = unprofessional_score * 15
        grammar_bonus = (has_proper_capitalization + has_punctuation) * 5
        
        final_score = base_score + professional_bonus - unprofessional_penalty + grammar_bonus
        return min(max(final_score, 0), 100)

    def _calculate_persuasiveness(self, response: str, strategies: List[NegotiationStrategy]) -> float:
        """Calculate persuasiveness based on strategies and content"""
        base_score = 50
        
        # Strategy diversity bonus
        strategy_bonus = len(strategies) * 8
        
        # Specific high-value strategies
        high_value_strategies = [
            NegotiationStrategy.MARKET_RESEARCH,
            NegotiationStrategy.VALUE_PROPOSITION,
            NegotiationStrategy.COLLABORATIVE
        ]
        
        high_value_bonus = sum(15 for strategy in strategies 
                              if strategy in high_value_strategies)
        
        # Evidence and data usage
        has_numbers = bool(re.search(r'\d+', response))
        has_specific_examples = bool(re.search(r'for example|such as|including', response, re.IGNORECASE))
        
        evidence_bonus = (has_numbers + has_specific_examples) * 10
        
        # Logical structure
        has_reasoning = bool(re.search(r'because|since|therefore|as a result', response, re.IGNORECASE))
        structure_bonus = has_reasoning * 8
        
        final_score = base_score + strategy_bonus + high_value_bonus + evidence_bonus + structure_bonus
        return min(max(final_score, 0), 100)

    def _calculate_emotional_intelligence(self, response: str) -> float:
        """Calculate emotional intelligence score"""
        empathy_indicators = [
            r'understand.*position', r'appreciate.*constraints',
            r'respect.*decision', r'see your point'
        ]
        
        relationship_building = [
            r'work together', r'partnership', r'mutual',
            r'both.*benefit', r'team'
        ]
        
        emotional_awareness = [
            r'excited', r'passionate', r'enthusiastic',
            r'concerned', r'worried', r'hopeful'
        ]
        
        empathy_score = sum(1 for pattern in empathy_indicators
                           if re.search(pattern, response, re.IGNORECASE))
        
        relationship_score = sum(1 for pattern in relationship_building
                               if re.search(pattern, response, re.IGNORECASE))
        
        emotional_score = sum(1 for pattern in emotional_awareness
                            if re.search(pattern, response, re.IGNORECASE))
        
        base_score = 60
        total_bonus = (empathy_score + relationship_score + emotional_score) * 10
        
        final_score = base_score + total_bonus
        return min(max(final_score, 0), 100)

    def _extract_key_phrases(self, response: str) -> List[str]:
        """Extract key negotiation phrases from the response"""
        key_phrases = []
        
        # Look for salary mentions
        salary_matches = re.findall(r'(NPR|USD|\$)\s*[\d,]+', response, re.IGNORECASE)
        key_phrases.extend(salary_matches)
        
        # Look for percentage mentions
        percentage_matches = re.findall(r'\d+%', response)
        key_phrases.extend(percentage_matches)
        
        # Look for positive phrases
        for phrase in self.positive_phrases:
            if phrase.lower() in response.lower():
                key_phrases.append(phrase)
        
        return key_phrases[:10]  # Limit to top 10

    def _identify_strengths(self, strategies: List[NegotiationStrategy], 
                          tone: CommunicationTone, response: str) -> List[str]:
        """Identify strengths in the negotiation approach"""
        strengths = []
        
        if NegotiationStrategy.MARKET_RESEARCH in strategies:
            strengths.append("Used market research to support position")
        
        if NegotiationStrategy.VALUE_PROPOSITION in strategies:
            strengths.append("Clearly articulated personal value proposition")
        
        if NegotiationStrategy.COLLABORATIVE in strategies:
            strengths.append("Demonstrated collaborative approach")
        
        if tone == CommunicationTone.PROFESSIONAL:
            strengths.append("Maintained professional tone throughout")
        
        if tone == CommunicationTone.CONFIDENT:
            strengths.append("Showed confidence in communication")
        
        if re.search(r'\d+', response):
            strengths.append("Included specific numbers and data")
        
        if re.search(r'thank|appreciate', response, re.IGNORECASE):
            strengths.append("Expressed gratitude and appreciation")
        
        if len(response.split()) > 50:
            strengths.append("Provided detailed and thoughtful response")
        
        return strengths

    def _identify_weaknesses(self, response: str, strategies: List[NegotiationStrategy]) -> List[str]:
        """Identify areas for improvement"""
        weaknesses = []
        
        if not strategies:
            weaknesses.append("No clear negotiation strategies detected")
        
        if NegotiationStrategy.MARKET_RESEARCH not in strategies:
            weaknesses.append("Could benefit from market research data")
        
        if not re.search(r'\d+', response):
            weaknesses.append("Missing specific salary figures or percentages")
        
        if not re.search(r'\?', response):
            weaknesses.append("Could ask more clarifying questions")
        
        if len(response.split()) < 30:
            weaknesses.append("Response could be more detailed")
        
        if any(neg in response.lower() for neg in self.negative_indicators):
            weaknesses.append("Tone could be more positive and collaborative")
        
        if NegotiationStrategy.VALUE_PROPOSITION not in strategies:
            weaknesses.append("Could better highlight personal value and achievements")
        
        return weaknesses

    def _generate_suggestions(self, weaknesses: List[str], 
                            strategies: List[NegotiationStrategy],
                            tone: CommunicationTone) -> List[str]:
        """Generate actionable suggestions for improvement"""
        suggestions = []
        
        if "No clear negotiation strategies detected" in weaknesses:
            suggestions.append("Try incorporating market research or value proposition strategies")
        
        if "Missing specific salary figures" in weaknesses:
            suggestions.append("Include specific salary ranges based on market research")
        
        if "Could ask more clarifying questions" in weaknesses:
            suggestions.append("Ask questions about benefits, growth opportunities, or timeline")
        
        if "Response could be more detailed" in weaknesses:
            suggestions.append("Provide more context about your experience and qualifications")
        
        if tone == CommunicationTone.AGGRESSIVE:
            suggestions.append("Consider a more collaborative and professional tone")
        
        if NegotiationStrategy.ALTERNATIVE_COMPENSATION not in strategies:
            suggestions.append("Consider discussing benefits, equity, or professional development")
        
        suggestions.append("Practice active listening and acknowledge the employer's constraints")
        suggestions.append("End with a clear next step or call to action")
        
        return suggestions[:6]  # Limit to top 6 suggestions

    def get_strategy_explanation(self, strategy: NegotiationStrategy) -> str:
        """Get explanation of what each strategy means"""
        explanations = {
            NegotiationStrategy.ANCHORING: "Setting a reference point with specific numbers or ranges",
            NegotiationStrategy.MARKET_RESEARCH: "Using industry data and salary surveys to support your position",
            NegotiationStrategy.VALUE_PROPOSITION: "Highlighting your unique skills, experience, and contributions",
            NegotiationStrategy.COLLABORATIVE: "Working together to find mutually beneficial solutions",
            NegotiationStrategy.COMPETITIVE: "Leveraging other offers or market competition",
            NegotiationStrategy.EMOTIONAL_APPEAL: "Expressing enthusiasm and passion for the role",
            NegotiationStrategy.LOGICAL_REASONING: "Using clear reasoning and cause-effect relationships",
            NegotiationStrategy.ALTERNATIVE_COMPENSATION: "Discussing non-salary benefits and perks",
            NegotiationStrategy.TIMELINE_PRESSURE: "Creating urgency with deadlines or competing offers",
            NegotiationStrategy.RELATIONSHIP_BUILDING: "Focusing on long-term partnership and mutual respect"
        }
        return explanations.get(strategy, "Unknown strategy")
