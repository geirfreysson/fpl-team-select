#!/usr/bin/env python3
"""
FPL Team Selection Dashboard

A Streamlit dashboard for the FPL team selector with interactive parameter controls.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path

# Try to import the FPL team selector
try:
    from fpl_team_selector import FPLTeamSelector
    SELECTOR_AVAILABLE = True
except ImportError as e:
    SELECTOR_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Page config
st.set_page_config(
    page_title="FPL Team Selector Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_player_pics(data_dir):
    """Load player pictures from JSON file."""
    try:
        pics_path = Path(data_dir) / "player_pics.json"
        if pics_path.exists():
            with open(pics_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

st.title("⚽ FPL Team Selector Dashboard")
st.markdown("Optimize your Fantasy Premier League team using Integer Linear Programming")

st.markdown("Vibe coded by [Geir Freysson](https://geirfreysson.com)")
st.markdown("For more data driven FPL madness check out the [FPL AI Agent](https://fpl.withrobots.ai)")

# Sidebar controls
st.sidebar.header("Optimization Parameters")

# Objective selection
objective = st.sidebar.selectbox(
    "Objective",
    options=["max_points", "max_spend"],
    index=0,
    help="max_points: Maximize projected points | max_spend: Maximize budget usage"
)

# Weighting sliders
fixture_weighting = st.sidebar.slider(
    "Fixture Difficulty Weighting",
    min_value=0.0,
    max_value=1.0,
    value=0.0,
    step=0.1,
    help="Higher weight = more influence from fixture difficulty (0.0 = ignore fixtures)"
)

last_season_weighting = st.sidebar.slider(
    "Last Season Performance Weighting",
    min_value=0.0,
    max_value=1.0,
    value=0.0,
    step=0.1,
    help="Higher weight = more influence from 2023/24 season data (0.0 = ignore history)"
)

# Boolean constraints
st.sidebar.subheader("Player Selection Constraints")

require_all_starts = st.sidebar.checkbox(
    "Only Regular Starters",
    value=True,
    help="If checked, only include players who have started all games"
)

max_per_team_per_position = st.sidebar.checkbox(
    "Max 1 Per Team Per Position",
    value=True,
    help="If checked, maximum 1 player per team per position (reduces team overlap)"
)

exclude_injury_risk = st.sidebar.checkbox(
    "Exclude Injury Risk Players",
    value=True,
    help="If checked, exclude players who are doubtful, injured, or have <75% chance of playing"
)

# Data directory (hardcoded)
data_dir = "fpl_data"

# Auto-refresh (hardcoded to True)
auto_refresh = True

# Manual optimization button (only show when auto-refresh is off)
if not auto_refresh:
    run_optimization = st.sidebar.button(
        "🚀 Optimize Team",
        type="primary",
        help="Run the optimization with current parameters",
        disabled=not SELECTOR_AVAILABLE
    )
else:
    run_optimization = True  # Always run when auto-refresh is enabled

# Main content area
if not SELECTOR_AVAILABLE:
    st.error(f"❌ Cannot load FPL Team Selector: {IMPORT_ERROR}")
    st.info("Make sure to install required dependencies: `uv add ortools`")
    st.stop()

# Create a key from current parameters to detect changes
current_params = (
    objective, fixture_weighting, last_season_weighting,
    require_all_starts, max_per_team_per_position, exclude_injury_risk, data_dir
)

# Initialize session state for parameters
if 'last_params' not in st.session_state:
    st.session_state.last_params = None
    st.session_state.solution = None

# Check if parameters changed
params_changed = st.session_state.last_params != current_params

# Run optimization if button clicked or auto-refresh enabled and params changed
should_optimize = run_optimization and (not auto_refresh or params_changed or st.session_state.solution is None)

if should_optimize:
    try:
        with st.spinner("Loading FPL data and optimizing team..."):
            # Initialize selector
            selector = FPLTeamSelector(data_dir)
            
            # Run optimization
            solution = selector.solve_team_selection(
                objective=objective,
                require_all_starts=require_all_starts,
                max_per_team_per_position=max_per_team_per_position,
                exclude_injury_risk=exclude_injury_risk,
                fixture_weighting=fixture_weighting,
                last_season_weighting=last_season_weighting
            )
        
        if solution:
            # Store solution in session state
            st.session_state.solution = solution
            st.session_state.last_params = current_params
            
            # Display solution summary
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cost", f"£{solution['total_price']:.1f}m", f"£{100.0 - solution['total_price']:.1f}m remaining")
            
            with col2:
                st.metric("Projected Points", f"{solution['total_proj_points']}")
            
            with col3:
                st.metric("Five GameAvg Fixture Difficulty", f"{solution['avg_fixture_difficulty']:.2f}", help="Lower is easier fixtures")
            
            with col4:
                if solution.get('fixture_weighting', 0) > 0:
                    st.metric("Fixture-Adjusted Points", f"{solution['total_fixture_adjusted_points']:.1f}")
                elif solution.get('last_season_weighting', 0) > 0:
                    st.metric("History-Adjusted Points", f"{solution['total_last_season_adjusted_points']:.1f}")
                else:
                    st.metric("Solver Status", solution['solver_status'])
            
            # Display team table
            st.subheader("🎯 Optimal Team")
            
            # Load player pictures
            player_pics = load_player_pics(data_dir)
            
            # Prepare display data ordered by position
            position_order = ['GKP', 'DEF', 'MID', 'FWD']
            display_data = []
            
            # Sort players by position order first
            selected_players_df = pd.DataFrame(solution['selected_players'])
            selected_players_df['position_order'] = selected_players_df['position'].map({pos: i for i, pos in enumerate(position_order)})
            selected_players_df = selected_players_df.sort_values(['position_order', 'name'])
            
            for _, player in selected_players_df.iterrows():
                # Get player picture URL
                pic_url = player_pics.get(str(player['id']), "")
                
                row = {
                    'Photo': pic_url,
                    'Name': player['name'],
                    'Position': player['position'],
                    'Team': player['team_name'],
                    'Price': f"£{player['price']:.1f}m",
                    'Points': f"{player['proj_points']:.0f}",
                    'Fixture Difficulty': f"{player['avg_fixture_difficulty_5']:.1f}",
                    'Next 5 Fixtures': player['next_5_fixtures']
                }
                
                # Add conditional columns based on weightings
                if solution.get('fixture_weighting', 0) > 0:
                    row['Fixture-Adj Points'] = f"{player['fixture_adjusted_points']:.1f}"
                
                if solution.get('last_season_weighting', 0) > 0:
                    row['Current PPG'] = f"{player['current_points_per_gw']:.1f}"
                    row['Last Season PPG'] = f"{player['last_season_points_per_gw']:.1f}"
                    row['History-Adj Points'] = f"{player['last_season_adjusted_points']:.1f}"
                
                display_data.append(row)
            
            df_display = pd.DataFrame(display_data)
            
            # Style the dataframe
            def style_position(val):
                color_map = {
                    'GKP': 'background-color: #ffeb3b; color: black',
                    'DEF': 'background-color: #4caf50; color: white',
                    'MID': 'background-color: #2196f3; color: white',
                    'FWD': 'background-color: #f44336; color: white'
                }
                return color_map.get(val, '')
            
            # Configure column types, especially the Photo column as ImageColumn
            column_config = {
                "Photo": st.column_config.ImageColumn(
                    "Photo",
                    help="Player photo",
                    width="small"
                )
            }
            
            # Style the dataframe and show with image column
            styled_df = df_display.style.applymap(style_position, subset=['Position'])
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True,
                column_config=column_config,
                height=len(df_display) * 35 + 40
            )
            
            # Team composition tables
            col1, col2 = st.columns(2)
            
            with col1:
                # Team distribution as table
                st.subheader("Team Distribution")
                team_counts = pd.DataFrame(list(solution['by_team_counts'].items()), 
                                         columns=['Team', 'Players'])
                team_counts = team_counts.sort_values('Players', ascending=False)
                st.dataframe(team_counts, use_container_width=True, hide_index=True)
            
            with col2:
                # Position breakdown
                positions_df = pd.DataFrame(solution['selected_players'])
                pos_summary = positions_df.groupby('position').agg({
                    'price': 'sum',
                    'proj_points': 'sum',
                    'name': 'count'
                }).round(1)
                pos_summary.columns = ['Total Cost (£m)', 'Total Points', 'Count']
                pos_summary = pos_summary.reindex(['GKP', 'DEF', 'MID', 'FWD'])
                
                st.subheader("Position Summary")
                st.dataframe(pos_summary, use_container_width=True)
            
            # Validation results
            validation = selector.validate_solution(solution)
            
            st.subheader("✅ Validation")
            val_col1, val_col2, val_col3, val_col4, val_col5 = st.columns(5)
            
            with val_col1:
                status = "✅" if validation['valid'] else "❌"
                st.metric("Overall Valid", status)
            
            with val_col2:
                status = "✅" if validation['squad_size'] else "❌"
                st.metric("Squad Size (15)", status)
            
            with val_col3:
                status = "✅" if validation['budget'] else "❌"
                st.metric("Budget (≤£100m)", status)
            
            with val_col4:
                status = "✅" if validation['positions'] else "❌"
                st.metric("Positions (2-5-5-3)", status)
            
            with val_col5:
                status = "✅" if validation['club_limits'] else "❌"
                st.metric("Club Limits (≤3)", status)
            
            # Export functionality
            st.subheader("📋 Export")
            
            # Player IDs for FPL import
            player_ids = solution['selected_ids']
            id_string = ",".join(map(str, player_ids))
            
            st.text_area(
                "Player IDs (for FPL import tools):",
                value=id_string,
                height=100,
                help="Copy these player IDs to import into FPL tools"
            )
            
            # Download CSV
            csv = df_display.to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv,
                file_name="fpl_optimal_team.csv",
                mime="text/csv"
            )
            
        else:
            st.error("❌ No feasible solution found! Try relaxing some constraints.")
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("Make sure you have run the data processing script and have valid FPL data files.")

# Display cached solution if available
elif st.session_state.solution is not None:
    solution = st.session_state.solution
    
    # Display solution summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cost", f"£{solution['total_price']:.1f}m", f"£{100.0 - solution['total_price']:.1f}m remaining")
    
    with col2:
        st.metric("Projected Points", f"{solution['total_proj_points']}")
    
    with col3:
        st.metric("Avg Fixture Difficulty", f"{solution['avg_fixture_difficulty']:.2f}", help="Lower is easier fixtures")
    
    with col4:
        if solution.get('fixture_weighting', 0) > 0:
            st.metric("Fixture-Adjusted Points", f"{solution['total_fixture_adjusted_points']:.1f}")
        elif solution.get('last_season_weighting', 0) > 0:
            st.metric("History-Adjusted Points", f"{solution['total_last_season_adjusted_points']:.1f}")
        else:
            st.metric("Solver Status", solution['solver_status'])
    
    # Display team table
    st.subheader("🎯 Optimal Team")
    
    # Load player pictures
    player_pics = load_player_pics(data_dir)
    
    # Prepare display data ordered by position
    position_order = ['GKP', 'DEF', 'MID', 'FWD']
    display_data = []
    
    # Sort players by position order first
    selected_players_df = pd.DataFrame(solution['selected_players'])
    selected_players_df['position_order'] = selected_players_df['position'].map({pos: i for i, pos in enumerate(position_order)})
    selected_players_df = selected_players_df.sort_values(['position_order', 'name'])
    
    for _, player in selected_players_df.iterrows():
        # Get player picture URL
        pic_url = player_pics.get(str(player['id']), "")
        
        row = {
            'Photo': pic_url,
            'Name': player['name'],
            'Position': player['position'],
            'Team': player['team_name'],
            'Price': f"£{player['price']:.1f}m",
            'Points': f"{player['proj_points']:.0f}",
            'Fixture Difficulty': f"{player['avg_fixture_difficulty_5']:.1f}",
            'Next 5 Fixtures': player['next_5_fixtures']
        }
        
        # Add conditional columns based on weightings
        if solution.get('fixture_weighting', 0) > 0:
            row['Fixture-Adj Points'] = f"{player['fixture_adjusted_points']:.1f}"
        
        if solution.get('last_season_weighting', 0) > 0:
            row['Current PPG'] = f"{player['current_points_per_gw']:.1f}"
            row['Last Season PPG'] = f"{player['last_season_points_per_gw']:.1f}"
            row['History-Adj Points'] = f"{player['last_season_adjusted_points']:.1f}"
        
        display_data.append(row)
    
    df_display = pd.DataFrame(display_data)
    
    # Style the dataframe
    def style_position(val):
        color_map = {
            'GKP': 'background-color: #ffeb3b; color: black',
            'DEF': 'background-color: #4caf50; color: white',
            'MID': 'background-color: #2196f3; color: white',
            'FWD': 'background-color: #f44336; color: white'
        }
        return color_map.get(val, '')
    
    # Configure column types, especially the Photo column as ImageColumn
    column_config = {
        "Photo": st.column_config.ImageColumn(
            "Photo",
            help="Player photo",
            width="small"
        )
    }
    
    # Style the dataframe and show with image column
    styled_df = df_display.style.applymap(style_position, subset=['Position'])
    st.dataframe(
        df_display, 
        use_container_width=True, 
        hide_index=True,
        column_config=column_config,
        height=len(df_display) * 35 + 40
    )
    
    if params_changed and auto_refresh:
        st.info("🔄 Parameters changed - optimization will run automatically")

else:
    # Initial state - show instructions
    st.markdown("""
    ## 🚀 Getting Started
    
    1. **Adjust parameters** in the sidebar:
       - Choose optimization objective (maximize points vs maximize spend)
       - Set fixture difficulty weighting (0.0 = ignore, 1.0 = heavy influence)
       - Set last season weighting (0.0 = ignore history, 1.0 = heavy historical influence)
       - Configure player selection constraints
    
    2. **Click "Optimize Team"** to run the algorithm
    
    3. **Review results** including:
       - Optimal 15-player squad
       - Cost breakdown and points projection
       - Team and position distributions
       - Validation against FPL rules
    
    ## 📊 Features
    
    - **Integer Linear Programming**: Uses OR-Tools for mathematically optimal solutions
    - **Multi-objective**: Balance current form, fixtures, and historical performance
    - **FPL Constraints**: Respects budget, positions, and club limits
    - **Flexible Filtering**: Include/exclude rotation players, injury risks
    - **Export Ready**: Get player IDs and CSV downloads
    
    ## 🔧 Requirements
    
    Make sure you have:
    - FPL data files in `fpl_data/` directory
    - Run `process_fpl_data.py` to get latest data
    - OR-Tools installed: `uv add ortools`
    - Streamlit installed: `uv add streamlit`
    """)
    
    # Show example parameters
    with st.expander("💡 Example Parameter Combinations"):
        st.markdown("""
        **Conservative (Current Form Focus):**
        - Fixture Weighting: 0.0
        - Last Season Weighting: 0.0
        - All constraints enabled
        
        **Balanced Approach:**
        - Fixture Weighting: 0.3
        - Last Season Weighting: 0.4
        - Regular starters only
        
        **Historical Focus:**
        - Fixture Weighting: 0.1
        - Last Season Weighting: 0.7
        - Allow rotation players
        
        **Fixture-Heavy:**
        - Fixture Weighting: 0.8
        - Last Season Weighting: 0.2
        - Exclude injury risks
        """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit and OR-Tools | FPL Team Optimization Dashboard")