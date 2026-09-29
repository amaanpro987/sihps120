from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
def make_report(path,well,status,recommendation=None):
 d=SimpleDocTemplate(path,pagesize=A4); s=getSampleStyleSheet(); st=[Paragraph('Baghewala Well-to-Surface Digital Twin Report',s['Title']),Paragraph(f"Well: {well['well_name']} ({well['well_id']})",s['Heading2']),Spacer(1,10),Paragraph('Decision-support report. Recommendations are advisory and require field validation.',s['BodyText']),Spacer(1,10)]
 st.append(Table([['Data stream','Records']]+[[k,str(v)] for k,v in status.get('records',{}).items()],style=[('GRID',(0,0),(-1,-1),.5,colors.grey)]))
 if recommendation:
  st += [Spacer(1,12),Paragraph('Scenario recommendation',s['Heading2']),Table([['Parameter','Value'],['Stroke (in)',recommendation['stroke_in']],['SPM',recommendation['spm']],['VFD Hz',recommendation['vfd_hz']],['Expected oil (bpd)',recommendation['expected_oil_bpd']],['Expected SOR',recommendation['expected_sor']],['Risk',recommendation['risk_score']],['Confidence',recommendation['confidence']]],style=[('GRID',(0,0),(-1,-1),.5,colors.grey)])]
 d.build(st)
