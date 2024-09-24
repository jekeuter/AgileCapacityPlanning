import streamlit as st
from data_management import load_team_data, load_team_velocity_data, load_team_member_data, save_data, get_latest_team_data, update_team_data

def calculate_avg_velocity(velocity_data, team_name, pi, num_sprints):
    # Format the PI value to match the format in the dataframe
    formatted_pi = f"PI {pi}"
    
    # Filter data for the selected team
    team_data = velocity_data[velocity_data["Team"] == team_name]

    # Sorting by Year, PI and Sprint to ensure proper order
    team_data = team_data.sort_values(by=["Year", "PI", "Sprint"], ascending=[True, True, True])

    # Check if the desired PI has any data
    team_pi_data = team_data[team_data["PI"] == formatted_pi]

    if team_pi_data.empty:
        # Find the latest available PI and its data
        latest_pi_data = team_data.drop_duplicates("PI", keep='last')
        if latest_pi_data.empty:
            return 0, "No data available for the selected team.", ""

        # Use the latest PI available
        latest_pi = latest_pi_data.iloc[-1]
        team_pi_data = team_data[team_data["PI"] == latest_pi["PI"]]
    else:
        # Use the identified PI's data
        latest_pi = team_pi_data.iloc[-1]

    # Getting the index of the latest PI's latest sprint
    latest_sprint_index = team_data.index.get_loc(latest_pi.name)

    # Calculate the start index for fetching sprints, starting one before the latest
    start_index = max(0, latest_sprint_index - num_sprints)

    # Fetch the relevant sprints, excluding the very latest one
    relevant_sprints = team_data.iloc[start_index:latest_sprint_index]

    if relevant_sprints.empty:
        return 0, "Insufficient sprints data available for the selected PI.", ""

    avg_velocity = relevant_sprints["SprintVelocity"].mean()

    # Fetching start and end sprint details
    start_sprint = relevant_sprints.iloc[0]["Sprint"]
    end_sprint = relevant_sprints.iloc[-1]["Sprint"]

    # Constructing the message
    info_message = f"Average velocity calculated from {start_sprint} to {end_sprint} over {len(relevant_sprints)} sprints."
    
    return avg_velocity, "", info_message


def manage_team_data_ui(file_path, sheet_name, velocity_sheet_name, team_name, pi, avg_duration, team_member_sheet_name, sp_conversion, user_role):
    st.header(f"Manage Team Data - PI {pi}")
    
    # Load the data
    data = load_team_data(file_path, sheet_name)
    velocity_data = load_team_velocity_data(file_path, velocity_sheet_name)
    team_member_data = load_team_member_data(file_path, team_member_sheet_name)
    
    # Check if the data was loaded successfully
    if data is None or velocity_data is None:
        st.error("Failed to load team data. Please check the file and sheet names.")
        return
    
    # Function to get data for the selected PI and team
    def get_team_pi_data(data, team_name, pi):
        team_pi_data = data[(data["Team Name"] == team_name) & (data["PI"] == pi)]
        if not team_pi_data.empty:
            return team_pi_data.iloc[0]
        else:
            return None
    
    # Initialize session state for the selected PI
    if f"pi_{pi}_team_{team_name}" not in st.session_state:
        st.session_state[f"pi_{pi}_team_{team_name}"] = {
            "num_sprints": 6,
            "avg_velocity": 0.0,
            "avg_team_members": 0,
            "sp_focus_factor": 0.0,
            "approach": "Velocity"
        }
    
    # Get the data for the selected team and PI
    team_pi_data = get_team_pi_data(data, team_name, pi)
    latest_team_data = get_latest_team_data(file_path, team_name, sheet_name)

    
    if team_pi_data is None:
        # No data for the selected PI, so show default values
        latest_team_data = get_latest_team_data(file_path, team_name, sheet_name)
        if not data[data["Team Name"] == team_name].empty:
            latest_team_data = get_latest_team_data(file_path, team_name, sheet_name)
        button_text = "Save Team Data"
    else:
        # Data exists for the selected PI, so show that data
        st.session_state[f"pi_{pi}_team_{team_name}"]["avg_velocity"] = float(team_pi_data["Average Velocity"])
        st.session_state[f"pi_{pi}_team_{team_name}"]["avg_team_members"] = int(team_pi_data["Average Team Members"])
        
        # Ensure the approach is either "Percentages" or "Velocity"
        approach = team_pi_data.get("Approach", "Velocity")
        if approach not in ["Percentages", "Velocity"]:
            approach = "Velocity"
        st.session_state[f"pi_{pi}_team_{team_name}"]["approach"] = approach
        button_text = "Update Team Data"    

    # Display the form to enter the data
    approach = st.selectbox(
        "Approach", 
        ["Percentages", "Velocity"], 
        index=["Percentages", "Velocity"].index(st.session_state[f"pi_{pi}_team_{team_name}"]["approach"]), 
        key=f"approach_{pi}_{team_name}",
        help="Choose an approach for the capacity planning: 'Percentages' for individual relative measures for each team member or 'Velocity' to calculate the capacity based on the team's average velocity and team members.")
    if st.session_state['show_help_texts']:
        if approach == "Percentages": 
            st.info("This approach is used when you want to calculate the capacity based on daily story point focus percentages of individual team members.")
        elif approach == "Velocity":
            st.info("This approach is used when you want to calculate the capacity based on the team's average velocity and team members.")
    
    
    
    if approach == "Velocity":
        # Display the average velocity input field
        num_sprints = st.slider(
            "Number of Sprints to calculate Average Velocity", 
            min_value=1, 
            max_value=20, 
            value=6, 
            key=f"num_sprints_{pi}_{team_name}",
            help="Define the number of sprints across which you want to calculate the baseline average velocity.")
        # Calculate the average velocity based on the selected number of sprints
        avg_velocity, warning_message, info_message = calculate_avg_velocity(velocity_data, team_name, pi, num_sprints)
        if warning_message:
            st.warning(warning_message)
        else:
            st.info(info_message)  # Display a grey callout box with information about included sprints
        # Display the average velocity input field
        avg_velocity_input = st.number_input(
            "Average Velocity", 
            min_value=0.0, 
            value=float(avg_velocity), 
            key=f"avg_velocity_{pi}_{team_name}",
            help="The average velocity across the chosen number of sprints is used to calculate the daily focus factor below. You can ovverride this automatically calculated value as needed.")

        # Display the average team member input field
        avg_team_members = st.number_input(
            "Average Number of Team Members", 
            min_value=0, 
            value=int(st.session_state[f"pi_{pi}_team_{team_name}"]["avg_team_members"]), 
            key=f"avg_team_members_{pi}_{team_name}",
            help="Enter the average number of team members you had across the chosen number of sprints. It is used to calculate the daily focus factor below.")

        # Calculate SP Focus Factor
        if avg_duration > 0 and avg_team_members > 0:
            sp_focus_factor = avg_velocity_input / avg_duration / avg_team_members
        else:
            sp_focus_factor = 0.0

        st.session_state[f"pi_{pi}_team_{team_name}"]["sp_focus_factor"] = sp_focus_factor

        st.success(f"SP Focus Factor: **{sp_focus_factor:.2%}** of daily time available for story points per team member.")
    elif approach == "Percentages":
        # Display the story point conversion rate
        st.success(f"The available time of each team member will be converted with **{sp_conversion} hours per story point**.")
    
    # Button to save the data
    if st.button(button_text):
        new_data = {
            "PI": pi,
            "Team Name": team_name,
            "Average Velocity": avg_velocity_input,
            "Average Duration": avg_duration,
            "Average Team Members": avg_team_members,
            "SP Focus Factor": sp_focus_factor,
            "Approach": approach,
            "SP Conversion": sp_conversion
        }
        update_team_data(file_path, new_data, sheet_name)
        
        if approach == "Velocity":
            # Update SP Focus Factor for all team members in the team_member_data
            team_members_to_update = (team_member_data["Team Name"] == team_name) & (team_member_data["PI"] == pi)
            team_member_data.loc[team_members_to_update, "SP Focus Factor (%)"] = sp_focus_factor
            save_data(file_path, "team_member_data", team_member_data)
        
        st.rerun()  # Rerun the script to update the UI

    # Display the data for the selected team
    show_data = st.toggle("Show Team Data")
    if show_data:
        team_data = data[data["Team Name"] == team_name]
        if not team_data.empty:
            st.subheader(f"Data for {team_name}")
            st.dataframe(
                team_data.drop(columns=["Average Duration"]),
                hide_index=True
            )
    
    # Display the velocity data for the selected team
    show_velocity_data = st.toggle("Show Velocity Data")
    if show_velocity_data:
        team_velocity_data = velocity_data[velocity_data["Team"] == team_name]
        if not team_velocity_data.empty:
            st.subheader(f"Velocity Data for {team_name}")
            st.dataframe(
                team_velocity_data,
                hide_index=True
                )
            st.line_chart(team_velocity_data.set_index("Sprint")["SprintVelocity"])
