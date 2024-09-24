import streamlit as st
import pandas as pd
import yaml
from streamlit_authenticator import Authenticate
from team_data_ui import manage_team_data_ui
from team_member_data_ui import manage_team_member_ui
from capability_data_ui import capability_data_ui
from pi_dashboard_ui import pi_dashboard_ui
from data_management import load_team_names, load_pi_options, load_portfolio_options, load_role_relevance, save_role_relevance
from auth import load_auth_config, create_authenticator, save_auth_config

st.set_page_config(layout="wide")

# File path for the data
file_path = r"C:\Coding Projects\streamlit_capa_planning\test_data.xlsx"
team_data_sheet_name = "team_data"
team_member_sheet_name = "team_member_data"
team_velocity_sheet_name = "team_velocity"
team_sheet_name = "team_dropdown"
pi_sheet_name = "pi_dropdown"
portfolio_sheet_name = "portfolio_dropdown"
role_sheet_name = "role_dropdown"
approach_sheet_name = "approach_dropdown"
capability_sheet_name = "capability_data"
role_relevance_sheet_name = "role_relevance"

# Load custom CSS file
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("styles.css")

# Load the configuration for authentication
config_file = 'auth_config.yaml'
config = load_auth_config(config_file)

# Create an authentication object
authenticator = create_authenticator(config)

# Authenticate the user
name, authentication_status, username = authenticator.login()

if authentication_status:
    st.sidebar.title(f"Welcome {name}")
    authenticator.logout('Logout', 'sidebar')

    # Retrieve the user's role
    user_role = config['credentials']['usernames'][username]['role']
    print(f"User Role: {user_role}")

    # Title of the app
    st.title("Agile Capacity Planning")

    # Toggle to show help texts
    if 'show_help_texts' not in st.session_state:
        st.session_state['show_help_texts'] = False
    st.sidebar.markdown("## 🆘 Help")
    st.session_state['show_help_texts'] = st.sidebar.toggle("Show Help Texts", value=st.session_state['show_help_texts'])

    # Load PI options
    pi_options = load_pi_options(file_path, pi_sheet_name)
    st.sidebar.markdown("## 📅 PI Selection")
    selected_pi = st.sidebar.selectbox("Select PI", pi_options, key="selected_pi")

    # Planning horizon
    st.sidebar.markdown("## 🌅 Planning Horizon")
    planning_horizon = st.sidebar.selectbox("Select the Planning Horizon", ["PI", "Portfolio"], help="The Planning Horizon determines the scope of the capacity planning. Select 'PI' for team-level capacity planning within a specific Program Increment (PI), or select 'Portfolio' for high-level capacity planning across multiple PIs.")

    if planning_horizon == "PI":
        with st.sidebar:
            teams = load_team_names(file_path, team_sheet_name)
            selected_team = st.selectbox("Select Team", teams, key="selected_team", help="Select the team, you want to validate the capacity. You will see only the teams you are assigned / obliged to.")
            st.sidebar.markdown("## ⚙️ Base Settings")
            with st.sidebar.expander("Team Settings"):
                avg_duration = st.number_input("Average Duration of a Sprint (days)", min_value=0.0, value=10.0, step=1.0, disabled=(user_role == "Viewer"), help="The number of working days in a sprint.")
                sp_conversion = st.number_input("Hours to Story Points Conversion (Hours/1 SP)", min_value=0.0, value=8.0, step=1.0, disabled=(user_role == "Viewer"), help="Select the team, you want to validate the capacity. You will see only the teams you are assigned / obliged to.")
                pi_buffer = st.slider("PI Buffer (%)", min_value=0.0, max_value=1.0, value=0.1, step=0.05, disabled=(user_role == "Viewer"), help="Select a buffer you want to apply to the total PI capacity.")
            with st.sidebar.expander("Team Member Settings"):
                fte = st.slider("Default FTE", min_value=0.0, max_value=1.0, value=1.0, step=0.05, disabled=(user_role == "Viewer"), help="Select the default full time equivalent that applies to the team members. 80% means the member works 4 of 5 days a week for your team.")
                hours = st.number_input("Default Business Hours", min_value=0.0, value=8.0, step=1.0, disabled=(user_role == "Viewer"), help="Specify the default contractual hours a member works on a given business day. 4 hours means, the person works in 50% part time.")
            with st.sidebar.expander("Role Relevance"):
                st.info("Select the Story Point relevant roles, that impact the capacity. If a role is not SP-relevant, the availabilities do not influence the team capacity.")
                role_relevance = load_role_relevance(file_path, role_relevance_sheet_name, selected_team, selected_pi)
                role_data = pd.read_excel(file_path, role_sheet_name)
                role_emoji_dict = pd.Series(role_data.Emoji.values, index=role_data.Role).to_dict()
                # Display checkboxes for each role
                role_relevance_dict = {}
                for role in role_emoji_dict.keys():
                    role_relevance_dict[role] = st.checkbox(f"{role_emoji_dict[role]} {role}", value=role_relevance.get(role, role in ["Developer", "Tester"]), disabled=(user_role == "Viewer"))
                # Save role relevance
                if st.button("Save Role Relevance", disabled=(user_role == "Viewer")):
                    save_role_relevance(file_path, role_relevance_sheet_name, selected_team, selected_pi, role_relevance_dict)
                    st.success("Role relevance updated successfully!")

        # Tabs for navigation under PI Planning
        tabs = st.tabs(["Manage Team Data", "Enter Team Member Data", "Dashboard"])
        with tabs[0]:
            manage_team_data_ui(file_path, team_data_sheet_name, team_velocity_sheet_name, selected_team, selected_pi, avg_duration, team_member_sheet_name, sp_conversion, user_role)
        with tabs[1]:
            manage_team_member_ui(file_path, team_member_sheet_name, role_sheet_name, selected_team, selected_pi, fte, hours, user_role)
        with tabs[2]:
            pi_dashboard_ui(file_path, team_member_sheet_name, selected_team, selected_pi, team_data_sheet_name, avg_duration, sp_conversion, pi_buffer, role_relevance_dict, user_role)

    elif planning_horizon == "Portfolio":
        with st.sidebar:
            portfolio_options = load_portfolio_options(file_path, portfolio_sheet_name)
            selected_area = st.selectbox("Select Area", portfolio_options, key="selected_area")
            st.sidebar.markdown("## ⚙️ Base Settings")
            with st.sidebar.expander("Portfolio Settings"):
                enabler_blocker = st.slider("Blocker for Dependencies per PI (%)", min_value=0.0, max_value=1.0, value=0.1, step=0.05)
                uncertainty_buffer = st.slider("Uncertainty Buffer per PI (%)", min_value=0.0, max_value=1.0, value=0.05, step=0.05)

        # Tabs for navigation under Portfolio Planning
        tabs = st.tabs(["Portfolio Overview", "Portfolio Capacity"])
        with tabs[0]:
            capability_data_ui(file_path, capability_sheet_name, selected_area, pi_options, selected_pi)
        with tabs[1]:
            st.write("Portfolio Analysis Content")

elif authentication_status == False:
    st.error('Username/password is incorrect')
    try:
        email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user(location='main', pre_authorization=False)
        if email_of_registered_user:
            save_auth_config(config, config_file)
            st.success('User registered successfully')
    except Exception as e:
        st.error(e)

elif authentication_status == None:
    st.warning('Please enter your username and password')
    try:
        email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user(location='main', pre_authorization=False)
        if email_of_registered_user:
            save_auth_config(config, config_file)
            st.success('User registered successfully')
    except Exception as e:
        st.error(e)
