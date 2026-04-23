import streamlit as st
import pandas as pd
import boto3
import io
from datetime import date, datetime, timedelta
import calendar

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLE
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Gestion Paie", page_icon="💰", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
[data-testid="stSidebar"] { background: #0f1117; border-right: 1px solid #1e2130; }
[data-testid="stSidebar"] * { color: #e0e4f0 !important; }
.stApp { background: #f5f6fa; }
.card { background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 16px;
        border: 1px solid #e8eaf0; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.kpi { flex:1; min-width:130px; background:#fff; border-radius:10px; padding:16px 20px;
       border:1px solid #e8eaf0; box-shadow:0 1px 4px rgba(0,0,0,0.04); }
.kpi-label { font-size:11px; font-weight:600; letter-spacing:.08em;
             text-transform:uppercase; color:#8890a8; margin-bottom:6px; }
.kpi-value { font-size:28px; font-weight:600; font-family:'DM Mono',monospace; color:#1a1d2e; }
.kpi-sub   { font-size:12px; color:#8890a8; margin-top:4px; }
.section-title { font-size:13px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
                 color:#8890a8; margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid #e8eaf0; }
.stButton > button { border-radius:8px; font-weight:600; font-family:'DM Sans',sans-serif; }
.res-badge { display:inline-block; padding:2px 9px; border-radius:12px; font-size:11px;
             font-weight:500; margin:2px 2px; white-space:nowrap; line-height:1.6; }
/* ── Planning grid ── */
.plan-table { border-collapse:collapse; width:100%; font-size:12px; }
.plan-th-time { background:#0f1117; color:#8890a8; padding:8px 6px; text-align:center;
                font-size:10px; font-weight:500; white-space:nowrap; border:1px solid #1e2130;
                min-width:72px; position:sticky; left:0; z-index:2; }
.plan-th-day  { background:#0f1117; color:#e0e4f0; padding:8px 10px; text-align:center;
                font-size:12px; font-weight:500; white-space:nowrap;
                border:1px solid #1e2130; min-width:130px; }
.plan-th-day-we { background:#1a1d2e; color:#6870a8; }
.plan-th-day-today { background:#2a4a80; color:#cce0ff; }
.plan-td-time { background:#f8f9fc; color:#8890a8; padding:5px 8px; text-align:center;
                font-size:10px; font-family:'DM Mono',monospace; border:1px solid #e8eaf0;
                white-space:nowrap; vertical-align:middle; position:sticky; left:0;
                z-index:1; min-width:72px; }
.plan-td-cell { padding:4px 5px; border:1px solid #e8eaf0; vertical-align:top;
                min-width:130px; min-height:36px; }
.plan-td-we   { background:#f9fafb; }
.plan-td-today { background:#fffbf0; border-color:#f0d080 !important; }
/* ── Fiche de paie ── */
.fiche-wrap { background:#fff; border-radius:12px; padding:28px 32px; border:1px solid #e8eaf0;
              box-shadow:0 2px 12px rgba(0,0,0,0.06); }
.fiche-titre { font-size:22px; font-weight:700; color:#1a1d2e; letter-spacing:-0.5px; }
.fiche-soustitre { font-size:13px; color:#8890a8; margin-top:2px; }
.fiche-sep  { border:none; border-top:2px solid #e8eaf0; margin:18px 0; }
.fiche-sep-bold { border:none; border-top:2px solid #0f1117; margin:10px 0; }
.fiche-row  { display:flex; justify-content:space-between; align-items:center;
              padding:5px 0; border-bottom:1px solid #f5f5f5; font-size:13px; }
.fiche-row-neg { color:#c0392b; }
.fiche-total { display:flex; justify-content:space-between; font-size:16px;
               font-weight:700; padding:12px 0 0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
TYPES_CONTRAT  = ["CDI","CDD","Intérim","Alternance","Stage","Freelance","Autre"]
STATUTS_CONTRAT= ["Actif","Terminé","Suspendu"]
STATUTS_FICHE  = ["Brouillon","Validée","Envoyée"]

TYPES_HEURE = [
    "Travail","Congé payé","RTT","Maladie","Accident travail",
    "Absent non justifié","Férié","Formation","Astreinte","Heure sup",
]
TYPE_HEURE_CFG = {
    "Travail":             {"bg":"#e6f9f0","dot":"#177049","txt":"#177049","lbl":"Travail"},
    "Congé payé":          {"bg":"#ddeeff","dot":"#1a6fa8","txt":"#1a6fa8","lbl":"Congé"},
    "RTT":                 {"bg":"#ede8fd","dot":"#6b1aa8","txt":"#6b1aa8","lbl":"RTT"},
    "Maladie":             {"bg":"#fde8e8","dot":"#b81c1c","txt":"#b81c1c","lbl":"Maladie"},
    "Accident travail":    {"bg":"#fde8e8","dot":"#c0392b","txt":"#c0392b","lbl":"AT"},
    "Absent non justifié": {"bg":"#fff0e8","dot":"#b84a1c","txt":"#b84a1c","lbl":"Abs.NJ"},
    "Férié":               {"bg":"#fff3e8","dot":"#a86a1a","txt":"#a86a1a","lbl":"Férié"},
    "Formation":           {"bg":"#f0f9e8","dot":"#4a9a1a","txt":"#4a9a1a","lbl":"Forma."},
    "Astreinte":           {"bg":"#f9f0e8","dot":"#a84a1a","txt":"#a84a1a","lbl":"Astr."},
    "Heure sup":           {"bg":"#fde8f9","dot":"#a81a7a","txt":"#a81a7a","lbl":"H.Sup"},
}
TYPE_IMPACT = {
    "Travail":"travail","Formation":"travail","Astreinte":"travail",
    "Congé payé":"conge","RTT":"conge","Férié":"ferie",
    "Maladie":"absence","Accident travail":"absence",
    "Absent non justifié":"absence_np","Heure sup":"sup",
}
TYPES_ABSENCE_RAPIDE = [
    "Congé payé","RTT","Maladie","Accident travail","Absent non justifié","Férié","Formation",
]

HEURES = [f"{h:02d}:00" for h in range(7, 21)]   # 07:00 → 20:00  (14 valeurs)
TIME_SLOTS = [f"{h:02d}:00" for h in range(7, 20)] # lignes calendrier 07:00→19:00
JOURS_FR  = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
MOIS_FR   = ["","Janvier","Février","Mars","Avril","Mai","Juin",
             "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

# Colonnes des tables
RESSOURCES_COLS = ["id_ressource","nom_ressource","type_contrat","heures_hebdo",
                   "taux_horaire","date_debut","date_fin","statut_contrat","notes","date_creation"]
PLANNING_COLS   = ["id_slot","date","heure_debut","heure_fin","id_ressource",
                   "nom_ressource","type_heure","notes","date_creation"]
FICHES_COLS     = ["id_fiche","id_ressource","nom_ressource","mois","annee",
                   "heures_contrat","heures_travail","heures_conge","heures_maladie",
                   "heures_sup","heures_autres","montant_brut","montant_net",
                   "statut","date_generation"]
PARAMS_COLS     = ["type_contrat","heures_hebdo","taux_horaire_base","jours_conge_annuels",
                   "periode_essai_jours","cotisations_salariales_pct",
                   "cotisations_patronales_pct","notes"]

PARAMS_DEFAULT = [
    {"type_contrat":"CDI",       "heures_hebdo":35,"taux_horaire_base":15.0,"jours_conge_annuels":25,"periode_essai_jours":90, "cotisations_salariales_pct":22.0,"cotisations_patronales_pct":42.0,"notes":""},
    {"type_contrat":"CDD",       "heures_hebdo":35,"taux_horaire_base":15.0,"jours_conge_annuels":25,"periode_essai_jours":14, "cotisations_salariales_pct":22.0,"cotisations_patronales_pct":42.0,"notes":""},
    {"type_contrat":"Alternance","heures_hebdo":35,"taux_horaire_base":8.0, "jours_conge_annuels":25,"periode_essai_jours":0,  "cotisations_salariales_pct":6.0, "cotisations_patronales_pct":20.0,"notes":"Exonérations spécifiques apprentissage"},
    {"type_contrat":"Stage",     "heures_hebdo":35,"taux_horaire_base":4.35,"jours_conge_annuels":0, "periode_essai_jours":0,  "cotisations_salariales_pct":0.0, "cotisations_patronales_pct":0.0, "notes":"Gratification minimale légale"},
    {"type_contrat":"Intérim",   "heures_hebdo":35,"taux_horaire_base":15.0,"jours_conge_annuels":25,"periode_essai_jours":0,  "cotisations_salariales_pct":22.0,"cotisations_patronales_pct":42.0,"notes":"Indemnité fin de mission +10%"},
    {"type_contrat":"Freelance", "heures_hebdo":0, "taux_horaire_base":50.0,"jours_conge_annuels":0, "periode_essai_jours":0,  "cotisations_salariales_pct":0.0, "cotisations_patronales_pct":0.0, "notes":"Facturation à la mission"},
    {"type_contrat":"Autre",     "heures_hebdo":35,"taux_horaire_base":12.0,"jours_conge_annuels":25,"periode_essai_jours":0,  "cotisations_salariales_pct":22.0,"cotisations_patronales_pct":42.0,"notes":""},
]

# ══════════════════════════════════════════════════════════════════════════════
# R2 / STOCKAGE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_r2():
    return boto3.client("s3",
        endpoint_url=f"https://{st.secrets['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=st.secrets["R2_ACCESS_KEY"],
        aws_secret_access_key=st.secrets["R2_SECRET_KEY"],
        region_name="auto")

def load_parquet(key, cols):
    try:
        obj = get_r2().get_object(Bucket=st.secrets["R2_BUCKET"], Key=key)
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    except Exception:
        return pd.DataFrame(columns=cols)

def save_parquet(df, key):
    buf = io.BytesIO(); df.to_parquet(buf, index=False); buf.seek(0)
    get_r2().put_object(Bucket=st.secrets["R2_BUCKET"], Key=key, Body=buf.getvalue())

def next_id_safe(df, col):
    if df is None or df.empty or col not in df.columns: return 1
    return int(df[col].max()) + 1

# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ══════════════════════════════════════════════════════════════════════════════
for k in ["ressources_df","planning_df","fiches_df","params_df","_loaded"]:
    if k not in st.session_state: st.session_state[k] = None

def load_data():
    st.session_state.ressources_df = load_parquet("fiches_paie/ressources.parquet", RESSOURCES_COLS)
    st.session_state.planning_df   = load_parquet("fiches_paie/planning.parquet",   PLANNING_COLS)
    st.session_state.fiches_df     = load_parquet("fiches_paie/fiches.parquet",     FICHES_COLS)
    st.session_state.params_df     = load_parquet("fiches_paie/params.parquet",     PARAMS_COLS)
    if st.session_state.params_df.empty:
        st.session_state.params_df = pd.DataFrame(PARAMS_DEFAULT)
        try: save_parquet(st.session_state.params_df, "fiches_paie/params.parquet")
        except: pass
    for df, key in [
        (st.session_state.ressources_df, "fiches_paie/ressources.parquet"),
        (st.session_state.planning_df,   "fiches_paie/planning.parquet"),
        (st.session_state.fiches_df,     "fiches_paie/fiches.parquet"),
    ]:
        if df.empty:
            try: save_parquet(df, key)
            except: pass
    st.session_state._loaded = True

if not st.session_state._loaded:
    load_data()

def _df(val, cols_or_default):
    """Retourne val si c'est un DataFrame non-None, sinon le fallback."""
    if val is not None and isinstance(val, pd.DataFrame):
        return val
    return cols_or_default if isinstance(cols_or_default, pd.DataFrame) else pd.DataFrame(columns=cols_or_default)

rdf = _df(st.session_state.ressources_df, RESSOURCES_COLS)
pdf = _df(st.session_state.planning_df,   PLANNING_COLS)
fdf = _df(st.session_state.fiches_df,     FICHES_COLS)
pms = _df(st.session_state.params_df,     pd.DataFrame(PARAMS_DEFAULT))

TODAY = date.today()

# Types de contrat effectifs = prédéfinis + personnalisés stockés dans params
_extra = [t for t in pms["type_contrat"].tolist() if t not in TYPES_CONTRAT] if not pms.empty else []
ALL_TYPES_CONTRAT = TYPES_CONTRAT + _extra

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
PAGES = ["🏠 Dashboard","👥 Ressources","📅 Planning","💰 Fiches de Paie","⚙️ Paramètres"]
SEPS  = set()
with st.sidebar:
    st.markdown("## 💰 Gestion Paie")
    st.markdown("---")
    if "page_active" not in st.session_state:
        st.session_state.page_active = PAGES[0]
    for p in PAGES:
        if st.button(p, use_container_width=True,
                     type="primary" if st.session_state.page_active == p else "secondary"):
            st.session_state.page_active = p; st.rerun()
    st.markdown("---")
    if st.button("🔄 Recharger", use_container_width=True):
        st.session_state._loaded = False; st.rerun()
    st.markdown(f'<div style="font-size:11px;color:#4a5268;margin-top:12px">'
                f'v1.0 · {TODAY.strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)

page_active = st.session_state.page_active

# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════
def get_params(type_contrat):
    if not pms.empty and type_contrat in pms["type_contrat"].values:
        return pms[pms["type_contrat"] == type_contrat].iloc[0].to_dict()
    return next((p for p in PARAMS_DEFAULT if p["type_contrat"] == type_contrat), PARAMS_DEFAULT[0])

def hours_between(h1, h2):
    """Nombre d'heures entre deux chaînes HH:MM."""
    t1 = int(str(h1)[:2]) + int(str(h1)[3:5]) / 60
    t2 = int(str(h2)[:2]) + int(str(h2)[3:5]) / 60
    return max(0.0, t2 - t1)

def heures_contrat_mois(heures_hebdo, year, month):
    """Heures contractuelles théoriques pour un mois (jours ouvrables)."""
    nb_days = calendar.monthrange(year, month)[1]
    work_days = sum(1 for d in range(1, nb_days + 1)
                    if date(year, month, d).weekday() < 5)
    return round(float(heures_hebdo) * work_days / 5, 2)

def calc_monthly_hours(planning_df, id_ressource, year, month):
    """Calcule les heures par catégorie pour une ressource et un mois (vectorisé)."""
    res = {"travail": 0.0, "conge": 0.0, "ferie": 0.0,
           "absence": 0.0, "absence_np": 0.0, "sup": 0.0}
    if planning_df.empty: return res
    dates = pd.to_datetime(planning_df["date"])
    mask  = (
        (planning_df["id_ressource"] == id_ressource) &
        (dates.dt.year  == year) &
        (dates.dt.month == month)
    )
    sub = planning_df[mask].copy()
    if sub.empty: return res
    # Calcul vectorisé des heures
    sub["_hd"] = sub["heure_debut"].str[:2].astype(int) + sub["heure_debut"].str[3:5].astype(int) / 60
    sub["_hf"] = sub["heure_fin"].str[:2].astype(int)   + sub["heure_fin"].str[3:5].astype(int)   / 60
    sub["_h"]  = (sub["_hf"] - sub["_hd"]).clip(lower=0)
    sub["_impact"] = sub["type_heure"].map(TYPE_IMPACT).fillna("travail")
    for impact, group in sub.groupby("_impact"):
        if impact in res:
            res[impact] = group["_h"].sum()
    return res

def get_week_days(anchor):
    """Liste des jours visibles : semaine de anchor bornée par le mois."""
    week_mon = anchor - timedelta(days=anchor.weekday())
    week_sun = week_mon + timedelta(days=6)
    m_start  = anchor.replace(day=1)
    m_end    = anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
    start    = max(week_mon, m_start)
    end      = min(week_sun, m_end)
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]

def statut_badge(statut):
    COL = {"Actif":("#e6f9f0","#177049"),"Terminé":("#fde8e8","#b81c1c"),
           "Suspendu":("#fff3e8","#a86a1a"),"Brouillon":("#f0f0f0","#6870a8"),
           "Validée":("#e6f9f0","#177049"),"Envoyée":("#ddeeff","#1a6fa8")}
    bg, col = COL.get(statut, ("#f0f0f0","#555"))
    return (f'<span style="background:{bg};color:{col};padding:2px 10px;'
            f'border-radius:12px;font-size:11px;font-weight:600">{statut}</span>')

def resource_badge(nom, type_heure):
    cfg = TYPE_HEURE_CFG.get(type_heure, {"bg":"#f0f0f0","dot":"#555","lbl":type_heure})
    dot = f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{cfg["dot"]};margin-right:4px;vertical-align:middle"></span>'
    label = nom.split(" ")[0] if " " in nom else nom
    return (f'<span class="res-badge" style="background:{cfg["bg"]};color:{cfg["dot"]};'
            f'border:1px solid {cfg["dot"]}30">{dot}{label} · {cfg["lbl"]}</span>')

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page_active == "🏠 Dashboard":
    st.markdown("# 🏠 Dashboard")

    actifs    = rdf[rdf["statut_contrat"] == "Actif"] if not rdf.empty else pd.DataFrame()
    n_actifs  = len(actifs)
    n_total   = len(rdf)
    n_slots_m = 0
    if not pdf.empty:
        n_slots_m = (pd.to_datetime(pdf["date"]).dt.month == TODAY.month).sum()
    n_fiches  = len(fdf)
    n_val     = len(fdf[fdf["statut"] == "Validée"]) if not fdf.empty else 0

    st.markdown(f"""<div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Ressources actives</div>
        <div class="kpi-value">{n_actifs}</div>
        <div class="kpi-sub">sur {n_total} au total</div></div>
      <div class="kpi"><div class="kpi-label">Créneaux {MOIS_FR[TODAY.month]}</div>
        <div class="kpi-value">{n_slots_m}</div>
        <div class="kpi-sub">planifiés ce mois</div></div>
      <div class="kpi"><div class="kpi-label">Fiches de paie</div>
        <div class="kpi-value">{n_fiches}</div>
        <div class="kpi-sub">{n_val} validée(s)</div></div>
      <div class="kpi"><div class="kpi-label">Types paramétrés</div>
        <div class="kpi-value">{len(TYPES_CONTRAT)}</div>
        <div class="kpi-sub">types de contrats</div></div>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Ressources actives</div>', unsafe_allow_html=True)
        if actifs.empty:
            st.info("Aucune ressource active. Créez vos employés dans l'onglet Ressources.")
        else:
            for _, r in actifs.iterrows():
                p   = get_params(r.get("type_contrat", "CDI"))
                hhh = r.get("heures_hebdo", p["heures_hebdo"])
                taux= r.get("taux_horaire", p["taux_horaire_base"])
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:7px 0;border-bottom:1px solid #f0f1f5;font-size:13px">'
                    f'<span><b>{r["nom_ressource"]}</b> '
                    f'<span style="color:#8890a8;font-size:11px">· {r.get("type_contrat","—")}</span></span>'
                    f'<span style="color:#8890a8;font-size:12px">{hhh}h/sem · {taux}€/h</span></div>',
                    unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Répartition par type de contrat</div>', unsafe_allow_html=True)
        if not rdf.empty and "type_contrat" in rdf.columns:
            grp = rdf.groupby("type_contrat").size().sort_values(ascending=False)
            for tc, n in grp.items():
                pct = int(n / len(rdf) * 100)
                st.markdown(
                    f'<div style="margin:8px 0"><div style="display:flex;justify-content:space-between;'
                    f'font-size:13px;margin-bottom:3px"><span>{tc}</span><b>{n}</b></div>'
                    f'<div style="background:#f0f1f5;border-radius:4px;height:5px">'
                    f'<div style="width:{pct}%;background:#378add;border-radius:4px;height:5px"></div>'
                    f'</div></div>', unsafe_allow_html=True)
        else:
            st.info("Aucune ressource enregistrée.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Fiches récentes
    if not fdf.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Dernières fiches de paie</div>', unsafe_allow_html=True)
        recent = fdf.sort_values("date_generation", ascending=False).head(6)
        cols_h = st.columns([2, 1, 1, 1, 1])
        for h, lbl in zip(cols_h, ["Ressource","Mois","Brut","Net","Statut"]):
            h.markdown(f'<div style="font-size:11px;font-weight:600;color:#8890a8;'
                       f'text-transform:uppercase;border-bottom:1px solid #e8eaf0;'
                       f'padding-bottom:4px">{lbl}</div>', unsafe_allow_html=True)
        for _, f in recent.iterrows():
            c = st.columns([2, 1, 1, 1, 1])
            c[0].markdown(f'<div style="padding:5px 0;font-size:13px">{f["nom_ressource"]}</div>', unsafe_allow_html=True)
            c[1].markdown(f'<div style="padding:5px 0;font-size:12px">{MOIS_FR[int(f["mois"])]} {int(f["annee"])}</div>', unsafe_allow_html=True)
            c[2].markdown(f'<div style="padding:5px 0;font-size:12px">{f["montant_brut"]:.2f}€</div>', unsafe_allow_html=True)
            c[3].markdown(f'<div style="padding:5px 0;font-size:13px;font-weight:600">{f["montant_net"]:.2f}€</div>', unsafe_allow_html=True)
            c[4].markdown(f'<div style="padding:5px 0">{statut_badge(f["statut"])}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : RESSOURCES
# ══════════════════════════════════════════════════════════════════════════════
elif page_active == "👥 Ressources":
    st.markdown("# 👥 Ressources")
    tab_list, tab_new = st.tabs(["📋 Liste des ressources", "➕ Nouvelle ressource"])

    with tab_list:
        if rdf.empty:
            st.info("Aucune ressource. Créez vos employés dans l'onglet 'Nouvelle ressource'.")
        else:
            fc1, fc2, fc3 = st.columns(3)
            with fc1: f_tc = st.selectbox("Type contrat", ["Tous"] + ALL_TYPES_CONTRAT, key="f_tc")
            with fc2: f_st = st.selectbox("Statut", ["Tous"] + STATUTS_CONTRAT, key="f_st")
            with fc3: f_q  = st.text_input("🔍 Recherche", placeholder="Nom…", key="f_q")

            filt = rdf.copy()
            if f_tc != "Tous": filt = filt[filt["type_contrat"] == f_tc]
            if f_st != "Tous": filt = filt[filt["statut_contrat"] == f_st]
            if f_q:            filt = filt[filt["nom_ressource"].str.contains(f_q, case=False, na=False)]

            st.caption(f"{len(filt)} ressource(s) affichée(s)")
            h = st.columns([0.6, 2.2, 1.4, 0.8, 0.8, 0.9, 1, 0.4, 0.4])
            for col, lbl in zip(h, ["ID","Nom","Contrat","H/sem","Taux","Début","Statut","✏️","🗑️"]):
                col.markdown(f'<div style="font-size:11px;font-weight:600;color:#8890a8;'
                             f'text-transform:uppercase;border-bottom:1px solid #e8eaf0;'
                             f'padding-bottom:4px">{lbl}</div>', unsafe_allow_html=True)

            eid = st.session_state.get("edit_res_id")
            for _, r in filt.iterrows():
                c = st.columns([0.6, 2.2, 1.4, 0.8, 0.8, 0.9, 1, 0.4, 0.4])
                c[0].markdown(f'<div style="padding:7px 0;font-size:11px;color:#8890a8">{r["id_ressource"]}</div>', unsafe_allow_html=True)
                c[1].markdown(f'<div style="padding:7px 0;font-weight:500">{r["nom_ressource"]}</div>', unsafe_allow_html=True)
                c[2].markdown(f'<div style="padding:7px 0;font-size:12px">{r.get("type_contrat","—")}</div>', unsafe_allow_html=True)
                c[3].markdown(f'<div style="padding:7px 0;font-size:12px">{r.get("heures_hebdo","—")}h</div>', unsafe_allow_html=True)
                c[4].markdown(f'<div style="padding:7px 0;font-size:12px">{float(r.get("taux_horaire",0)):.2f}€</div>', unsafe_allow_html=True)
                dd = pd.to_datetime(r.get("date_debut"))
                c[5].markdown(f'<div style="padding:7px 0;font-size:12px">{dd.strftime("%d/%m/%Y") if pd.notna(dd) else "—"}</div>', unsafe_allow_html=True)
                c[6].markdown(f'<div style="padding:7px 0">{statut_badge(r.get("statut_contrat","Actif"))}</div>', unsafe_allow_html=True)
                with c[7]:
                    if st.button("✏️", key=f"er_{r['id_ressource']}"):
                        st.session_state.edit_res_id = r["id_ressource"]; st.rerun()
                with c[8]:
                    if st.button("🗑️", key=f"dr_{r['id_ressource']}"):
                        st.session_state.ressources_df = rdf[rdf["id_ressource"] != r["id_ressource"]]
                        try: save_parquet(st.session_state.ressources_df, "fiches_paie/ressources.parquet"); st.rerun()
                        except Exception as e: st.error(f"Erreur R2 : {e}")

            if eid:
                row = rdf[rdf["id_ressource"] == eid]
                if not row.empty:
                    r = row.iloc[0]
                    st.markdown("---")
                    st.markdown(f'<div class="section-title">Modifier — {r["nom_ressource"]}</div>', unsafe_allow_html=True)
                    with st.form("form_edit_res"):
                        e1, e2, e3 = st.columns(3)
                        with e1: en  = st.text_input("Nom", value=r["nom_ressource"])
                        with e2:
                            tc_i = ALL_TYPES_CONTRAT.index(r.get("type_contrat","CDI")) if r.get("type_contrat") in ALL_TYPES_CONTRAT else 0
                            etc  = st.selectbox("Type contrat", ALL_TYPES_CONTRAT, index=tc_i)
                        with e3:
                            st_i = STATUTS_CONTRAT.index(r.get("statut_contrat","Actif")) if r.get("statut_contrat") in STATUTS_CONTRAT else 0
                            est  = st.selectbox("Statut", STATUTS_CONTRAT, index=st_i)
                        p_def = get_params(etc)
                        e4, e5, e6 = st.columns(3)
                        with e4: ehh = st.number_input("Heures/semaine", 0.0, 60.0, float(r.get("heures_hebdo", p_def["heures_hebdo"])), 0.5)
                        with e5: eth = st.number_input("Taux horaire (€)", 0.0, value=float(r.get("taux_horaire", p_def["taux_horaire_base"])), step=0.1)
                        with e6: edd = st.date_input("Date début", pd.to_datetime(r.get("date_debut", TODAY)).date())
                        e7, e8 = st.columns(2)
                        with e7:
                            df_raw = r.get("date_fin")
                            has_df = df_raw is not None and pd.notna(df_raw)
                            edit_df_chk = st.checkbox("Date de fin prévue ?", value=has_df)
                        with e8:
                            edit_df_val = None
                            if edit_df_chk:
                                default_df = pd.to_datetime(df_raw).date() if has_df else TODAY + timedelta(days=365)
                                edit_df_val = st.date_input("Date de fin", default_df)
                        en2 = st.text_input("Notes", value=r.get("notes","") or "")
                        s1, s2 = st.columns(2)
                        with s1:
                            if st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True):
                                idx = st.session_state.ressources_df[st.session_state.ressources_df["id_ressource"] == eid].index
                                for col, val in [("nom_ressource",en),("type_contrat",etc),("statut_contrat",est),
                                                 ("heures_hebdo",ehh),("taux_horaire",eth),
                                                 ("date_debut",pd.Timestamp(edd)),
                                                 ("date_fin", pd.Timestamp(edit_df_val) if edit_df_val else None),
                                                 ("notes",en2)]:
                                    st.session_state.ressources_df.loc[idx, col] = val
                                try:
                                    save_parquet(st.session_state.ressources_df, "fiches_paie/ressources.parquet")
                                    st.session_state.pop("edit_res_id", None); st.success("Enregistré."); st.rerun()
                                except Exception as e: st.error(f"Erreur R2 : {e}")
                        with s2:
                            if st.form_submit_button("✖ Annuler", use_container_width=True):
                                st.session_state.pop("edit_res_id", None); st.rerun()

    with tab_new:
        st.info("ℹ️ Les valeurs par défaut sont pré-remplies selon le type de contrat sélectionné (paramétrable dans ⚙️ Paramètres).")
        tc_sel = st.selectbox("Type de contrat *", ALL_TYPES_CONTRAT, key="new_tc")
        p_def  = get_params(tc_sel)
        with st.form("form_new_res", clear_on_submit=True):
            st.markdown('<div class="section-title">Identité</div>', unsafe_allow_html=True)
            n1, n2 = st.columns(2)
            with n1: n_id  = st.text_input("ID Ressource *", placeholder="Ex: EMP-001")
            with n2: n_nom = st.text_input("Nom complet *",  placeholder="Ex: Jean Dupont")

            st.markdown('<div class="section-title">Paramètres contrat</div>', unsafe_allow_html=True)
            p1, p2, p3 = st.columns(3)
            with p1: n_hh = st.number_input("Heures/semaine", 0.0, 60.0, float(p_def["heures_hebdo"]), 0.5)
            with p2: n_th = st.number_input("Taux horaire (€)", 0.0, value=float(p_def["taux_horaire_base"]), step=0.1)
            with p3: n_st = st.selectbox("Statut", STATUTS_CONTRAT)

            st.markdown('<div class="section-title">Dates</div>', unsafe_allow_html=True)
            d1, d2 = st.columns(2)
            with d1: n_dd = st.date_input("Date de début *", TODAY)
            with d2: chk  = st.checkbox("Date de fin prévue ?")
            n_df = None
            if chk: n_df = st.date_input("Date de fin", TODAY + timedelta(days=365))
            n_notes = st.text_input("Notes", placeholder="Informations complémentaires")

            if st.form_submit_button("✅ Créer la ressource", type="primary", use_container_width=True):
                if not n_id or not n_nom:
                    st.error("L'ID et le nom sont obligatoires.")
                elif not rdf.empty and n_id in rdf["id_ressource"].values:
                    st.error(f"L'ID «{n_id}» existe déjà.")
                else:
                    new_r = {"id_ressource":n_id,"nom_ressource":n_nom,"type_contrat":tc_sel,
                             "heures_hebdo":n_hh,"taux_horaire":n_th,
                             "date_debut":pd.Timestamp(n_dd),
                             "date_fin":pd.Timestamp(n_df) if n_df else None,
                             "statut_contrat":n_st,"notes":n_notes,
                             "date_creation":pd.Timestamp(datetime.now())}
                    st.session_state.ressources_df = pd.concat(
                        [rdf, pd.DataFrame([new_r])], ignore_index=True)
                    try:
                        save_parquet(st.session_state.ressources_df, "fiches_paie/ressources.parquet")
                        st.success(f"✅ Ressource «{n_nom}» créée !"); st.balloons(); st.rerun()
                    except Exception as e: st.error(f"Erreur R2 : {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : PLANNING
# ══════════════════════════════════════════════════════════════════════════════
elif page_active == "📅 Planning":
    st.markdown("# 📅 Planning")

    # ── CSS calendrier interactif ─────────────────────────────────────────────
    st.markdown("""<style>
    .cal-hdr{background:#0f1117;color:#e0e4f0;text-align:center;padding:7px 3px;
             font-size:12px;font-weight:600;border-radius:6px;line-height:1.4;}
    .cal-hdr-we{color:#6870a8!important;background:#1a1d2e!important;}
    .cal-hdr-today{color:#cce0ff!important;background:#2a4a80!important;}
    .cal-time{color:#8890a8;font-size:9px;font-family:'DM Mono',monospace;
              text-align:center;padding:3px 1px;line-height:1.3;}
    .cal-cell{min-height:46px;padding:2px 3px;border:1px solid #e8eaf0;
              border-radius:5px;margin:1px 0;background:#fff;}
    .cal-cell-we{background:#f9fafb!important;}
    .cal-cell-today{background:#fffbf0!important;border-color:#f0c850!important;}
    /* Boutons ultra-compacts dans la grille */
    div[data-testid="stHorizontalBlock"] div[data-testid="stButton"]>button{
        padding:0px 2px!important;font-size:9px!important;
        height:16px!important;min-height:0!important;
        border-radius:3px!important;line-height:1!important;
    }
    </style>""", unsafe_allow_html=True)

    # ── Dialog de gestion des créneaux ────────────────────────────────────────
    @st.dialog("📅 Gérer le créneau")
    def slot_dialog(d, t_slot):
        slot_h = int(t_slot[:2])
        h_next = f"{slot_h+1:02d}:00"

        # En-tête 1 ligne
        flag = " 📌" if d == TODAY else (" 🌅" if d.weekday() >= 5 else "")
        st.markdown(
            f'<span style="font-size:15px;font-weight:700">'
            f'{JOURS_FR[d.weekday()]} {d.strftime("%d/%m/%Y")}{flag}</span>'
            f'<span style="font-size:11px;color:#8890a8;margin-left:8px">'
            f'🕐 {t_slot} → {h_next}</span>',
            unsafe_allow_html=True)
        st.markdown("<hr style='margin:8px 0 10px;border-color:#e8eaf0'>",
                    unsafe_allow_html=True)

        # Données fraîches
        cur_pdf = _df(st.session_state.planning_df, PLANNING_COLS)
        cur_rdf = _df(st.session_state.ressources_df, RESSOURCES_COLS)

        # Slots couvrant cet horaire
        slots_here = []
        if not cur_pdf.empty:
            tmp = cur_pdf.copy()
            tmp["_dt"] = pd.to_datetime(tmp["date"]).dt.date
            for _, row in tmp[tmp["_dt"] == d].iterrows():
                try:
                    if int(str(row["heure_debut"])[:2]) <= slot_h < int(str(row["heure_fin"])[:2]):
                        slots_here.append(row.to_dict())
                except Exception:
                    continue

        # ── Slots existants ───────────────────────────────────────────────────
        if slots_here:
            for slot in slots_here:
                s_id     = slot["id_slot"]
                cur_type = slot.get("type_heure", "Travail")
                hd_h     = int(str(slot["heure_debut"])[:2])
                hf_h     = int(str(slot["heure_fin"])[:2])
                cfg      = TYPE_HEURE_CFG.get(cur_type, {"bg":"#f0f0f0","dot":"#555"})

                # Ligne résumé: nom + horaire + badge + delete
                rc1, rc2 = st.columns([3.5, 0.5])
                rc1.markdown(
                    f'<div style="padding:3px 0">'
                    f'<b style="font-size:13px">{slot["nom_ressource"]}</b>'
                    f'<span style="font-size:11px;color:#8890a8;margin:0 6px">'
                    f'{slot["heure_debut"]}→{slot["heure_fin"]}</span>'
                    f'<span style="background:{cfg["bg"]};color:{cfg["dot"]};'
                    f'padding:1px 6px;border-radius:8px;font-size:10px;font-weight:500">'
                    f'{cur_type}</span></div>',
                    unsafe_allow_html=True)
                with rc2:
                    if st.button("🗑️", key=f"del_{s_id}_{slot_h}"):
                        st.session_state.planning_df = st.session_state.planning_df[
                            st.session_state.planning_df["id_slot"] != s_id]
                        try:
                            save_parquet(st.session_state.planning_df, "fiches_paie/planning.parquet")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                # Changement de type : immédiat + auto-split si nécessaire
                tp_idx   = TYPES_HEURE.index(cur_type) if cur_type in TYPES_HEURE else 0
                new_type = st.selectbox(
                    "Type d'heure", TYPES_HEURE, index=tp_idx,
                    key=f"tp_{s_id}_{slot_h}",
                    label_visibility="collapsed")

                if new_type != cur_type:
                    pidx = st.session_state.planning_df[
                        st.session_state.planning_df["id_slot"] == s_id].index
                    # Auto-split si on est en milieu de créneau (pas à la frontière)
                    if slot_h > hd_h and hf_h > slot_h + 1:
                        # Tronquer le slot existant jusqu'à t_slot
                        st.session_state.planning_df.loc[pidx, "heure_fin"] = t_slot
                        # Créer un nouveau slot de t_slot à hf avec le nouveau type
                        new_s = {
                            "id_slot":       next_id_safe(st.session_state.planning_df, "id_slot"),
                            "date":          pd.Timestamp(d),
                            "heure_debut":   t_slot,
                            "heure_fin":     slot["heure_fin"],
                            "id_ressource":  slot["id_ressource"],
                            "nom_ressource": slot["nom_ressource"],
                            "type_heure":    new_type,
                            "notes":         slot.get("notes", ""),
                            "date_creation": pd.Timestamp(datetime.now()),
                        }
                        st.session_state.planning_df = pd.concat(
                            [st.session_state.planning_df, pd.DataFrame([new_s])],
                            ignore_index=True)
                    else:
                        # Frontière ou créneau d'1h : changer tout le slot
                        st.session_state.planning_df.loc[pidx, "type_heure"] = new_type
                    try:
                        save_parquet(st.session_state.planning_df, "fiches_paie/planning.parquet")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

                # Modifier les horaires du slot (form compact 1 ligne)
                with st.form(f"hrs_{s_id}"):
                    hd_idx = HEURES[:-1].index(slot["heure_debut"]) \
                             if slot["heure_debut"] in HEURES[:-1] else 1
                    hf_idx = HEURES[1:].index(slot["heure_fin"]) \
                             if slot["heure_fin"] in HEURES[1:] else 9
                    fh1, fh2, fh3 = st.columns([2, 2, 1])
                    with fh1:
                        new_hd = st.selectbox("Début", HEURES[:-1], index=hd_idx,
                                              key=f"hd_{s_id}", label_visibility="collapsed")
                    with fh2:
                        new_hf = st.selectbox("Fin",   HEURES[1:],  index=hf_idx,
                                              key=f"hf_{s_id}", label_visibility="collapsed")
                    with fh3:
                        save_h = st.form_submit_button("⏱ Horaires", use_container_width=True)
                    if save_h:
                        if HEURES.index(new_hf) <= HEURES.index(new_hd):
                            st.error("Fin > Début.")
                        else:
                            pidx2 = st.session_state.planning_df[
                                st.session_state.planning_df["id_slot"] == s_id].index
                            st.session_state.planning_df.loc[pidx2, "heure_debut"] = new_hd
                            st.session_state.planning_df.loc[pidx2, "heure_fin"]   = new_hf
                            try:
                                save_parquet(st.session_state.planning_df,
                                             "fiches_paie/planning.parquet")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                st.markdown("<hr style='margin:6px 0;border-color:#f0f1f5'>",
                            unsafe_allow_html=True)
        else:
            st.caption("Ce créneau est libre.")

        # ── Ajouter une ressource ─────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            'color:#8890a8;letter-spacing:.06em;margin:4px 0 8px">➕ Ajouter</div>',
            unsafe_allow_html=True)

        if cur_rdf.empty:
            st.warning("Aucune ressource disponible.")
        else:
            res_list = (cur_rdf[cur_rdf["statut_contrat"] == "Actif"]["nom_ressource"].tolist()
                        or cur_rdf["nom_ressource"].tolist())
            with st.form("dlg_add"):
                a1, a2 = st.columns(2)
                with a1:
                    add_res  = st.selectbox("Ressource *", res_list)
                    add_type = st.selectbox("Type *", TYPES_HEURE)
                with a2:
                    hd_def = HEURES.index("08:00") if "08:00" in HEURES else 1
                    hf_def = HEURES[1:].index("17:00") if "17:00" in HEURES[1:] else 9
                    add_hd = st.selectbox("Début", HEURES[:-1], index=hd_def)
                    add_hf = st.selectbox("Fin",   HEURES[1:],  index=hf_def)
                if st.form_submit_button("✅ Ajouter", type="primary",
                                         use_container_width=True):
                    if HEURES.index(add_hf) <= HEURES.index(add_hd):
                        st.error("Fin > Début.")
                    else:
                        rrow = cur_rdf[cur_rdf["nom_ressource"] == add_res].iloc[0]
                        new_slot = {
                            "id_slot":       next_id_safe(cur_pdf, "id_slot"),
                            "date":          pd.Timestamp(d),
                            "heure_debut":   add_hd,
                            "heure_fin":     add_hf,
                            "id_ressource":  rrow["id_ressource"],
                            "nom_ressource": add_res,
                            "type_heure":    add_type,
                            "notes":         "",
                            "date_creation": pd.Timestamp(datetime.now()),
                        }
                        st.session_state.planning_df = pd.concat(
                            [cur_pdf, pd.DataFrame([new_slot])], ignore_index=True)
                        try:
                            save_parquet(st.session_state.planning_df,
                                         "fiches_paie/planning.parquet")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    # ── Navigation mois / semaine ─────────────────────────────────────────────
    if "plan_anchor" not in st.session_state:
        st.session_state.plan_anchor = TODAY
    anchor = st.session_state.plan_anchor

    nav1, nav2, nav3, nav4, nav5 = st.columns([1.1, 1.1, 2.8, 1.1, 1.1])
    with nav1:
        if st.button("◀◀ Mois préc.", use_container_width=True):
            m, y = (12, anchor.year - 1) if anchor.month == 1 else (anchor.month - 1, anchor.year)
            st.session_state.plan_anchor = date(y, m, 1); st.rerun()
    with nav2:
        if st.button("◀ Sem. préc.", use_container_width=True):
            wmon     = anchor - timedelta(days=anchor.weekday())
            m_start  = anchor.replace(day=1)
            if wmon <= m_start:  # Déjà à la 1ère sem → mois précédent
                m2, y2 = (12, anchor.year - 1) if anchor.month == 1 else (anchor.month - 1, anchor.year)
                last_d = calendar.monthrange(y2, m2)[1]
                st.session_state.plan_anchor = date(y2, m2, last_d)
            else:
                new_mon = wmon - timedelta(days=7)
                st.session_state.plan_anchor = max(new_mon, m_start)
            st.rerun()
    with nav3:
        st.markdown(f'<div style="text-align:center;font-size:20px;font-weight:700;padding:4px 0">'
                    f'{MOIS_FR[anchor.month]} {anchor.year}</div>', unsafe_allow_html=True)
    with nav4:
        if st.button("Sem. suiv. ▶", use_container_width=True):
            m_end    = anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
            wdays    = get_week_days(anchor)
            if wdays[-1] >= m_end:  # Dernière sem → mois suivant
                m2, y2 = (1, anchor.year + 1) if anchor.month == 12 else (anchor.month + 1, anchor.year)
                st.session_state.plan_anchor = date(y2, m2, 1)
            else:
                wmon = anchor - timedelta(days=anchor.weekday())
                st.session_state.plan_anchor = wmon + timedelta(days=7)
            st.rerun()
    with nav5:
        if st.button("Mois suiv. ▶▶", use_container_width=True):
            m2, y2 = (1, anchor.year + 1) if anchor.month == 12 else (anchor.month + 1, anchor.year)
            st.session_state.plan_anchor = date(y2, m2, 1); st.rerun()

    week_days = get_week_days(anchor)
    week_set  = set(week_days)
    st.caption(
        f"📅 Semaine du **{week_days[0].strftime('%d %b')}** au **{week_days[-1].strftime('%d %b %Y')}** "
        f"· {len(week_days)} jour(s) affiché(s)"
        + (" · ⚠️ Semaine partielle (fin de mois)" if len(week_days) < 7 else "")
    )

    # ── Construction du slot_lookup ────────────────────────────────────────────
    slot_lookup = {}  # (date, "HH:00") → list[dict]
    if not pdf.empty:
        tmp = pdf.copy()
        tmp["_dt"] = pd.to_datetime(tmp["date"]).dt.date
        for _, row in tmp[tmp["_dt"].isin(week_set)].iterrows():
            try:
                hd = int(str(row["heure_debut"])[:2])
                hf = int(str(row["heure_fin"])[:2])
            except Exception:
                continue
            for h in range(hd, hf):
                key = (row["_dt"], f"{h:02d}:00")
                if key not in slot_lookup:
                    slot_lookup[key] = []
                slot_lookup[key].append({
                    "id_slot": row["id_slot"],
                    "nom":     row["nom_ressource"],
                    "type":    row["type_heure"],
                    "hd":      row["heure_debut"],
                    "hf":      row["heure_fin"],
                })

    # ── Grille calendrier interactive ────────────────────────────────────────
    n_days = len(week_days)
    ratio  = [0.42] + [1.0] * n_days

    # En-tête des jours
    hcols = st.columns(ratio)
    hcols[0].markdown('<div style="font-size:9px;color:#8890a8;text-align:center;'
                      'padding:7px 0">Créneau</div>', unsafe_allow_html=True)
    for i, d in enumerate(week_days):
        is_we    = d.weekday() >= 5
        is_today = d == TODAY
        cls  = "cal-hdr-today" if is_today else ("cal-hdr-we" if is_we else "")
        today_dot = "<br><small>●</small>" if is_today else ""
        hcols[i+1].markdown(
            f'<div class="cal-hdr {cls}">{JOURS_FR[d.weekday()]}<br>{d.day:02d}{today_dot}</div>',
            unsafe_allow_html=True)

    # Lignes horaires
    for t_slot in TIME_SLOTS:
        h_next = f"{int(t_slot[:2])+1:02d}:00"
        row = st.columns(ratio)
        with row[0]:
            st.markdown(f'<div class="cal-time">{t_slot}<br>↓<br>{h_next}</div>',
                        unsafe_allow_html=True)
        for i, d in enumerate(week_days):
            slots    = slot_lookup.get((d, t_slot), [])
            is_we    = d.weekday() >= 5
            is_today = d == TODAY
            cls_cell = "cal-cell-today" if is_today else ("cal-cell-we" if is_we else "")
            with row[i+1]:
                seen = set()
                badges_html = ""
                for s in slots:
                    if s["id_slot"] in seen: continue
                    seen.add(s["id_slot"])
                    badges_html += resource_badge(s["nom"], s["type"])
                n_unique = len(seen)
                st.markdown(
                    f'<div class="cal-cell {cls_cell}">{badges_html}</div>',
                    unsafe_allow_html=True)
                btn_lbl  = "＋" if n_unique == 0 else f"✎{n_unique}"
                btn_type = "secondary" if n_unique == 0 else "primary"
                if st.button(btn_lbl, key=f"c_{d}_{t_slot}", type=btn_type,
                             use_container_width=True,
                             help=f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m')} · "
                                  f"{t_slot}→{h_next} · {n_unique} ressource(s)"):
                    slot_dialog(d, t_slot)

    # ── Légende ───────────────────────────────────────────────────────────────
    leg_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 16px">'
    for th, cfg in TYPE_HEURE_CFG.items():
        leg_html += (f'<span style="background:{cfg["bg"]};color:{cfg["dot"]};'
                     f'border:1px solid {cfg["dot"]}30;padding:2px 9px;border-radius:10px;'
                     f'font-size:11px;font-weight:500">● {th}</span>')
    leg_html += "</div>"
    st.markdown(leg_html, unsafe_allow_html=True)

    # ── Récapitulatif mensuel ─────────────────────────────────────────────────
    st.markdown("---")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-title">Récapitulatif {MOIS_FR[anchor.month]} {anchor.year}</div>',
            unsafe_allow_html=True)

        if rdf.empty:
            st.info("Aucune ressource.")
        else:
            actives = rdf[rdf["statut_contrat"] == "Actif"] if not rdf.empty else rdf
            for _, r in actives.iterrows():
                hrs      = calc_monthly_hours(pdf, r["id_ressource"], anchor.year, anchor.month)
                p        = get_params(r.get("type_contrat", "CDI"))
                h_ctr    = heures_contrat_mois(r.get("heures_hebdo", p["heures_hebdo"]),
                                               anchor.year, anchor.month)
                h_trav   = hrs["travail"]
                h_sup_eff= max(0.0, h_trav - h_ctr)
                h_tot    = h_trav + hrs["conge"] + hrs["ferie"] + hrs["absence"] + hrs["absence_np"] + hrs["sup"]

                st.markdown(
                    f'<div style="margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid #e8eaf0">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:6px">'
                    f'<span style="font-weight:600;font-size:13px">{r["nom_ressource"]}</span>'
                    f'<span style="font-size:11px;color:#8890a8">{r.get("type_contrat","—")}</span></div>'
                    f'<div style="font-size:12px;color:#6870a8;margin-bottom:6px">'
                    f'Contrat : <b>{h_ctr:.1f}h</b> · Planifié : <b>{h_tot:.1f}h</b></div>'
                    f'<div style="display:flex;gap:4px;flex-wrap:wrap">',
                    unsafe_allow_html=True)

                badges = []
                if h_trav > 0:
                    badges.append(f'<span style="background:#e6f9f0;color:#177049;padding:2px 8px;border-radius:10px;font-size:11px">✅ {h_trav:.1f}h travail</span>')
                if hrs["conge"] > 0:
                    badges.append(f'<span style="background:#ddeeff;color:#1a6fa8;padding:2px 8px;border-radius:10px;font-size:11px">🌴 {hrs["conge"]:.1f}h congé</span>')
                if hrs["ferie"] > 0:
                    badges.append(f'<span style="background:#fff3e8;color:#a86a1a;padding:2px 8px;border-radius:10px;font-size:11px">🏛️ {hrs["ferie"]:.1f}h férié</span>')
                if hrs["absence"] + hrs["absence_np"] > 0:
                    tot_abs = hrs["absence"] + hrs["absence_np"]
                    badges.append(f'<span style="background:#fde8e8;color:#b81c1c;padding:2px 8px;border-radius:10px;font-size:11px">🤒 {tot_abs:.1f}h absence</span>')
                # N'afficher qu'un seul badge heures sup : les heures sup calculées OU déclarées
                h_sup_display = h_sup_eff if h_sup_eff > 0 else hrs["sup"]
                if h_sup_display > 0:
                    lbl_sup = "sup calculées" if h_sup_eff > 0 else "sup déclarées"
                    badges.append(f'<span style="background:#fde8f9;color:#a81a7a;padding:2px 8px;border-radius:10px;font-size:11px">⏱️ {h_sup_display:.1f}h {lbl_sup}</span>')
                if not badges:
                    badges.append('<span style="color:#8890a8;font-size:11px;font-style:italic">Aucun créneau ce mois</span>')

                st.markdown(" ".join(badges) + '</div></div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : FICHES DE PAIE
# ══════════════════════════════════════════════════════════════════════════════
elif page_active == "💰 Fiches de Paie":
    st.markdown("# 💰 Fiches de Paie")

    tab_gen, tab_hist = st.tabs(["📄 Générer une fiche", "📋 Historique"])

    with tab_gen:
        if rdf.empty:
            st.warning("Aucune ressource disponible. Créez des ressources dans l'onglet Ressources.")
        else:
            col_f, col_p = st.columns([1, 1.6])

            with col_f:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">Paramètres</div>', unsafe_allow_html=True)

                res_opts = rdf["nom_ressource"].tolist()
                sel_res  = st.selectbox("Ressource *", res_opts, key="fiche_res")
                sel_mois = st.selectbox("Mois *", list(range(1, 13)),
                                        format_func=lambda m: MOIS_FR[m],
                                        index=(TODAY.month - 2) % 12, key="fiche_mois")
                sel_annee= st.number_input("Année *", 2020, 2035, TODAY.year, key="fiche_an")

                res_row = rdf[rdf["nom_ressource"] == sel_res].iloc[0]
                p       = get_params(res_row.get("type_contrat", "CDI"))

                st.markdown('<div class="section-title" style="margin-top:16px">Calcul</div>', unsafe_allow_html=True)
                g1, g2 = st.columns(2)
                with g1:
                    h_hebdo = st.number_input("H contrat/sem", 0.0, 60.0, float(res_row.get("heures_hebdo", p["heures_hebdo"])), 0.5)
                    taux_h  = st.number_input("Taux horaire (€)", 0.0, value=float(res_row.get("taux_horaire", p["taux_horaire_base"])), step=0.1)
                with g2:
                    cotis_s = st.number_input("Cotis. salariales %", 0.0, 60.0, float(p["cotisations_salariales_pct"]), 0.1)
                    maj_pct = st.number_input("Majoration H.sup % (≤8h)", 0.0, 100.0, 25.0, 1.0)

                # ── Calculs ────────────────────────────────────────────────────
                hrs      = calc_monthly_hours(pdf, res_row["id_ressource"], int(sel_annee), sel_mois)
                h_ctr    = heures_contrat_mois(h_hebdo, int(sel_annee), sel_mois)
                h_trav   = hrs["travail"] + hrs["sup"]  # travail effectif total
                h_sup    = max(0.0, h_trav - h_ctr)
                h_sup_25 = min(h_sup, 8.0)
                h_sup_50 = max(0.0, h_sup - 8.0)

                # Absences non justifiées → déduction
                abs_nj_h = hrs["absence_np"]

                sal_base = h_ctr    * taux_h
                maj_25   = h_sup_25 * taux_h * (maj_pct / 100)
                maj_50   = h_sup_50 * taux_h * 0.50
                ded_abs  = abs_nj_h * taux_h
                brut     = sal_base + maj_25 + maj_50 - ded_abs
                cotis_m  = brut * (cotis_s / 100)
                net      = brut - cotis_m

                st.markdown('</div>', unsafe_allow_html=True)

                # ── Vérif doublon ──────────────────────────────────────────────
                fiche_existante = None
                if not fdf.empty:
                    dup = fdf[
                        (fdf["id_ressource"] == res_row["id_ressource"]) &
                        (fdf["mois"]  == sel_mois) &
                        (fdf["annee"] == int(sel_annee))
                    ]
                    if not dup.empty:
                        fiche_existante = dup.iloc[0]
                        st.warning(
                            f"⚠️ Une fiche existe déjà pour **{sel_res}** · "
                            f"**{MOIS_FR[sel_mois]} {int(sel_annee)}** "
                            f"(#{int(fiche_existante['id_fiche'])} · {fiche_existante['statut']}). "
                            "Enregistrer créera une fiche supplémentaire."
                        )

                if st.button("💾 Enregistrer la fiche de paie", type="primary", use_container_width=True):
                    new_f = {
                        "id_fiche":       next_id_safe(fdf, "id_fiche"),
                        "id_ressource":   res_row["id_ressource"],
                        "nom_ressource":  sel_res,
                        "mois":           sel_mois,
                        "annee":          int(sel_annee),
                        "heures_contrat": round(h_ctr, 2),
                        "heures_travail": round(h_trav, 2),
                        "heures_conge":   round(hrs["conge"] + hrs["ferie"], 2),
                        "heures_maladie": round(hrs["absence"] + hrs["absence_np"], 2),
                        "heures_sup":     round(h_sup, 2),
                        "heures_autres":  0.0,
                        "montant_brut":   round(brut, 2),
                        "montant_net":    round(net, 2),
                        "statut":         "Brouillon",
                        "date_generation":pd.Timestamp(datetime.now()),
                    }
                    st.session_state.fiches_df = pd.concat(
                        [fdf, pd.DataFrame([new_f])], ignore_index=True)
                    try:
                        save_parquet(st.session_state.fiches_df, "fiches_paie/fiches.parquet")
                        st.success("✅ Fiche enregistrée !"); st.rerun()
                    except Exception as e: st.error(f"Erreur R2 : {e}")

            # ── Aperçu fiche de paie ────────────────────────────────────────
            with col_p:
                st.markdown('<div class="fiche-wrap">', unsafe_allow_html=True)
                # En-tête
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">'
                    f'<div><div class="fiche-titre">BULLETIN DE PAIE</div>'
                    f'<div class="fiche-soustitre">{MOIS_FR[sel_mois]} {int(sel_annee)}</div></div>'
                    f'<div style="text-align:right">'
                    f'<div style="font-weight:700;font-size:15px">{sel_res}</div>'
                    f'<div style="font-size:12px;color:#8890a8">{res_row.get("type_contrat","—")} · {res_row["id_ressource"]}</div>'
                    f'<div style="font-size:12px;color:#8890a8">Depuis : '
                    f'{pd.to_datetime(res_row.get("date_debut","")).strftime("%d/%m/%Y") if pd.notna(res_row.get("date_debut")) else "—"}'
                    f'</div></div></div>', unsafe_allow_html=True)
                st.markdown('<hr class="fiche-sep-bold">', unsafe_allow_html=True)

                # Heures
                st.markdown('<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                            'color:#8890a8;margin-bottom:6px">Détail des heures</div>', unsafe_allow_html=True)
                def frow(label, val, neg=False):
                    cls = " fiche-row-neg" if neg else ""
                    st.markdown(f'<div class="fiche-row{cls}"><span>{label}</span><span>{val}</span></div>',
                                unsafe_allow_html=True)

                frow(f"Heures contractuelles ({h_hebdo:.0f}h/sem)", f"{h_ctr:.2f}h")
                if h_trav > 0:       frow("Heures travaillées",              f"{h_trav:.2f}h")
                if hrs["conge"] > 0: frow("Congés payés / RTT",              f"{hrs['conge']:.2f}h")
                if hrs["ferie"] > 0: frow("Jours fériés",                    f"{hrs['ferie']:.2f}h")
                if hrs["absence"] > 0: frow("Absences justifiées",           f"{hrs['absence']:.2f}h")
                if abs_nj_h > 0:     frow("Absences non justifiées",         f"{abs_nj_h:.2f}h", neg=True)
                if h_sup > 0:        frow("Heures supplémentaires",          f"{h_sup:.2f}h")

                st.markdown('<hr class="fiche-sep">', unsafe_allow_html=True)

                # Rémunération
                st.markdown('<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                            'color:#8890a8;margin-bottom:6px">Rémunération brute</div>', unsafe_allow_html=True)
                frow(f"Salaire de base  ({h_ctr:.1f}h × {taux_h:.2f}€)", f"{sal_base:.2f} €")
                if h_sup_25 > 0:
                    frow(f"H.sup +{maj_pct:.0f}%  ({h_sup_25:.1f}h × {taux_h:.2f}€ × {maj_pct:.0f}%)", f"+{maj_25:.2f} €")
                if h_sup_50 > 0:
                    frow(f"H.sup +50%  ({h_sup_50:.1f}h)", f"+{maj_50:.2f} €")
                if ded_abs > 0:
                    frow(f"Déduction absences NJ  ({abs_nj_h:.1f}h)", f"−{ded_abs:.2f} €", neg=True)

                st.markdown(f'<div class="fiche-row" style="font-weight:700;border-top:1px solid #e0e0e0;'
                            f'margin-top:4px;padding-top:8px"><span>Total brut</span>'
                            f'<span>{brut:.2f} €</span></div>', unsafe_allow_html=True)

                st.markdown('<hr class="fiche-sep">', unsafe_allow_html=True)

                # Cotisations
                st.markdown('<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                            'color:#8890a8;margin-bottom:6px">Cotisations salariales</div>', unsafe_allow_html=True)
                frow(f"Cotisations salariales  ({cotis_s:.1f}%)", f"−{cotis_m:.2f} €", neg=True)

                st.markdown('<hr class="fiche-sep-bold">', unsafe_allow_html=True)
                st.markdown(f'<div class="fiche-total"><span>NET À PAYER</span>'
                            f'<span style="color:#177049;font-size:20px">{net:.2f} €</span></div>',
                            unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # ── Historique ─────────────────────────────────────────────────────────────
    with tab_hist:
        if fdf.empty:
            st.info("Aucune fiche de paie générée pour le moment.")
        else:
            hf1, hf2, hf3 = st.columns(3)
            with hf1: hf_r = st.selectbox("Ressource", ["Toutes"] + fdf["nom_ressource"].unique().tolist(), key="hfr")
            with hf2: hf_m = st.selectbox("Mois", ["Tous"] + [MOIS_FR[m] for m in range(1,13)], key="hfm")
            with hf3: hf_s = st.selectbox("Statut", ["Tous"] + STATUTS_FICHE, key="hfs")

            f2 = fdf.copy()
            if hf_r != "Toutes": f2 = f2[f2["nom_ressource"] == hf_r]
            if hf_m != "Tous":   f2 = f2[f2["mois"].apply(lambda m: MOIS_FR[int(m)]) == hf_m]
            if hf_s != "Tous":   f2 = f2[f2["statut"] == hf_s]

            st.caption(f"{len(f2)} fiche(s)")

            # Tableau récap
            th = st.columns([0.4, 1.8, 1, 0.8, 0.8, 0.8, 0.8, 1, 0.5, 0.5])
            for col, lbl in zip(th, ["#","Ressource","Période","H.ctr","H.trav","Brut","Net","Statut","✏️","🗑️"]):
                col.markdown(f'<div style="font-size:11px;font-weight:600;color:#8890a8;'
                             f'text-transform:uppercase;border-bottom:1px solid #e8eaf0;'
                             f'padding-bottom:4px">{lbl}</div>', unsafe_allow_html=True)

            for _, f in f2.sort_values(["annee","mois"], ascending=False).iterrows():
                c = st.columns([0.4, 1.8, 1, 0.8, 0.8, 0.8, 0.8, 1, 0.5, 0.5])
                c[0].markdown(f'<div style="padding:6px 0;font-size:12px;color:#8890a8">#{int(f["id_fiche"])}</div>', unsafe_allow_html=True)
                c[1].markdown(f'<div style="padding:6px 0;font-weight:500">{f["nom_ressource"]}</div>', unsafe_allow_html=True)
                c[2].markdown(f'<div style="padding:6px 0;font-size:12px">{MOIS_FR[int(f["mois"])]} {int(f["annee"])}</div>', unsafe_allow_html=True)
                c[3].markdown(f'<div style="padding:6px 0;font-size:12px">{f["heures_contrat"]:.1f}h</div>', unsafe_allow_html=True)
                c[4].markdown(f'<div style="padding:6px 0;font-size:12px">{f["heures_travail"]:.1f}h</div>', unsafe_allow_html=True)
                c[5].markdown(f'<div style="padding:6px 0;font-size:12px">{f["montant_brut"]:.2f}€</div>', unsafe_allow_html=True)
                c[6].markdown(f'<div style="padding:6px 0;font-weight:600">{f["montant_net"]:.2f}€</div>', unsafe_allow_html=True)
                c[7].markdown(f'<div style="padding:6px 0">{statut_badge(f["statut"])}</div>', unsafe_allow_html=True)
                with c[8]:
                    if st.button("✏️", key=f"fmod_{f['id_fiche']}"):
                        st.session_state[f"edit_fiche_{f['id_fiche']}"] = True; st.rerun()
                with c[9]:
                    if st.button("🗑️", key=f"fdel_{f['id_fiche']}"):
                        st.session_state.fiches_df = fdf[fdf["id_fiche"] != f["id_fiche"]]
                        try: save_parquet(st.session_state.fiches_df, "fiches_paie/fiches.parquet"); st.rerun()
                        except Exception as e: st.error(f"Erreur R2 : {e}")

                # Inline statut edit
                if st.session_state.get(f"edit_fiche_{f['id_fiche']}"):
                    with st.form(f"fform_{f['id_fiche']}"):
                        new_st = st.selectbox("Nouveau statut", STATUTS_FICHE,
                                              index=STATUTS_FICHE.index(f["statut"]) if f["statut"] in STATUTS_FICHE else 0)
                        fs1, fs2 = st.columns(2)
                        with fs1:
                            if st.form_submit_button("💾 Mettre à jour", type="primary"):
                                idx = st.session_state.fiches_df[st.session_state.fiches_df["id_fiche"] == f["id_fiche"]].index
                                st.session_state.fiches_df.loc[idx, "statut"] = new_st
                                try:
                                    save_parquet(st.session_state.fiches_df, "fiches_paie/fiches.parquet")
                                    st.session_state.pop(f"edit_fiche_{f['id_fiche']}", None); st.rerun()
                                except Exception as e: st.error(f"Erreur R2 : {e}")
                        with fs2:
                            if st.form_submit_button("✖ Annuler"):
                                st.session_state.pop(f"edit_fiche_{f['id_fiche']}", None); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : PARAMÈTRES
# ══════════════════════════════════════════════════════════════════════════════
elif page_active == "⚙️ Paramètres":
    st.markdown("# ⚙️ Paramètres")
    st.caption("Modifiez les paramètres par défaut de chaque type de contrat. "
               "Ces valeurs pré-remplissent automatiquement les formulaires de création.")

    defined_types = set(TYPES_CONTRAT)
    all_params    = pms if not pms.empty else pd.DataFrame(PARAMS_DEFAULT)

    def _save_params(df):
        try:
            save_parquet(df, "fiches_paie/params.parquet")
            return True, None
        except Exception as e:
            return False, str(e)

    def _compact_param_fields(key_prefix, cur):
        """Champs de paramètres en grille 3×2. Retourne le dict des valeurs."""
        c1, c2, c3 = st.columns(3)
        with c1:
            ph  = st.number_input("Heures/sem", 0.0, 60.0,
                                  float(cur.get("heures_hebdo", 35)), 0.5,
                                  key=f"{key_prefix}_hh")
            pjc = st.number_input("Congés/an (j)", 0, 60,
                                  int(cur.get("jours_conge_annuels", 25)),
                                  key=f"{key_prefix}_jc")
        with c2:
            pt  = st.number_input("Taux horaire (€/h)", 0.0,
                                  value=float(cur.get("taux_horaire_base", 15.0)), step=0.1,
                                  key=f"{key_prefix}_th")
            pe  = st.number_input("Période d'essai (j)", 0,
                                  value=int(cur.get("periode_essai_jours", 0)),
                                  key=f"{key_prefix}_pe")
        with c3:
            pcs = st.number_input("Cotis. salariales %", 0.0, 60.0,
                                  float(cur.get("cotisations_salariales_pct", 22.0)), 0.1,
                                  key=f"{key_prefix}_cs")
            pcp = st.number_input("Cotis. patronales %", 0.0, 80.0,
                                  float(cur.get("cotisations_patronales_pct", 42.0)), 0.1,
                                  key=f"{key_prefix}_cp")
        pn = st.text_input("Notes", value=str(cur.get("notes","")) if cur.get("notes") else "",
                           key=f"{key_prefix}_n")
        return {"heures_hebdo": ph, "taux_horaire_base": pt, "jours_conge_annuels": pjc,
                "periode_essai_jours": pe, "cotisations_salariales_pct": pcs,
                "cotisations_patronales_pct": pcp, "notes": pn}

    # ── Cartes pour chaque type ───────────────────────────────────────────────
    all_tc_list = all_params["type_contrat"].tolist()

    for tc in all_tc_list:
        is_custom   = tc not in defined_types
        badge_col   = "#6b1aa8" if is_custom else "#1a6fa8"
        badge_bg    = "#ede8fd" if is_custom else "#ddeeff"
        badge_txt   = "Personnalisé" if is_custom else "Prédéfini"
        cur         = all_params[all_params["type_contrat"] == tc].iloc[0].to_dict()

        # Résumé court pour le label de l'expander
        hh   = cur.get("heures_hebdo", 0)
        taux = cur.get("taux_horaire_base", 0)
        cs   = cur.get("cotisations_salariales_pct", 0)
        summary = f"{hh:.0f}h/sem · {taux:.2f}€/h · Sal. {cs:.0f}%"

        with st.expander(
            f"{'🏷️' if is_custom else '📋'}  **{tc}** — {summary}",
            expanded=False):

            st.markdown(
                f'<span style="background:{badge_bg};color:{badge_col};padding:2px 8px;'
                f'border-radius:8px;font-size:11px;font-weight:600">{badge_txt}</span>',
                unsafe_allow_html=True)

            with st.form(f"param_edit_{tc}"):
                vals = _compact_param_fields(f"e_{tc}", cur)
                btn_cols = st.columns([2, 1, 1])
                with btn_cols[0]:
                    save_ok = st.form_submit_button(
                        "💾 Enregistrer", type="primary", use_container_width=True)
                with btn_cols[1]:
                    # Réinitialiser aux valeurs d'usine (prédéfinis seulement)
                    factory = next((p for p in PARAMS_DEFAULT if p["type_contrat"] == tc), None)
                    reset_ok = st.form_submit_button(
                        "🔄 Défaut", use_container_width=True,
                        disabled=(factory is None))
                with btn_cols[2]:
                    del_ok = st.form_submit_button(
                        "🗑️ Supprimer", use_container_width=True,
                        disabled=(not is_custom),
                        help="Seuls les types personnalisés peuvent être supprimés.")

                if save_ok:
                    new_p = {"type_contrat": tc, **vals}
                    idx = st.session_state.params_df[
                        st.session_state.params_df["type_contrat"] == tc].index
                    if len(idx) > 0:
                        for k, v in new_p.items():
                            st.session_state.params_df.loc[idx, k] = v
                    else:
                        st.session_state.params_df = pd.concat(
                            [st.session_state.params_df, pd.DataFrame([new_p])], ignore_index=True)
                    ok, err = _save_params(st.session_state.params_df)
                    if ok:
                        st.success(f"✅ «{tc}» enregistré."); st.rerun()
                    else:
                        st.error(f"Erreur : {err}")

                if reset_ok and factory:
                    idx = st.session_state.params_df[
                        st.session_state.params_df["type_contrat"] == tc].index
                    for k, v in factory.items():
                        st.session_state.params_df.loc[idx, k] = v
                    ok, err = _save_params(st.session_state.params_df)
                    if ok:
                        st.success(f"✅ «{tc}» réinitialisé."); st.rerun()
                    else:
                        st.error(f"Erreur : {err}")

                if del_ok and is_custom:
                    st.session_state.params_df = st.session_state.params_df[
                        st.session_state.params_df["type_contrat"] != tc]
                    ok, err = _save_params(st.session_state.params_df)
                    if ok:
                        st.success(f"✅ «{tc}» supprimé."); st.rerun()
                    else:
                        st.error(f"Erreur : {err}")

    # ── Ajouter un nouveau type ───────────────────────────────────────────────
    st.markdown("---")
    with st.expander("➕ Créer un nouveau type de contrat", expanded=False):
        st.caption("Le nouveau type apparaîtra dans les menus déroulants de l'onglet Ressources.")
        with st.form("param_new_type"):
            n_name = st.text_input("Nom du nouveau type *",
                                   placeholder="Ex: Portage salarial, CDI Cadre, …")
            new_vals = _compact_param_fields(
                "new_type",
                {"heures_hebdo": 35, "taux_horaire_base": 15.0, "jours_conge_annuels": 25,
                 "periode_essai_jours": 0, "cotisations_salariales_pct": 22.0,
                 "cotisations_patronales_pct": 42.0, "notes": ""})
            if st.form_submit_button("✅ Créer", type="primary", use_container_width=True):
                n = n_name.strip()
                if not n:
                    st.error("Le nom est obligatoire.")
                elif n in all_params["type_contrat"].values:
                    st.error(f"«{n}» existe déjà.")
                else:
                    new_p = {"type_contrat": n, **new_vals}
                    st.session_state.params_df = pd.concat(
                        [st.session_state.params_df, pd.DataFrame([new_p])], ignore_index=True)
                    ok, err = _save_params(st.session_state.params_df)
                    if ok:
                        st.success(f"✅ Type «{n}» créé !"); st.rerun()
                    else:
                        st.error(f"Erreur : {err}")
