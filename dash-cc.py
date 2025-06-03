import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import MinMaxScaler
import json
import os

# Configuration page
st.set_page_config(layout="wide", page_title="Dashboard Agents")

# Chargement des données
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data.csv")
        df['date'] = pd.to_datetime(df['date'])
        return df
    except FileNotFoundError:
        st.error("❌ Fichier data.csv introuvable")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

st.title("Dashboard Performance Agents")

# Sidebar filtres
with st.sidebar:
    st.header("Filtres")
    dates = st.date_input("Période", [df['date'].min(), df['date'].max()])
    agents = st.multiselect("Agents", df['agent'].unique(), default=list(df['agent'].unique()))
    zones = st.multiselect("Zones", df['zone'].unique(), default=list(df['zone'].unique()))

# Filtre données
filtered_df = df[
    (df['date'] >= pd.to_datetime(dates[0])) &
    (df['date'] <= pd.to_datetime(dates[1])) &
    (df['agent'].isin(agents)) &
    (df['zone'].isin(zones))
]

# KPIs
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Commandes", f"{filtered_df['total_commandes_journalier'].sum():,}")
with col2:
    st.metric("Total Appels", f"{filtered_df['total_interaction_appel_par_agent'].sum():,}")
with col3:
    st.metric("Réclamations", f"{filtered_df['total_reclamation_par_agent'].sum():,}")
with col4:
    st.metric("Livraisons Impossibles", f"{filtered_df['total_suivi_livraison_impossible_par_agent'].sum():,}")

# Graphique principal
fig = px.bar(filtered_df, x='agent', y='total_commandes_journalier',
             title="Commandes par Agent", color='agent')
st.plotly_chart(fig, use_container_width=True)

# *** SOLUTION : TABLEAU SIMPLE SANS STYLING ***
st.subheader("Détails des Performances")
st.dataframe(filtered_df, use_container_width=True)

# Système notation
st.subheader("Notation Agents")
scores = filtered_df.groupby("agent").agg({
    "total_commandes_journalier": "sum",
    "total_interaction_appel_par_agent": "sum",
    "total_reclamation_par_agent": "sum",
    "total_suivi_livraison_impossible_par_agent": "sum"
}).reset_index()

# Calcul scores
scores["reclam_score"] = 1 / (1 + scores["total_reclamation_par_agent"])
scores["livr_score"] = 1 / (1 + scores["total_suivi_livraison_impossible_par_agent"])

# Normalisation
scaler = MinMaxScaler()
cols_to_scale = ["total_commandes_journalier", "total_interaction_appel_par_agent", "reclam_score", "livr_score"]
scores_norm = pd.DataFrame(
    scaler.fit_transform(scores[cols_to_scale]),
    columns=["cmd", "appels", "reclam", "livr"],
    index=scores["agent"]
)

# Note finale
scores_norm["note"] = (
    scores_norm["cmd"] * 0.40 +
    scores_norm["appels"] * 0.25 +
    scores_norm["reclam"] * 0.20 +
    scores_norm["livr"] * 0.15
) * 100

scores_final = scores_norm[["note"]].round(1).sort_values("note", ascending=False)

# *** SOLUTION : TABLEAU SCORES SANS STYLING ***
st.dataframe(scores_final, use_container_width=True)

# Graphique scores
fig_score = px.bar(scores_final.reset_index(), x="agent", y="note",
                   title="Classement par Performance", color="note",
                   color_continuous_scale="viridis")
st.plotly_chart(fig_score, use_container_width=True)

# Commentaires
st.subheader("Commentaires")
selected_agent = st.selectbox("Agent", scores_final.index)
feedback = st.text_area(f"Commentaire pour {selected_agent}")

# Gestion commentaires
COMMENT_FILE = "commentaires.json"

def load_comments():
    if os.path.exists(COMMENT_FILE):
        with open(COMMENT_FILE, "r") as f:
            return json.load(f)
    return {}

if st.button("Enregistrer"):
    comments = load_comments()
    comments[selected_agent] = feedback
    with open(COMMENT_FILE, "w") as f:
        json.dump(comments, f)
    st.success(f"✅ Commentaire enregistré pour {selected_agent}")