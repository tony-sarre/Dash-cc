import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import requests
from io import StringIO

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Performance Agents",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour améliorer l'apparence
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .kpi-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    h1 {
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stSelectbox > div > div {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def load_data():
    """Charge les données depuis Heroku avec gestion d'erreur"""
    try:
        url = "https://data.heroku.com/dataclips/ackxrcibmcibimjncetgsayvfguw.csv"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text))
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        return pd.DataFrame()


def calculate_performance_score(agent_data):
    """Calcule un score de performance globale pour un agent"""
    if len(agent_data) == 0:
        return 0

    # Normalisation des métriques (sur 100)
    interactions = agent_data['total_interaction_appel_par_agent'].sum()
    commandes = agent_data['total_commandes_journalier'].sum()
    notations = agent_data['total_notation_par_agent'].sum()

    # Métriques négatives
    reclamations = agent_data['total_reclamation_par_agent'].sum()
    suivi_reclamations = agent_data['total_suivi_reclamation_par_agent'].sum()
    livraison_impossible = agent_data['total_suivi_livraison_impossible_par_agent'].sum()

    # Score basé sur les interactions positives vs négatives
    score_positif = (interactions * 2) + (commandes * 3) + (notations * 1.5)
    score_negatif = (reclamations * 2) + (suivi_reclamations * 1.5) + (livraison_impossible * 1.8)

    # Score final (plus il y a d'activité positive, meilleur c'est)
    if score_positif + score_negatif == 0:
        return 0

    score = (score_positif / (score_positif + score_negatif)) * 100
    return min(score, 100)


def create_gauge_chart(value, title, max_value=100):
    """Crée un graphique en jauge"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16}},
        delta={'reference': max_value * 0.7},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "lightgray"},
                {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def main():
    st.title("📊 Dashboard Performance des Agents")

    # Chargement des données
    with st.spinner("Chargement des données..."):
        df = load_data()

    if df.empty:
        st.error("Impossible de charger les données. Veuillez vérifier la connexion.")
        return

    # Sidebar pour les filtres
    st.sidebar.header("🔧 Filtres")

    # Filtre par période
    date_min = df['date'].min()
    date_max = df['date'].max()

    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Date début", date_min, min_value=date_min, max_value=date_max)
    with col2:
        end_date = st.date_input("Date fin", date_max, min_value=date_min, max_value=date_max)

    # Filtre par agent
    agents = ['Tous'] + sorted(df['agent'].dropna().unique().tolist())
    selected_agent = st.sidebar.selectbox("Agent", agents)

    # Filtre par zone
    zones = ['Toutes'] + sorted(df['zone'].dropna().unique().tolist())
    selected_zone = st.sidebar.selectbox("Zone", zones)

    # Application des filtres
    filtered_df = df[
        (df['date'] >= pd.to_datetime(start_date)) &
        (df['date'] <= pd.to_datetime(end_date))
        ]

    if selected_agent != 'Tous':
        filtered_df = filtered_df[filtered_df['agent'] == selected_agent]

    if selected_zone != 'Toutes':
        filtered_df = filtered_df[filtered_df['zone'] == selected_zone]

    if filtered_df.empty:
        st.warning("Aucune donnée disponible pour les filtres sélectionnés.")
        return

    # Métriques globales
    st.header("📈 Vue d'ensemble")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_agents = filtered_df['agent'].nunique()
        st.metric("👥 Agents actifs", total_agents)

    with col2:
        total_commandes = filtered_df['total_commandes_journalier'].sum()
        st.metric("🛍️ Total commandes", f"{total_commandes:,}")

    with col3:
        total_interactions = filtered_df['total_interaction_appel_par_agent'].sum()
        st.metric("📞 Total interactions", f"{total_interactions:,}")

    with col4:
        avg_sku = filtered_df['moyenne_sku_par_commande'].mean()
        st.metric("📦 Moy. SKU/commande", f"{avg_sku:.1f}")

    # Deuxième ligne de métriques
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_reclamations = filtered_df['total_reclamation_par_agent'].sum()
        st.metric("⚠️ Total réclamations", f"{total_reclamations:,}")

    with col2:
        total_suivi_reclamations = filtered_df['total_suivi_reclamation_par_agent'].sum()
        st.metric("🔄 Suivi réclamations", f"{total_suivi_reclamations:,}")

    with col3:
        total_livraison_impossible = filtered_df['total_suivi_livraison_impossible_par_agent'].sum()
        st.metric("🚫 Livraisons impossibles", f"{total_livraison_impossible:,}")

    with col4:
        total_notations = filtered_df['total_notation_par_agent'].sum()
        st.metric("⭐ Notations livreurs", f"{total_notations:,}")

    # Performance par agent
    st.header("🏆 Classement des Agents")

    # Calcul des scores de performance
    agent_performance = []
    for agent in filtered_df['agent'].unique():
        if pd.isna(agent):
            continue
        agent_data = filtered_df[filtered_df['agent'] == agent]
        score = calculate_performance_score(agent_data)

        agent_performance.append({
            'Agent': agent,
            'Score Performance': score,
            'Commandes': agent_data['total_commandes_journalier'].sum(),
            'Interactions': agent_data['total_interaction_appel_par_agent'].sum(),
            'Réclamations': agent_data['total_reclamation_par_agent'].sum(),
            'Suivi Réclamations': agent_data['total_suivi_reclamation_par_agent'].sum(),
            'Livraisons Impossibles': agent_data['total_suivi_livraison_impossible_par_agent'].sum(),
            'Notations Livreurs': agent_data['total_notation_par_agent'].sum(),
            'SKU Total': agent_data['total_sku_par_agent'].sum()
        })

    performance_df = pd.DataFrame(agent_performance).sort_values('Score Performance', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Graphique en barres du classement
        fig = px.bar(
            performance_df.head(10),
            x='Agent',
            y='Score Performance',
            color='Score Performance',
            color_continuous_scale='RdYlGn',
            title="Top 10 - Scores de Performance"
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Jauge pour le meilleur agent
        if not performance_df.empty:
            best_agent = performance_df.iloc[0]
            fig_gauge = create_gauge_chart(
                best_agent['Score Performance'],
                f"Meilleur Agent\n{best_agent['Agent']}"
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

    # Tableau détaillé des performances
    st.subheader("📋 Détail des Performances")
    st.dataframe(
        performance_df.style.format({
            'Score Performance': '{:.1f}',
            'Commandes': '{:,}',
            'Interactions': '{:,}',
            'Réclamations': '{:,}',
            'Suivi Réclamations': '{:,}',
            'Livraisons Impossibles': '{:,}',
            'Notations Livreurs': '{:,}',
            'SKU Total': '{:,}'
        }).background_gradient(subset=['Score Performance'], cmap='RdYlGn'),
        use_container_width=True
    )

    # Évolution temporelle
    st.header("📅 Évolution dans le Temps")

    # Données agrégées par date
    daily_stats = filtered_df.groupby('date').agg({
        'total_commandes_journalier': 'sum',
        'total_interaction_appel_par_agent': 'sum',
        'total_reclamation_par_agent': 'sum',
        'total_suivi_reclamation_par_agent': 'sum',
        'total_suivi_livraison_impossible_par_agent': 'sum',
        'total_notation_par_agent': 'sum',
        'total_sku_par_agent': 'sum'
    }).reset_index()

    # Graphiques d'évolution
    fig_evolution = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Commandes par jour', 'Interactions par jour',
                        'Réclamations par jour', 'Suivi Réclamations par jour',
                        'Livraisons Impossibles par jour', 'Notations Livreurs par jour'),
        vertical_spacing=0.08
    )

    # Commandes
    fig_evolution.add_trace(
        go.Scatter(x=daily_stats['date'], y=daily_stats['total_commandes_journalier'],
                   mode='lines+markers', name='Commandes', line=dict(color='blue')),
        row=1, col=1
    )

    # Interactions
    fig_evolution.add_trace(
        go.Scatter(x=daily_stats['date'], y=daily_stats['total_interaction_appel_par_agent'],
                   mode='lines+markers', name='Interactions', line=dict(color='green')),
        row=1, col=2
    )

    # Réclamations
    fig_evolution.add_trace(
        go.Scatter(x=daily_stats['date'], y=daily_stats['total_reclamation_par_agent'],
                   mode='lines+markers', name='Réclamations', line=dict(color='red')),
        row=2, col=1
    )

    # Suivi Réclamations
    fig_evolution.add_trace(
        go.Scatter(x=daily_stats['date'], y=daily_stats['total_suivi_reclamation_par_agent'],
                   mode='lines+markers', name='Suivi Réclamations', line=dict(color='orange')),
        row=2, col=2
    )

    # Livraisons Impossibles
    fig_evolution.add_trace(
        go.Scatter(x=daily_stats['date'], y=daily_stats['total_suivi_livraison_impossible_par_agent'],
                   mode='lines+markers', name='Livraisons Impossibles', line=dict(color='darkred')),
        row=3, col=1
    )

    # Notations Livreurs
    fig_evolution.add_trace(
        go.Scatter(x=daily_stats['date'], y=daily_stats['total_notation_par_agent'],
                   mode='lines+markers', name='Notations', line=dict(color='purple')),
        row=3, col=2
    )

    fig_evolution.update_layout(height=800, showlegend=False, title_text="Évolution des Métriques")
    st.plotly_chart(fig_evolution, use_container_width=True)

    # Analyse par zone (si plusieurs zones)
    if selected_zone == 'Toutes' and filtered_df['zone'].nunique() > 1:
        st.header("🌍 Performance par Zone")

        zone_stats = filtered_df.groupby('zone').agg({
            'total_commandes_journalier': 'sum',
            'total_interaction_appel_par_agent': 'sum',
            'total_reclamation_par_agent': 'sum',
            'total_suivi_reclamation_par_agent': 'sum',
            'total_suivi_livraison_impossible_par_agent': 'sum',
            'total_notation_par_agent': 'sum',
            'agent': 'nunique'
        }).reset_index()
        zone_stats.columns = ['Zone', 'Commandes', 'Interactions', 'Réclamations',
                              'Suivi Réclamations', 'Livraisons Impossibles', 'Notations', 'Nb_Agents']

        col1, col2 = st.columns(2)

        with col1:
            fig_zone_pie = px.pie(
                zone_stats,
                values='Commandes',
                names='Zone',
                title="Répartition des Commandes par Zone"
            )
            st.plotly_chart(fig_zone_pie, use_container_width=True)

        with col2:
            fig_zone_bar = px.bar(
                zone_stats,
                x='Zone',
                y=['Commandes', 'Interactions', 'Réclamations', 'Suivi Réclamations',
                   'Livraisons Impossibles', 'Notations'],
                title="Métriques par Zone",
                barmode='group'
            )
            st.plotly_chart(fig_zone_bar, use_container_width=True)

    # Analyse détaillée d'un agent spécifique
    if selected_agent != 'Tous':
        st.header(f"🔍 Analyse Détaillée - {selected_agent}")

        agent_data = filtered_df[filtered_df['agent'] == selected_agent]

        col1, col2, col3 = st.columns(3)

        with col1:
            total_days = agent_data['date'].nunique()
            st.metric("📅 Jours d'activité", total_days)

        with col2:
            avg_commandes = agent_data['total_commandes_journalier'].mean()
            st.metric("📈 Moy. commandes/jour", f"{avg_commandes:.1f}")

        with col3:
            efficiency_ratio = (agent_data['total_commandes_journalier'].sum() /
                                max(agent_data['total_reclamation_par_agent'].sum() +
                                    agent_data['total_suivi_livraison_impossible_par_agent'].sum(), 1))
            st.metric("⚡ Ratio Efficacité", f"{efficiency_ratio:.1f}")

        # Graphique de l'activité quotidienne de l'agent
        fig_agent = px.line(
            agent_data,
            x='date',
            y=['total_commandes_journalier', 'total_interaction_appel_par_agent',
               'total_reclamation_par_agent', 'total_suivi_reclamation_par_agent',
               'total_suivi_livraison_impossible_par_agent', 'total_notation_par_agent'],
            title=f"Activité Quotidienne - {selected_agent}",
            labels={'value': 'Nombre', 'variable': 'Métrique'}
        )
        st.plotly_chart(fig_agent, use_container_width=True)

    # Footer avec informations
    st.markdown("---")
    st.markdown("""
    **💡 Indicateurs de Performance:**
    - **Score Performance**: Calculé selon le ratio interactions positives vs réclamations
    - **Ratio Efficacité**: Commandes traitées par réclamation
    - **Données actualisées**: Toutes les 5 minutes
    """)


if __name__ == "__main__":
    main()