from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import io
import base64
from datetime import datetime
import os

class LocationViabilityReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
        # Criteria for scoring indicators
        self.criteria = {
            'restaurants_and_cafes': {'threshold': 4, 'weight': 0.15, 'description': 'Food establishments attract consistent foot traffic'},
            'shops': {'threshold': 8, 'weight': 0.20, 'description': 'Retail establishments are primary foot traffic generators'},
            'intersection_count': {'threshold': 20, 'weight': 0.15, 'description': 'Road intersections indicate pedestrian movement'},
            'schools_universities': {'threshold': 1, 'weight': 0.10, 'description': 'Educational institutions bring regular crowds'},
            'hospitals_clinics': {'threshold': 1, 'weight': 0.08, 'description': 'Healthcare facilities ensure steady visitor flow'},
            'bus_stops': {'threshold': 2, 'weight': 0.12, 'description': 'Public transport hubs concentrate pedestrians'},
            'pedestrian_crossings': {'threshold': 3, 'weight': 0.08, 'description': 'Pedestrian infrastructure indicates walkability'},
            'markets': {'threshold': 1, 'weight': 0.07, 'description': 'Markets create concentrated commercial activity'},
            'tourist_sites': {'threshold': 1, 'weight': 0.03, 'description': 'Tourist attractions bring occasional crowds'},
            'places_of_worship': {'threshold': 1, 'weight': 0.02, 'description': 'Religious sites generate periodic gatherings'}
        }
    
    def setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        self.summary_style = ParagraphStyle(
            'Summary',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            backColor=colors.lightgrey,
            borderColor=colors.darkblue,
            borderWidth=1,
            leftIndent=10,
            rightIndent=10,
            topPadding=10,
            bottomPadding=10
        )
    
    def calculate_indicator_scores(self, analysis_data):
        """Calculate scores for each indicator and rank them"""
        scores = []
        
        for indicator, data in analysis_data.items():
            if indicator in self.criteria:
                criteria = self.criteria[indicator]
                
                # Get count value
                if isinstance(data, dict) and 'count' in data:
                    count = data['count']
                    places = data.get('places', [])
                else:
                    count = data
                    places = []
                
                # Calculate score (0-100)
                threshold = criteria['threshold']
                weight = criteria['weight']
                
                # Base score based on meeting threshold
                if count >= threshold:
                    base_score = 100
                else:
                    base_score = (count / threshold) * 100
                
                # Bonus for exceeding threshold significantly
                if count > threshold * 2:
                    base_score = min(120, base_score + 20)
                
                # Weighted score
                weighted_score = base_score * weight
                
                scores.append({
                    'indicator': indicator,
                    'count': count,
                    'threshold': threshold,
                    'base_score': base_score,
                    'weighted_score': weighted_score,
                    'weight': weight,
                    'meets_criteria': count >= threshold,
                    'description': criteria['description'],
                    'places': places
                })
        
        # Sort by weighted score (descending)
        scores.sort(key=lambda x: x['weighted_score'], reverse=True)
        return scores
    
    def calculate_overall_viability(self, scores):
        """Calculate overall viability score and rating"""
        total_weighted_score = sum(score['weighted_score'] for score in scores)
        max_possible_score = sum(100 * criteria['weight'] for criteria in self.criteria.values())
        
        viability_percentage = (total_weighted_score / max_possible_score) * 100
        
        if viability_percentage >= 80:
            rating = "EXCELLENT"
            color = colors.green
        elif viability_percentage >= 65:
            rating = "GOOD"
            color = colors.blue
        elif viability_percentage >= 50:
            rating = "MODERATE"
            color = colors.orange
        elif viability_percentage >= 35:
            rating = "POOR"
            color = colors.red
        else:
            rating = "VERY POOR"
            color = colors.darkred
        
        return viability_percentage, rating, color
    
    def format_indicator_name(self, name):
        """Format indicator name for display"""
        return name.replace('_', ' ').title()
    
    def generate_summary(self, location_name, lat, lon, radius, viability_percentage, rating, scores):
        """Generate executive summary"""
        criteria_met = sum(1 for score in scores if score['meets_criteria'])
        total_criteria = len(scores)
        
        top_indicators = [self.format_indicator_name(score['indicator']) for score in scores[:3]]
        bottom_indicators = [self.format_indicator_name(score['indicator']) for score in scores[-2:]]
        
        summary = f"""
        <b>EXECUTIVE SUMMARY</b><br/><br/>
        
        Location: {location_name}<br/>
        Coordinates: {lat:.4f}, {lon:.4f}<br/>
        Analysis Radius: {radius}m<br/>
        Overall Viability: <b>{viability_percentage:.1f}% ({rating})</b><br/>
        Criteria Met: {criteria_met}/{total_criteria}<br/><br/>
        
        <b>Key Findings:</b><br/>
        • Strongest indicators: {', '.join(top_indicators)}<br/>
        • Areas for improvement: {', '.join(bottom_indicators)}<br/>
        • This location shows <b>{rating.lower()}</b> potential for foot traffic generation<br/>
        """
        
        if viability_percentage >= 65:
            summary += "• <b>Recommendation:</b> Highly suitable for foot traffic-dependent businesses<br/>"
        elif viability_percentage >= 50:
            summary += "• <b>Recommendation:</b> Moderately suitable, consider specific business type<br/>"
        else:
            summary += "• <b>Recommendation:</b> Consider alternative locations or targeted improvements<br/>"
        
        return summary
    
    def create_indicators_table(self, scores):
        """Create detailed indicators table"""
        data = [['Rank', 'Indicator', 'Count', 'Threshold', 'Score', 'Status']]
        
        for i, score in enumerate(scores, 1):
            status = "✓ Met" if score['meets_criteria'] else "✗ Not Met"
            status_color = colors.green if score['meets_criteria'] else colors.red
            
            data.append([
                str(i),
                self.format_indicator_name(score['indicator']),
                str(score['count']),
                str(score['threshold']),
                f"{score['base_score']:.1f}%",
                status
            ])
        
        table = Table(data, colWidths=[0.5*inch, 2.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        return table
    
    def generate_report(self, analysis_data, location_name, lat, lon, radius, output_path):
        """Generate the complete PDF report"""
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        
        # Calculate scores and viability
        scores = self.calculate_indicator_scores(analysis_data)
        viability_percentage, rating, rating_color = self.calculate_overall_viability(scores)
        
        # Title
        story.append(Paragraph("FOOT TRAFFIC VIABILITY ANALYSIS", self.title_style))
        story.append(Spacer(1, 20))
        
        # Summary section
        summary_text = self.generate_summary(location_name, lat, lon, radius, viability_percentage, rating, scores)
        story.append(Paragraph(summary_text, self.summary_style))
        story.append(Spacer(1, 20))
        
        # Overall Score
        score_text = f"<b>OVERALL VIABILITY SCORE: {viability_percentage:.1f}% ({rating})</b>"
        score_style = ParagraphStyle('Score', parent=self.styles['Normal'], fontSize=16, 
                                   alignment=TA_CENTER, textColor=rating_color, spaceAfter=20)
        story.append(Paragraph(score_text, score_style))
        story.append(Spacer(1, 20))
        
        # Detailed Analysis
        story.append(Paragraph("DETAILED INDICATOR ANALYSIS", self.heading_style))
        story.append(Paragraph("Indicators ranked from most promising to least promising:", self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Indicators table
        story.append(self.create_indicators_table(scores))
        story.append(Spacer(1, 20))
        
        # Detailed descriptions
        story.append(Paragraph("INDICATOR DESCRIPTIONS & ANALYSIS", self.heading_style))
        
        for i, score in enumerate(scores, 1):
            indicator_name = self.format_indicator_name(score['indicator'])
            status_text = "MEETS CRITERIA" if score['meets_criteria'] else "BELOW THRESHOLD"
            status_color = colors.green if score['meets_criteria'] else colors.red
            
            # Indicator header
            header_text = f"<b>{i}. {indicator_name}</b> (Score: {score['base_score']:.1f}%)"
            story.append(Paragraph(header_text, self.styles['Heading3']))
            
            # Status
            status_para = f"<b>Status:</b> <font color='{status_color.hexval()}'>{status_text}</font>"
            story.append(Paragraph(status_para, self.styles['Normal']))
            
            # Details
            details = f"<b>Count:</b> {score['count']} | <b>Threshold:</b> {score['threshold']} | <b>Weight:</b> {score['weight']*100:.0f}%"
            story.append(Paragraph(details, self.styles['Normal']))
            
            # Description
            story.append(Paragraph(f"<b>Analysis:</b> {score['description']}", self.styles['Normal']))
            
            # Places (if available and not too many)
            if score['places'] and len(score['places']) <= 10:
                places_text = f"<b>Notable Places:</b> {', '.join(score['places'][:5])}"
                if len(score['places']) > 5:
                    places_text += f" (and {len(score['places'])-5} more)"
                story.append(Paragraph(places_text, self.styles['Normal']))
            
            story.append(Spacer(1, 12))
        
        # Conclusion
        story.append(PageBreak())
        story.append(Paragraph("CONCLUSION & RECOMMENDATIONS", self.heading_style))
        
        conclusion = self.generate_conclusion(viability_percentage, rating, scores)
        story.append(Paragraph(conclusion, self.styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        footer_style = ParagraphStyle('Footer', parent=self.styles['Normal'], 
                                    fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
        story.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(story)
        
        return {
            'viability_percentage': viability_percentage,
            'rating': rating,
            'summary': summary_text,
            'scores': scores
        }
    
    def generate_conclusion(self, viability_percentage, rating, scores):
        """Generate conclusion and recommendations"""
        criteria_met = sum(1 for score in scores if score['meets_criteria'])
        total_criteria = len(scores)
        
        conclusion = f"""
        <b>Overall Assessment:</b><br/>
        This location achieved a viability score of <b>{viability_percentage:.1f}%</b>, rating it as <b>{rating}</b> 
        for foot traffic generation. The analysis shows {criteria_met} out of {total_criteria} key criteria are met.<br/><br/>
        """
        
        if viability_percentage >= 80:
            conclusion += """
            <b>Recommendations:</b><br/>
            • This location is <b>excellent</b> for foot traffic-dependent businesses<br/>
            • Consider high-visibility retail, restaurants, or service businesses<br/>
            • The strong infrastructure supports premium positioning<br/>
            • Monitor peak hours to optimize operations<br/><br/>
            """
        elif viability_percentage >= 65:
            conclusion += """
            <b>Recommendations:</b><br/>
            • This location is <b>good</b> for most commercial activities<br/>
            • Focus on businesses that complement existing strong indicators<br/>
            • Consider targeted marketing to maximize foot traffic<br/>
            • Address weaker indicators through partnerships or improvements<br/><br/>
            """
        elif viability_percentage >= 50:
            conclusion += """
            <b>Recommendations:</b><br/>
            • This location has <b>moderate</b> potential requiring careful planning<br/>
            • Choose businesses that don't rely heavily on walk-in traffic<br/>
            • Invest in marketing and visibility improvements<br/>
            • Consider niche markets that align with strong indicators<br/><br/>
            """
        else:
            conclusion += """
            <b>Recommendations:</b><br/>
            • This location shows <b>limited</b> foot traffic potential<br/>
            • Consider alternative locations for foot traffic-dependent businesses<br/>
            • If proceeding, focus on destination businesses with strong marketing<br/>
            • Evaluate infrastructure improvements or wait for area development<br/><br/>
            """
        
        # Top 3 strengths
        top_3 = scores[:3]
        conclusion += f"<b>Key Strengths:</b><br/>"
        for score in top_3:
            conclusion += f"• {self.format_indicator_name(score['indicator'])}: {score['count']} (Score: {score['base_score']:.1f}%)<br/>"
        
        conclusion += "<br/>"
        
        # Areas for improvement
        bottom_2 = [s for s in scores if not s['meets_criteria']][-2:] if any(not s['meets_criteria'] for s in scores) else scores[-2:]
        if bottom_2:
            conclusion += f"<b>Areas for Improvement:</b><br/>"
            for score in bottom_2:
                conclusion += f"• {self.format_indicator_name(score['indicator'])}: {score['count']} (Needs: {score['threshold']})<br/>"
        
        return conclusion 