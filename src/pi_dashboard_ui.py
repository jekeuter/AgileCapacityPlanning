import streamlit as st
import pandas as pd
from data_management import load_team_data, load_team_names, load_pi_options, get_team_members

@st.cache_data
def get_cached_team_names(file_path, team_sheet_name):
    return load_team_names(file_path, team_sheet_name)

@st.cache_data
def get_cached_pi_options(file_path, pi_sheet_name):
    return load_pi_options(file_path, pi_sheet_name)

@st.cache_data
def get_cached_team_members(file_path, team_member_sheet_name, team_name, pi):
    return get_team_members(file_path, team_member_sheet_name, team_name, pi)

def calculate_capacity(team_members, approach, sp_conversion, sprint_duration, num_sprints, role_relevance_dict):
    capacities = []
    for member in team_members:
        role = member["role"]
        if not role_relevance_dict.get(role, False):
            member_capacities = [0] * num_sprints
        else:
            sp_focus_factor = member["sp_focus_factor"]
            hours = member["hours"]
            multiplier = member.get("multiplier", 1.0)
            fte = member["fte"]
            member_capacities = []
            if approach == "Velocity":
                for sprint in range(num_sprints):
                    days_off = member["days_off"][sprint]
                    actual_capacity = (sprint_duration - days_off) * fte * sp_focus_factor * multiplier
                    member_capacities.append(actual_capacity)
            elif approach == "Percentages":
                for sprint in range(num_sprints):
                    days_off = member["days_off"][sprint]
                    hours_capacity = (sprint_duration - days_off) * hours * fte
                    actual_capacity = (hours_capacity / sp_conversion) * sp_focus_factor * multiplier
                    member_capacities.append(actual_capacity)
        capacities.append(member_capacities)
    return capacities

def calculate_team_capacity(team_members, pi_buffer, approach, sp_conversion, sprint_duration=10, num_sprints=5, role_relevance_dict={}):
    member_capacities = calculate_capacity(team_members, approach, sp_conversion, sprint_duration, num_sprints, role_relevance_dict)
    total_capacity_per_sprint_without_buffer = [sum(sprint) for sprint in zip(*member_capacities)]
    total_capacity_per_sprint_with_buffer = [capacity * (1 - pi_buffer) for capacity in total_capacity_per_sprint_without_buffer]
    total_capacity_pi_without_buffer = sum(total_capacity_per_sprint_without_buffer)
    total_capacity_pi_with_buffer = sum(total_capacity_per_sprint_with_buffer)
    return member_capacities, total_capacity_per_sprint_without_buffer, total_capacity_per_sprint_with_buffer, total_capacity_pi_without_buffer, total_capacity_pi_with_buffer

def get_team_pi_data(data, team_name, pi):
    team_pi_data = data[(data["Team Name"] == team_name) & (data["PI"] == pi)]
    if not team_pi_data.empty:
        return team_pi_data.iloc[0]
    else:
        return None

def pi_dashboard_ui(file_path, team_member_sheet_name, team_name, pi, team_data_sheet_name, avg_duration, sp_conversion, pi_buffer, role_relevance_dict, user_role):
    st.header(f"Capacity Overview for PI - {pi}")

    team_data = load_team_data(file_path, team_data_sheet_name)
    team_pi_data = get_team_pi_data(team_data, team_name, pi)
    approach = team_pi_data["Approach"] if team_pi_data is not None else "Velocity"

    team_members = get_cached_team_members(file_path, team_member_sheet_name, team_name, pi)
    
    if not team_members:
        st.error("No team members found for the selected team and PI.")
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        return
        
    
    member_capacities, total_capacity_per_sprint_without_buffer, total_capacity_per_sprint_with_buffer, total_capacity_pi_without_buffer, total_capacity_pi_with_buffer = calculate_team_capacity(team_members, pi_buffer, approach, sp_conversion, role_relevance_dict=role_relevance_dict)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Total Capacity for PI (without buffer)", value=round(total_capacity_pi_without_buffer, 1))
    col2.metric(label="Total Capacity for PI (with buffer)", value=round(total_capacity_pi_with_buffer,1), delta=f"{pi_buffer * -100:.0f}% PI Buffer")
    with col4:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    member_names = [member["name"] for member in team_members]
    member_roles = [member["role"] for member in team_members]
    days_off_bar = [member["days_off"] for member in team_members]
    
    data = {"Team Member": member_names, "Role": member_roles, "Days Off Bar": days_off_bar}
    for sprint in range(len(member_capacities[0])):
        data[f"Sprint {sprint + 1} Capacity (SP)"] = [capacities[sprint] for capacities in member_capacities]
    
    df = pd.DataFrame(data)
    
    totals = ["Total", "", [0] * 5] + [df[f"Sprint {i + 1} Capacity (SP)"].sum() for i in range(len(member_capacities[0]))]
    df.loc[len(df)] = totals

    column_config = {
        "Team Member": st.column_config.TextColumn("Team Member", width="medium"),
        "Role": st.column_config.TextColumn("Role", width="medium"),
        "Days Off Bar": st.column_config.BarChartColumn(
            "Days Off per Sprint",
            help="Visual representation of days off per sprint",
            width="medium",
            y_min=0,
            y_max=10
        )
    }

    st.subheader("Detailed Capacity per Team Member")
    st.dataframe(df, column_config=column_config, use_container_width=True, hide_index=True)

    sprint_df = pd.DataFrame({
        "Sprint": [f"Sprint {i + 1}" for i in range(len(total_capacity_per_sprint_without_buffer))],
        "Capacity with Buffer (SP)": total_capacity_per_sprint_with_buffer,
        "Buffer (SP)": [total_capacity_per_sprint_without_buffer[i] - total_capacity_per_sprint_with_buffer[i] for i in range(len(total_capacity_per_sprint_with_buffer))]
    })
    sprint_df = sprint_df.melt(id_vars="Sprint", var_name="Capacity Type", value_name="SP")

    st.subheader("Total Capacity per Sprint (including Buffer)")
    st.bar_chart(sprint_df.pivot_table(index="Sprint", columns="Capacity Type", values="SP"))

    role_sp = {}
    for member, capacities in zip(team_members, member_capacities):
        role = member["role"]
        total_sp = sum(capacities)
        if role in role_sp:
            role_sp[role] += total_sp
        else:
            role_sp[role] = total_sp
    
    role_sp_df = pd.DataFrame(list(role_sp.items()), columns=["Role", "Total SP"])
    
    st.subheader("Total Story Points per Role")
    st.bar_chart(role_sp_df.set_index("Role"), horizontal=True)
