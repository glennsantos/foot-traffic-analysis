from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
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
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

class LocationViabilityReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
        # Criteria for scoring indicators
        self.criteria = {
            'restaurants_and_cafes': {'threshold': 4, 'weight': 0.13, 'description': 'Food establishments attract consistent foot traffic'},
            'shops': {'threshold': 8, 'weight': 0.17, 'description': 'Retail establishments are primary foot traffic generators'},
            'intersection_count': {'threshold': 20, 'weight': 0.12, 'description': 'Road intersections indicate pedestrian movement'},
            'office_buildings': {'threshold': 3, 'weight': 0.10, 'description': 'Office buildings generate strong B2B lunch crowd traffic'},
            'schools_universities': {'threshold': 1, 'weight': 0.09, 'description': 'Educational institutions bring regular crowds'},
            'transport_hubs': {'threshold': 2, 'weight': 0.10, 'description': 'Public transport hubs concentrate pedestrians'},
            'hospitals_clinics': {'threshold': 1, 'weight': 0.07, 'description': 'Healthcare facilities ensure steady visitor flow'},
            'parking_lots': {'threshold': 1, 'weight': 0.07, 'description': 'Parking facilities boost drive-in accessibility'},
            'pedestrian_crossings': {'threshold': 3, 'weight': 0.07, 'description': 'Pedestrian infrastructure indicates walkability'},
            'markets': {'threshold': 1, 'weight': 0.06, 'description': 'Markets create concentrated commercial activity'},
            'tourist_sites': {'threshold': 1, 'weight': 0.01, 'description': 'Tourist attractions bring occasional crowds'},
            'places_of_worship': {'threshold': 1, 'weight': 0.01, 'description': 'Religious sites generate periodic gatherings'}
        }
    
    def setup_custom_styles(self):
        self.ink = colors.HexColor('#172c3b')
        self.teal = colors.HexColor('#087f73')
        self.muted = colors.HexColor('#596c79')
        self.line = colors.HexColor('#dce5e7')
        self.content_width = A4[0] - 88
        self.styles['Normal'].fontSize = 9
        self.styles['Normal'].leading = 14
        self.styles['Normal'].textColor = self.ink
        self.styles['Heading3'].textColor = self.ink
        self.styles['Heading3'].fontSize = 12
        self.styles['Heading3'].leading = 16
        self.styles['Heading3'].spaceBefore = 12
        self.styles['Heading3'].spaceAfter = 8
        self.title_style = ParagraphStyle(
            'CustomTitle', parent=self.styles['Heading1'], fontSize=28,
            leading=33, spaceAfter=12, textColor=self.ink)
        self.heading_style = ParagraphStyle(
            'CustomHeading', parent=self.styles['Heading2'], fontSize=17,
            leading=22, spaceBefore=12, spaceAfter=12, textColor=self.ink)
        self.summary_style = ParagraphStyle(
            'Summary', parent=self.styles['Normal'], fontSize=10, leading=16,
            spaceAfter=12, textColor=self.ink)
        self.cell_style = ParagraphStyle(
            'TableCell', parent=self.styles['Normal'], fontSize=8, leading=11)
        self.cell_header_style = ParagraphStyle(
            'TableHeader', parent=self.cell_style, textColor=colors.white,
            fontName='Helvetica-Bold')

    def styled_table(self, data, widths):
        rows = [[Paragraph(escape(str(cell)), self.cell_header_style if i == 0
                           else self.cell_style) for cell in row]
                for i, row in enumerate(data)]
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.ink),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#f3f6f6')]),
            ('LINEBELOW', (0, 0), (-1, 0), 1, self.teal),
            ('LINEBELOW', (0, 1), (-1, -1), 0.4, self.line),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 9),
            ('RIGHTPADDING', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ]))
        return table

    def draw_page(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(self.teal)
        canvas.setLineWidth(2)
        canvas.line(44, height - 32, width - 44, height - 32)
        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(self.ink)
        canvas.drawString(44, height - 24, 'RETAIL LOCATION / SITE SCREENING')
        canvas.setStrokeColor(self.line)
        canvas.setLineWidth(0.5)
        canvas.line(44, 39, width - 44, 39)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.muted)
        canvas.drawString(44, 26, 'Data (c) OpenStreetMap contributors | Verify conditions on site')
        canvas.drawRightString(width - 44, 26, f'{doc.page}')
        canvas.restoreState()

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
        
        if viability_percentage >= 98:
            rating = "BEST"
            color = colors.darkgreen
        elif viability_percentage >= 95:
            rating = "OUTSTANDING"
            color = colors.green
        elif viability_percentage >= 85:
            rating = "EXCELLENT"
            color = colors.blue
        elif viability_percentage >= 80:
            rating = "GOOD"
            color = colors.darkblue
        elif viability_percentage >= 70:
            rating = "MODERATE"
            color = colors.orange
        else:
            rating = "POOR"
            color = colors.red
        
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
        
        Location: {escape(str(location_name))}<br/>
        Coordinates: {lat:.4f}, {lon:.4f}<br/>
        Analysis Radius: {radius}m<br/>
        Overall Viability: <b>{viability_percentage:.1f}% ({rating})</b><br/>
        Criteria Met: {criteria_met}/{total_criteria}<br/><br/>
        
        <b>Key Findings:</b><br/>
        • Strongest indicators: {', '.join(top_indicators)}<br/>
        • Areas for improvement: {', '.join(bottom_indicators)}<br/>
        • This location shows <b>{rating.lower()}</b> potential for foot traffic generation<br/>
        """
        
        if viability_percentage >= 85:
            summary += "• <b>Recommendation:</b> Highly suitable for foot traffic-dependent businesses<br/>"
        elif viability_percentage >= 70:
            summary += "• <b>Recommendation:</b> Moderately suitable, consider specific business type<br/>"
        else:
            summary += "• <b>Recommendation:</b> Consider alternative locations or targeted improvements<br/>"
        
        return summary
    
    def create_indicators_table(self, scores):
        """Create a ranked indicator table within the printable page width."""
        data = [['Rank', 'Indicator', 'Count', 'Target', 'Score', 'Status']]
        for i, score in enumerate(scores, 1):
            data.append([str(i), self.format_indicator_name(score['indicator']),
                         str(score['count']), str(score['threshold']),
                         f"{score['base_score']:.1f}%",
                         'Met' if score['meets_criteria'] else 'Below target'])
        return self.styled_table(data, [42, self.content_width - 256, 43, 43, 56, 72])

    def create_places_table(self, indicator_name, places_data):
        """Keep complete names and addresses readable with wrapped cells."""
        if not places_data:
            return None
        data = [['Name', 'Latitude', 'Longitude', 'Address']]
        for place in places_data[:20]:
            lat_str = f"{place['latitude']:.6f}" if place.get('latitude') is not None else 'N/A'
            lon_str = f"{place['longitude']:.6f}" if place.get('longitude') is not None else 'N/A'
            data.append([place.get('name') or 'Unnamed place', lat_str, lon_str,
                         place.get('address') or 'Address not mapped'])
        return self.styled_table(data, [155, 74, 74, self.content_width - 303])

    def generate_report(self, analysis_data, location_name, lat, lon, radius, output_path):
        """Generate the complete PDF report"""
        doc = SimpleDocTemplate(
            output_path, pagesize=A4, leftMargin=44, rightMargin=44,
            topMargin=54, bottomMargin=56,
            title=f"Retail location report - {location_name}", author='Retail Location Viability Analyzer')
        story = []
        
        # Calculate scores and viability
        scores = self.calculate_indicator_scores(analysis_data)
        viability_percentage, rating, rating_color = self.calculate_overall_viability(scores)
        
        # Title
        story.append(Paragraph("Retail location report", self.title_style))
        story.append(Spacer(1, 20))
        
        summary_text = self.generate_summary(location_name, lat, lon, radius, viability_percentage, rating, scores)
        story.append(Paragraph(escape(str(location_name)), self.heading_style))
        story.append(Paragraph(f"{lat:.4f}, {lon:.4f} &nbsp; | &nbsp; {radius} m radius", self.styles['Normal']))
        story.append(Spacer(1, 18))
        score_style = ParagraphStyle(
            'Score', parent=self.styles['Normal'], fontSize=30, leading=36,
            textColor=colors.white, fontName='Helvetica-Bold')
        label_style = ParagraphStyle(
            'ScoreLabel', parent=self.styles['Normal'], fontSize=10,
            leading=15, textColor=colors.HexColor('#b7efdb'))
        score_card = Table([[
            Paragraph(f"{viability_percentage:.1f}%", score_style),
            Paragraph(f"MODEL VIABILITY SCORE<br/><b>{rating}</b><br/>"
                      f"{sum(s['meets_criteria'] for s in scores)} of {len(scores)} criteria met", label_style)
        ]], colWidths=[150, self.content_width - 150])
        score_card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.ink),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 18),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ]))
        story.append(score_card)
        story.append(Spacer(1, 14))
        story.append(Paragraph(
            "This score summarizes mapped indicators against the app's thresholds. "
            "It is not a measured pedestrian count or a sales forecast. "
            "Confirm map entries, pedestrian activity, rent, and site access before deciding.", self.styles['Normal']))
        story.append(Spacer(1, 16))
        story.append(Paragraph(summary_text, self.summary_style))
        story.append(PageBreak())

        # Detailed Analysis
        story.append(Paragraph("Indicator comparison", self.heading_style))
        story.append(Paragraph("Indicators ranked from most promising to least promising:", self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Indicators table
        story.append(self.create_indicators_table(scores))
        story.append(Spacer(1, 20))
        
        # Detailed descriptions
        story.append(Paragraph("Nearby places and indicator details", self.heading_style))
        
        for i, score in enumerate(scores, 1):
            section_start = len(story)
            indicator_name = self.format_indicator_name(score['indicator'])
            status_text = "MEETS CRITERIA" if score['meets_criteria'] else "BELOW THRESHOLD"
            status_color = self.teal if score['meets_criteria'] else colors.HexColor('#965224')
            
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
            
            # Detailed places table (if available)
            if score['places'] and len(score['places']) > 0:
                # Get detailed places data from analysis_data
                detailed_places = None
                if score['indicator'] in analysis_data:
                    indicator_data = analysis_data[score['indicator']]
                    if isinstance(indicator_data, dict) and 'detailed_places' in indicator_data:
                        detailed_places = indicator_data['detailed_places']
                
                if detailed_places and len(detailed_places) > 0:
                    story.append(Spacer(1, 8))
                    story.append(Paragraph(f"<b>Detailed Places List:</b>", self.styles['Normal']))
                    story.append(Spacer(1, 4))
                    
                    places_table = self.create_places_table(indicator_name, detailed_places)
                    if places_table:
                        story.append(places_table)
                        
                        if len(detailed_places) > 20:
                            story.append(Spacer(1, 4))
                            story.append(Paragraph(f"<i>Showing first 20 of {len(detailed_places)} places</i>", self.styles['Normal']))
                else:
                    # Fallback to simple places table using formatted place names
                    story.append(Spacer(1, 8))
                    story.append(Paragraph(f"<b>Places Found:</b>", self.styles['Normal']))
                    story.append(Spacer(1, 4))
                    
                    # Create simple table with just place names
                    places_data = [['Place Name']]
                    for place_name in score['places'][:20]:  # Limit to first 20 places
                        if place_name and place_name != 'nan (nan)':  # Filter out invalid entries
                            places_data.append([place_name])
                    
                    if len(places_data) > 1:  # Only create table if we have actual places
                        simple_table = self.styled_table(places_data, [self.content_width])
                        story.append(simple_table)
                        
                        if len(score['places']) > 20:
                            story.append(Spacer(1, 4))
                            story.append(Paragraph(f"<i>Showing first 20 of {len(score['places'])} places</i>", self.styles['Normal']))
                    else:
                        # If no valid places, show a simple text message
                        story.append(Paragraph(f"No specific place names available for this indicator.", self.styles['Normal']))
            
            story.append(Spacer(1, 12))
            section = story[section_start:]
            story[section_start:] = [KeepTogether(section)]
        
        # Conclusion
        story.append(PageBreak())
        story.append(Paragraph("Assessment and next steps", self.heading_style))
        
        conclusion = self.generate_conclusion(viability_percentage, rating, scores)
        story.append(Paragraph(conclusion, self.styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = (
            f"Report generated on {datetime.now(ZoneInfo('Asia/Manila')).strftime('%B %d, %Y at %I:%M %p PHT')} | "
            f"Data © OpenStreetMap contributors"
        )
        footer_style = ParagraphStyle('Footer', parent=self.styles['Normal'], 
                                    fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
        story.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(story, onFirstPage=self.draw_page, onLaterPages=self.draw_page)
        
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
        
        if viability_percentage >= 95:
            conclusion += """
            <b>Recommendations:</b><br/>
            • This location is <b>outstanding/best</b> for foot traffic-dependent businesses<br/>
            • Ideal for premium retail, flagship stores, or high-end restaurants<br/>
            • Exceptional infrastructure supports maximum business potential<br/>
            • Consider premium positioning and pricing strategies<br/><br/>
            """
        elif viability_percentage >= 85:
            conclusion += """
            <b>Recommendations:</b><br/>
            • This location is <b>excellent</b> for foot traffic-dependent businesses<br/>
            • Consider high-visibility retail, restaurants, or service businesses<br/>
            • The strong infrastructure supports premium positioning<br/>
            • Monitor peak hours to optimize operations<br/><br/>
            """
        elif viability_percentage >= 80:
            conclusion += """
            <b>Recommendations:</b><br/>
            • This location is <b>good</b> for most commercial activities<br/>
            • Focus on businesses that complement existing strong indicators<br/>
            • Consider targeted marketing to maximize foot traffic<br/>
            • Address weaker indicators through partnerships or improvements<br/><br/>
            """
        elif viability_percentage >= 70:
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
            • This location shows <b>poor</b> foot traffic potential<br/>
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
