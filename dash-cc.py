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
        st.error(" Fichier data.csv introuvable")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

st.title("Dashboard Performance Agents")

# Sidebar filtres
with st.sidebar:
    st.header("Filtres")

    # Gestion sûre de l'entrée de date
    default_dates = [df['date'].min(), df['date'].max()]
    dates = st.date_input("Période", value=default_dates,
                          min_value=default_dates[0].date(),
                          max_value=default_dates[1].date())

    # Option "Tous" pour les agents
    all_agents = list(df['agent'].unique())
    agent_choice = st.selectbox("Sélection Agents", ["Tous", "Sélection personnalisée"])
    if agent_choice == "Tous":
        agents = all_agents
        st.info(f"Tous les agents sélectionnés ({len(all_agents)})")
    else:
        agents = st.multiselect("Agents", all_agents, default=all_agents)

    # Option "Tous" pour les zones
    all_zones = list(df['zone'].unique())
    zone_choice = st.selectbox("Sélection Zones", ["Tous", "Sélection personnalisée"])
    if zone_choice == "Tous":
        zones = all_zones
        st.info(f"Toutes les zones sélectionnées ({len(all_zones)})")
    else:
        zones = st.multiselect("Zones", all_zones, default=all_zones)

#  Filtre données en toute sécurité
try:
    if isinstance(dates, list) and len(dates) == 2:
        start_date = pd.to_datetime(dates[0])
        end_date = pd.to_datetime(dates[1])
        filtered_df = df[
            (df['date'] >= start_date) &
            (df['date'] <= end_date) &
            (df['agent'].isin(agents)) &
            (df['zone'].isin(zones))
        ]
    else:
       # st.warning(" Veuillez sélectionner une plage de deux dates.")
        filtered_df = df.copy()
except Exception as e:
    st.error(f" Erreur lors du filtrage des données : {str(e)}")
    filtered_df = df.copy()

# KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Commandes", f"{filtered_df['total_commandes_journalier'].sum():,}")

with col2:
    st.metric("Total Interactions", f"{filtered_df['total_interactions_par_agent'].sum():,}")

with col3:
    st.metric("Réclamations", f"{filtered_df['total_reclamation_par_agent'].sum():,}")

with col4:
    st.metric("Livraisons Impossibles", f"{filtered_df['total_suivi_livraison_impossible_par_agent'].sum():,}")

col5, col6, col7, col8 = st.columns(4)

with col5:
    notation = filtered_df['total_notation_par_agent'].sum()
    st.metric("Notation", f"{notation:.1f}" if not pd.isna(notation) else "0.0")

with col6:
    moy_sku = filtered_df['moyenne_sku_par_commande'].mean()
    st.metric("Moy. SKU/Commande", f"{moy_sku:.1f}" if not pd.isna(moy_sku) else "0.0")

with col7:
    st.metric("Total SKU", f"{filtered_df['total_sku_par_agent'].sum():,}")

with col8:
    st.metric("Suivi Réclamation", f"{filtered_df['total_suivi_reclamation_par_agent'].sum():,}")

col9, col10, col11 = st.columns(3)

with col9:
    nb_agents = len(filtered_df['agent'].unique())
    st.metric("Agents Actifs", f"{nb_agents}")

with col10:
    nb_zones = len(filtered_df['zone'].unique())
    st.metric("Zones Actives", f"{nb_zones}")

with col11:
    if nb_agents > 0:
        moy_cmd_agent = filtered_df['total_commandes_journalier'].sum() / nb_agents
        st.metric("Moy. Cmd/Agent", f"{moy_cmd_agent:.0f}")
    else:
        st.metric("Moy. Cmd/Agent", "0")

fig = px.bar(filtered_df, x='agent', y='total_commandes_journalier',
             title="Commandes par Agent", color='agent')
st.plotly_chart(fig, use_container_width=True)

st.subheader("Détails des Performances")
st.dataframe(filtered_df, use_container_width=True)

st.subheader("Notation Agents")
scores = filtered_df.groupby("agent").agg({
    "total_commandes_journalier": "sum",
    "total_interaction_appel_par_agent": "sum",
    "total_reclamation_par_agent": "sum",
    "total_suivi_livraison_impossible_par_agent": "sum",
    "total_notation_par_agent": "mean",
    "total_sku_par_agent": "sum",
    "total_suivi_reclamation_par_agent": "sum"
}).reset_index()

scores["reclam_score"] = 1 / (1 + scores["total_reclamation_par_agent"])
scores["livr_score"] = 1 / (1 + scores["total_suivi_livraison_impossible_par_agent"])

scaler = MinMaxScaler()
cols_to_scale = ["total_commandes_journalier", "total_interaction_appel_par_agent", "reclam_score", "livr_score",
                 "total_notation_par_agent"]
scores_norm = pd.DataFrame(
    scaler.fit_transform(scores[cols_to_scale]),
    columns=["cmd", "interaction", "reclam", "livr", "notation"],
    index=scores["agent"]
)

scores_norm["note"] = (
    scores_norm["cmd"] * 0.30 +
    scores_norm["interaction"] * 0.20 +
    scores_norm["reclam"] * 0.20 +
    scores_norm["livr"] * 0.15 +
    scores_norm["notation"] * 0.15
) * 100

scores_final = scores_norm[["note"]].round(1).sort_values("note", ascending=False)
st.dataframe(scores_final, use_container_width=True)

fig_score = px.bar(scores_final.reset_index(), x="agent", y="note",
                   title="Classement par Performance", color="note",
                   color_continuous_scale="viridis")
st.plotly_chart(fig_score, use_container_width=True)

st.subheader("Commentaires")
selected_agent = st.selectbox("Agent", scores_final.index)
feedback = st.text_area(f"Commentaire pour {selected_agent}")

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