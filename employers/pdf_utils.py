# PDF Generation Utilities for Employer Features
import io
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from datetime import datetime

def generate_candidate_profile_pdf(candidate, job=None, match_data=None):
    """Generate PDF for candidate profile"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#34495e'),
        borderWidth=1,
        borderColor=colors.HexColor('#3498db'),
        borderPadding=5,
        backColor=colors.HexColor('#ecf0f1')
    )
    
    content = []
    
    # Title
    if job:
        title = f"Candidate Profile - {candidate.user_profile.user.get_full_name()} for {job.title}"
    else:
        title = f"Candidate Profile - {candidate.user_profile.user.get_full_name()}"
    
    content.append(Paragraph(title, title_style))
    content.append(Spacer(1, 20))
    
    # Match Score (if available)
    if match_data and 'score' in match_data:
        score_text = f"<b>Match Score: {match_data['score']}%</b>"
        content.append(Paragraph(score_text, styles['Normal']))
        content.append(Spacer(1, 10))
    
    # Personal Information
    content.append(Paragraph("Personal Information", heading_style))
    
    personal_data = [
        ['Full Name:', candidate.user_profile.user.get_full_name() or 'N/A'],
        ['Email:', candidate.user_profile.user.email or 'N/A'],
        ['Phone:', getattr(candidate, 'phone', 'N/A')],
        ['Location:', getattr(candidate, 'preferred_location', 'N/A')],
        ['Experience Level:', getattr(candidate, 'experience_level', 'N/A').title()],
    ]
    
    personal_table = Table(personal_data, colWidths=[2*inch, 4*inch])
    personal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    content.append(personal_table)
    content.append(Spacer(1, 20))
    
    # Professional Summary
    if hasattr(candidate, 'summary') and candidate.summary:
        content.append(Paragraph("Professional Summary", heading_style))
        content.append(Paragraph(candidate.summary, styles['Normal']))
        content.append(Spacer(1, 15))
    
    # Skills
    if hasattr(candidate, 'skills') and candidate.skills:
        content.append(Paragraph("Skills", heading_style))
        skills_list = [s.strip() for s in candidate.skills.split(',') if s.strip()]
        skills_text = ", ".join(skills_list)
        content.append(Paragraph(skills_text, styles['Normal']))
        content.append(Spacer(1, 15))
    
    # Education
    if hasattr(candidate, 'education') and candidate.education:
        content.append(Paragraph("Education", heading_style))
        content.append(Paragraph(candidate.education, styles['Normal']))
        content.append(Spacer(1, 15))
    
    # Match Reasons (if available)
    if match_data and 'match_reasons' in match_data and match_data['match_reasons']:
        content.append(Paragraph("Why This Candidate Matches", heading_style))
        for reason in match_data['match_reasons']:
            content.append(Paragraph(f"• {reason}", styles['Normal']))
        content.append(Spacer(1, 15))
    
    # Footer
    content.append(Spacer(1, 30))
    footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Hireo Employer Platform"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    content.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    
    return buffer

def generate_applications_report_pdf(applications, job=None, employer_profile=None):
    """Generate PDF report for job applications"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER
    )
    
    content = []
    
    # Title
    if job:
        title = f"Applications Report - {job.title}"
    else:
        title = "Applications Report"
    
    content.append(Paragraph(title, title_style))
    content.append(Spacer(1, 20))
    
    # Summary
    total_apps = len(applications)
    summary_text = f"<b>Total Applications: {total_apps}</b>"
    content.append(Paragraph(summary_text, styles['Normal']))
    content.append(Spacer(1, 20))
    
    # Applications Table
    if applications:
        table_data = [['Candidate Name', 'Email', 'Applied Date', 'Status', 'Experience']]
        
        for app in applications[:50]:  # Limit to 50 for PDF readability
            candidate = app.get('candidate', app) if isinstance(app, dict) else app.applicant
            table_data.append([
                candidate.user_profile.user.get_full_name() or 'N/A',
                candidate.user_profile.user.email or 'N/A',
                getattr(app, 'applied_at', datetime.now()).strftime('%m/%d/%Y') if hasattr(app, 'applied_at') else 'N/A',
                getattr(app, 'status', 'N/A').title() if hasattr(app, 'status') else 'N/A',
                getattr(candidate, 'experience_level', 'N/A').title()
            ])
        
        table = Table(table_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
    else:
        content.append(Paragraph("No applications found.", styles['Normal']))
    
    # Footer
    content.append(Spacer(1, 30))
    footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Hireo Employer Platform"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    content.append(Paragraph(footer_text, footer_style))
    
    doc.build(content)
    buffer.seek(0)
    
    return buffer

def generate_smart_matching_report_pdf(candidates, job, total_matches):
    """Generate PDF report for smart matching results"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER
    )
    
    content = []
    
    # Title
    title = f"Smart Matching Report - {job.title}"
    content.append(Paragraph(title, title_style))
    content.append(Spacer(1, 20))
    
    # Job Details
    job_info = f"<b>Position:</b> {job.title}<br/>"
    job_info += f"<b>Company:</b> {job.company.name}<br/>"
    job_info += f"<b>Location:</b> {getattr(job.location, 'city', 'N/A')}<br/>"
    job_info += f"<b>Total Matches Found:</b> {total_matches}"
    
    content.append(Paragraph(job_info, styles['Normal']))
    content.append(Spacer(1, 20))
    
    # Top Candidates Table
    if candidates:
        table_data = [['Rank', 'Candidate Name', 'Match Score', 'Experience', 'Location']]
        
        for i, candidate_data in enumerate(candidates[:20], 1):  # Top 20 candidates
            candidate = candidate_data['candidate']
            score = candidate_data['score']
            
            table_data.append([
                str(i),
                candidate.user_profile.user.get_full_name() or 'N/A',
                f"{score}%",
                getattr(candidate, 'experience_level', 'N/A').title(),
                getattr(candidate, 'preferred_location', 'N/A')
            ])
        
        table = Table(table_data, colWidths=[0.5*inch, 2*inch, 1*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
    else:
        content.append(Paragraph("No matching candidates found.", styles['Normal']))
    
    # Footer
    content.append(Spacer(1, 30))
    footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Hireo Smart Matching System"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    content.append(Paragraph(footer_text, footer_style))
    
    doc.build(content)
    buffer.seek(0)
    
    return buffer

def create_pdf_response(buffer, filename):
    """Create HTTP response for PDF download"""
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
