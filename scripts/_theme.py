"""
Tema compartido: paleta, tipografia, componentes CSS.
Todas las referencias de color, fuente y espaciado viven aqui.
"""

# ─── PALETA PRINCIPAL ───
P = {
    'primary': '#B71C1C',
    'primary-light': '#E53935',
    'primary-bg': '#FFEBEE',
    'secondary': '#F9A825',
    'secondary-light': '#FFF8E1',
    'accent': '#1565C0',
    'accent-light': '#E3F2FD',
    'surface': '#FAFAFA',
    'text': '#212121',
    'text-secondary': '#616161',
    'text-hint': '#9E9E9E',
    'border': '#E0E0E0',
    'border-light': '#F0F0F0',
    'bg': '#F5F5F5',
    'success': '#2E7D32',
    'success-bg': '#E8F5E9',
    'warning': '#E65100',
    'warning-bg': '#FFF3E0',
    'error': '#C62828',
    'error-bg': '#FFEBEE',
    'neutral': '#757575',
    'white': '#FFFFFF',
    'shadow': 'rgba(0,0,0,0.06)',
    'shadow-hover': 'rgba(0,0,0,0.12)',
}

# ─── PALETA DE 13 CANDIDATOS (ColorBrewer Paired + extras) ───
CAND_COLORS = [
    '#E53935','#1E88E5','#43A047','#8E24AA','#FB8C00',
    '#FDD835','#6D4C41','#D81B60','#757575','#00ACC1',
    '#FFB300','#795548','#00897B',
]

# ─── PALETAS DE MAPA ───
YLORRD = ['#FFFFCC','#FFEDA0','#FED976','#FEB24C','#FD8D3C','#FC4E2A','#E31A1C','#BD0026','#800026']
RDBU = ['#2166AC','#4393C3','#92C5DE','#D1E5F0','#F7F7F7','#FDDBC7','#F4A582','#D6604D','#B2182B']
PURPLES = ['#F2F0F7','#DADAEB','#BCBDDC','#9E9AC8','#807DBA','#6A51A3','#54278F','#3F007D','#2C0055']

# ─── TIPOGRAFIA ───
FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace"
FONT_MONO_JS = FONT_MONO.replace("'", "\\'")

# ─── CSS SHARED (componentes base) ───
CSS_RESET = """
  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body { font-family:""" + FONT_FAMILY + """; background:""" + P['bg'] + """; color:""" + P['text'] + """; line-height:1.5; -webkit-font-smoothing:antialiased; }
"""

CSS_CARD = """
  .card { background:""" + P['white'] + """; border-radius:12px; border:1px solid """ + P['border-light'] + """;
    box-shadow:0 1px 3px """ + P['shadow'] + """; transition:box-shadow 0.2s, transform 0.2s; }
  .card:hover { box-shadow:0 4px 12px """ + P['shadow-hover'] + """; }
  .card-header { padding:20px 24px 0; }
  .card-body { padding:20px 24px; }
  .card-title { font-size:16px; font-weight:600; color:""" + P['text'] + """; margin-bottom:4px; }
  .card-subtitle { font-size:12px; color:""" + P['text-secondary'] + """; }
"""

CSS_BUTTON = """
  .btn { display:inline-flex; align-items:center; gap:6px; height:36px; padding:0 16px;
    border:none; border-radius:8px; font-family:""" + FONT_FAMILY + """; font-size:13px; font-weight:500;
    cursor:pointer; transition:all 0.15s; text-decoration:none; line-height:1; }
  .btn-primary { background:""" + P['primary'] + """; color:white; }
  .btn-primary:hover { background:""" + P['primary-light'] + """; }
  .btn-outline { background:transparent; border:1.5px solid """ + P['border'] + """; color:""" + P['text'] + """; }
  .btn-outline:hover { border-color:""" + P['primary'] + """; color:""" + P['primary'] + """; }
  .btn-outline.active { background:""" + P['primary-bg'] + """; border-color:""" + P['primary'] + """; color:""" + P['primary'] + """; }
  .btn-ghost { background:transparent; color:""" + P['text-secondary'] + """; }
  .btn-ghost:hover { background:""" + P['border-light'] + """; color:""" + P['text'] + """; }
  .btn-sm { height:28px; padding:0 10px; font-size:11px; border-radius:6px; }
  .btn-icon { width:36px; padding:0; justify-content:center; }
"""

CSS_INPUT = """
  .input { height:36px; padding:0 12px; border:1.5px solid """ + P['border'] + """; border-radius:8px;
    font-family:""" + FONT_FAMILY + """; font-size:13px; color:""" + P['text'] + """;
    transition:border-color 0.15s, box-shadow 0.15s; background:""" + P['white'] + """; }
  .input:focus { outline:none; border-color:""" + P['primary'] + """; box-shadow:0 0 0 3px """ + P['primary-bg'] + """; }
  .input::placeholder { color:""" + P['text-hint'] + """; }

  .select { height:36px; padding:0 32px 0 12px; border:1.5px solid """ + P['border'] + """; border-radius:8px;
    font-family:""" + FONT_FAMILY + """; font-size:13px; color:""" + P['text'] + """;
    background:""" + P['white'] + """ url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239E9E9E' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E") no-repeat right 10px center;
    -webkit-appearance:none; appearance:none; cursor:pointer; transition:border-color 0.15s; }
  .select:focus { outline:none; border-color:""" + P['primary'] + """; box-shadow:0 0 0 3px """ + P['primary-bg'] + """; }
"""

CSS_TABLE = """
  .table-wrap { overflow-x:auto; border-radius:8px; border:1px solid """ + P['border-light'] + """; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { background:""" + P['bg'] + """; color:""" + P['text-secondary'] + """; font-weight:500; font-size:11px;
    text-transform:uppercase; letter-spacing:0.5px; padding:10px 12px; text-align:left;
    white-space:nowrap; cursor:pointer; position:sticky; top:0; z-index:1;
    border-bottom:1px solid """ + P['border'] + """; user-select:none; }
  th:hover { color:""" + P['primary'] + """; }
  th .sort-arrow { display:inline-block; margin-left:4px; opacity:0; transition:opacity 0.15s; }
  th:hover .sort-arrow, th.sort-active .sort-arrow { opacity:0.5; }
  th.sort-asc .sort-arrow, th.sort-desc .sort-arrow { opacity:1; }
  td { padding:8px 12px; border-bottom:1px solid """ + P['border-light'] + """; }
  tr:nth-child(even) td { background:""" + P['bg'] + """; }
  tr:hover td { background:""" + P['primary-bg'] + """; }
"""

CSS_BADGE = """
  .badge { display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border-radius:6px;
    font-size:11px; font-weight:500; line-height:1.4; }
  .badge-primary { background:""" + P['primary-bg'] + """; color:""" + P['primary'] + """; }
  .badge-success { background:""" + P['success-bg'] + """; color:""" + P['success'] + """; }
  .badge-warning { background:""" + P['warning-bg'] + """; color:""" + P['warning'] + """; }
  .badge-error { background:""" + P['error-bg'] + """; color:""" + P['error'] + """; }
  .badge-neutral { background:""" + P['border-light'] + """; color:""" + P['text-secondary'] + """; }
"""

# ─── RESPONSIVE BREAKPOINTS ───
BP = {'sm': '640px', 'md': '768px', 'lg': '1024px', 'xl': '1280px'}

# ─── COMPONENTES COMPUESTOS ───
CSS_STAT_CARD = """
  .stat-card { background:white; border-radius:12px; padding:20px; border:1px solid """ + P['border-light'] + """;
    box-shadow:0 1px 3px """ + P['shadow'] + """; }
  .stat-card .stat-icon { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; margin-bottom:12px; }
  .stat-card .stat-icon.primary { background:""" + P['primary-bg'] + """; color:""" + P['primary'] + """; }
  .stat-card .stat-icon.accent { background:""" + P['accent-light'] + """; color:""" + P['accent'] + """; }
  .stat-card .stat-icon.success { background:""" + P['success-bg'] + """; color:""" + P['success'] + """; }
  .stat-card .stat-icon.warning { background:""" + P['warning-bg'] + """; color:""" + P['warning'] + """; }
  .stat-card .stat-num { font-family:""" + FONT_MONO + """; font-size:28px; font-weight:700; color:""" + P['text'] + """; line-height:1.1; }
  .stat-card .stat-label { font-size:12px; color:""" + P['text-secondary'] + """; text-transform:uppercase; letter-spacing:0.5px; margin-top:4px; }
  .stat-card .stat-bar { height:3px; border-radius:2px; margin-top:12px; background:""" + P['border-light'] + """; overflow:hidden; }
  .stat-card .stat-bar-fill { height:100%; border-radius:2px; transition:width 0.6s ease; }
"""

CSS_SECTION_NAV = """
  .section-nav { display:flex; gap:4px; padding:4px; background:""" + P['white'] + """;
    border-radius:10px; border:1px solid """ + P['border-light'] + """; overflow-x:auto;
    position:sticky; top:0; z-index:100; }
  .section-nav a { display:flex; align-items:center; gap:6px; padding:6px 14px; border-radius:6px;
    font-size:12px; font-weight:500; color:""" + P['text-secondary'] + """; text-decoration:none;
    white-space:nowrap; transition:all 0.15s; }
  .section-nav a:hover { background:""" + P['border-light'] + """; color:""" + P['text'] + """; }
  .section-nav a.active { background:""" + P['primary-bg'] + """; color:""" + P['primary'] + """; }
"""

CSS_ANIMATIONS = """
  @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
  @keyframes fadeInUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
  @keyframes scaleIn { from { opacity:0; transform:scale(0.95); } to { opacity:1; transform:scale(1); } }
  .anim-fade-in { animation:fadeIn 0.3s ease both; }
  .anim-fade-up { animation:fadeInUp 0.4s ease both; }
  .anim-scale { animation:scaleIn 0.25s ease both; }
  .anim-delay-1 { animation-delay:0.05s; }
  .anim-delay-2 { animation-delay:0.1s; }
  .anim-delay-3 { animation-delay:0.15s; }
  .anim-delay-4 { animation-delay:0.2s; }
"""
