import streamlit as st
import pandas as pd
from data_management import load_team_member_data, save_data

def manage_team_member_ui(file_path, sheet_name, role_sheet_name, team_name, pi, fte, hours, user_role):
    # Fetch team data
    team_data_df = pd.read_excel(file_path, 'team_data')
    team_member_data = pd.read_excel(file_path, sheet_name)
    team_data = team_data_df[(team_data_df['Team Name'] == team_name) & (team_data_df['PI'] == pi)]

    team_member_df = load_team_member_data(file_path, sheet_name)
    team_member_data = team_member_df[(team_member_df['Team Name'] == team_name) & (team_member_df['PI'] == pi)]
    
    # Load role options
    role_data = pd.read_excel(file_path, role_sheet_name)
    # Create a dictionary for role emojis
    role_emoji_dict = pd.Series(role_data.Emoji.values, index=role_data.Role).to_dict()

    # Create role display options with emojis
    role_display_options = [f"{emoji} {role}" for role, emoji in role_emoji_dict.items()]
    role_to_emoji_map = {f"{emoji} {role}": role for role, emoji in role_emoji_dict.items()}

    if not team_data.empty:
        approach = team_data.iloc[0]['Approach']
        sp_focus_factor = float(team_data.iloc[0].get('SP Focus Factor', 0.0))
    else:
        approach = None
        sp_focus_factor = 0.0
        st.error("No data entry exists for the team in this PI. Please switch to the Team Data Tab and add the respective entry first. Then continue here.")

    # Section to copy data from other PIs
    if not team_data.empty:
        with st.expander("📋 Copy Data from Other PI"):
            available_pis = team_member_data[team_member_data['Team Name'] == team_name]['PI'].unique().tolist()
            if pi in available_pis:
                available_pis.remove(pi)  # Remove current PI from selection if present
            pi_selector = st.selectbox('Select a PI to copy data from:', available_pis)

            if st.button('Copy PI Data'):
                copy_pi_data(file_path, sheet_name, team_name, pi_selector, pi, team_data)

        show_new_member_form = st.toggle("Add New Team Member", value=team_member_data.empty)
        if show_new_member_form:
            st.subheader(f"Add New Team Members for PI {pi}")
            # Form to add new team members
            with st.form("new_member_form"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("##### 👤 Base Info")
                    new_name = st.text_input("Team Member Name")
                    selected_role_with_emoji = st.selectbox("Team Member Role", role_display_options)
                    selected_role = role_to_emoji_map[selected_role_with_emoji]  # Get the actual role without emoji
                    new_hours = st.number_input("Contracted Business Hours", value=hours, min_value=0.0, max_value=10.0)
                    new_fte = st.slider("FTE (%)", value=fte, min_value=0.0, max_value=1.0, step=0.01)
                    new_focus_factor = st.slider("SP Focus Factor (%)", value=sp_focus_factor, min_value=0.0, max_value=1.0, step=0.01, disabled=(approach == "Velocity"))
                    new_status = st.selectbox("Status", ["Onboarding", "Offboarding", "Active"], index=2)

                with col2:
                    st.markdown("##### 🏖️ Days Off per Sprint")
                    new_days_off = [st.number_input(f"Days Off Sprint {i+1}", value=0, min_value=0) for i in range(5)]
                    if new_status == "Onboarding":
                        new_multiplier = st.slider("Multiplier", min_value=0.0, max_value=2.0, value=0.25, step=0.05)
                    elif new_status == "Offboarding":
                        new_multiplier = st.slider("Multiplier", min_value=-2.0, max_value=0.0, value=-0.75, step=0.05)
                    else:
                        new_multiplier = st.slider("Multiplier", min_value=0.0, max_value=2.0, value=1.0, step=0.05)
                submit_button = st.form_submit_button("Add Member")

            if submit_button:
                new_member_data = {
                    "Team Name": team_name, "PI": pi, "Name": new_name, "Role": selected_role,
                    "Hours": new_hours, "FTE": new_fte,
                    **{f"Days Off Sprint {i+1}": new_days_off[i] for i in range(5)},
                    "SP Focus Factor (%)": new_focus_factor if approach == "Percentage" else sp_focus_factor,
                    "Status": new_status,
                    "Multiplier": new_multiplier
                }
                add_new_team_member(file_path, sheet_name, new_member_data)

        # Display existing team members
        num_team_members = len(team_member_data)
        show_members = st.toggle(f"Manage Existing Team Members ({num_team_members})", value=not team_member_data.empty)
        if show_members:
            st.subheader(f"Existing Team Members for PI {pi}")
            display_team_members(file_path, sheet_name, team_name, pi, role_emoji_dict, role_display_options, role_to_emoji_map, approach)

def add_new_team_member(file_path, sheet_name, member_data):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    new_member_df = pd.DataFrame([member_data])
    df = pd.concat([df, new_member_df], ignore_index=True)
    save_data(file_path, sheet_name, df)
    st.success("Added new team member!")

def display_team_members(file_path, sheet_name, team_name, pi, role_emoji_dict, role_display_options, role_to_emoji_map, approach):
    df = load_team_member_data(file_path, sheet_name)
    team_df = df[(df['Team Name'] == team_name) & (df['PI'] == pi)]
    # Normalize FTE values to a range of 0-1
    team_df['FTE'] = team_df['FTE'] / 100.0 if team_df['FTE'].max() > 1 else team_df['FTE']

    # Adding columns for visualization
    days_off_columns = [f"Days Off Sprint {i}" for i in range(1, 6)]
    team_df['Total Days Off'] = team_df[days_off_columns].sum(axis=1)
    team_df['Days Off Bar'] = team_df[days_off_columns].apply(lambda row: list(row), axis=1)

    # Define the column configuration for visualization
    column_config = {
        # Convert string representation of list into actual lists
        "Name": st.column_config.TextColumn("Name", width="medium"),
        "Role": st.column_config.TextColumn("Role", width="medium"),
        "Days Off Bar": st.column_config.BarChartColumn(
            "Days Off per Sprint",
            help="Visual representation of days off per sprint",
            width="medium",
            y_min=0,
            y_max=10  # Adjust y_max dynamically based on the data
        )
    }

    # Display the DataFrame with the visualization
    st.dataframe(
        team_df[["Name", "Role", "Days Off Bar"]],
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )

    # Display each team member with details
    st.markdown("##### Adjust details")
    for index, row in team_df.iterrows():
        print(f"Row FTE value type: {type(row['FTE'])}")  # Debug print to check the type of FTE
        print(f"Row FTE value: {row['FTE']}")  # Debug print to check the value of FTE
        # Ensure the FTE value is a float
        if isinstance(row['FTE'], list):
            row['FTE'] = row['FTE'][0] if row['FTE'] else 0.0
        
        row['FTE'] = float(row['FTE']) if not isinstance(row['FTE'], float) else row['FTE']

        # Get emoji from dictionary
        emoji = role_emoji_dict.get(row['Role'], "➡️")  # Default emoji if not found
        role_display = f"{emoji} {row['Role']}" 
        with st.expander(f"{row['Name']} - {role_display} - Total Days Off: {row['Total Days Off']}"):
            col1, col2 = st.columns(2)
            with col1:
                updated_name = st.text_input("Name", value=row['Name'], key=f"name_{index}")
                # Dropdown for role with emoji
                current_role_display = f"{emoji} {row['Role']}"
                updated_role_display = st.selectbox("Role", role_display_options, index=role_display_options.index(current_role_display), key=f"role_{index}")
                updated_role = role_to_emoji_map[updated_role_display]  # Map back to the original role for storage
                updated_hours = st.number_input("Hours", value=row['Hours'], key=f"hours_{index}")
                updated_fte = st.slider("FTE (%)", value=row['FTE'], key=f"fte_{index}", min_value=0.0, max_value=1.0, step=0.01)
                updated_focus_factor = st.slider("SP Focus Factor (%)", value=row.get('SP Focus Factor (%)', 0.0), key=f"focus_{index}", disabled=(approach == "Velocity"), step=0.01),
                current_status = row['Status']
                updated_status = st.selectbox("Status", ["Onboarding", "Offboarding", "Active"], index=["Onboarding", "Offboarding", "Active"].index(current_status), key=f"status_{index}")
            with col2:
                updated_days_off = [st.number_input(f"Days Off Sprint {i+1}", value=row.get(f"Days Off Sprint {i+1}", 0), key=f"days_{index}_{i}") for i in range(5)]
                updated_multiplier = st.slider("Multiplier", min_value=-2.0, max_value=2.0, value=row.get('Multiplier', 1.0), step=0.05, key=f"multiplier_{index}")
            if st.button('Update', key=f'update{index}'):
                update_member_data = {
                    "Name": updated_name,
                    "Role": updated_role,  # Store without emoji
                    "Hours": updated_hours,
                    "FTE": updated_fte,
                    **{f"Days Off Sprint {i+1}": updated_days_off[i] for i in range(5)},
                    "SP Focus Factor (%)": updated_focus_factor,
                    "Status": updated_status,
                    "Multiplier": updated_multiplier
                }
                update_team_member(file_path, sheet_name, df, row.name, update_member_data)
            if st.button('Delete', key=f'delete{index}'):
                delete_team_member(file_path, sheet_name, df, row.name)

def copy_pi_data(file_path, sheet_name, team_name, source_pi, target_pi, team_data):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    
    source_data = df[(df['Team Name'] == team_name) & (df['PI'] == source_pi)]
    target_data = df[(df['Team Name'] == team_name) & (df['PI'] == target_pi)]

    # Check if target PI already has data
    if not target_data.empty:
        if not st.confirm('Target PI already has data. Do you want to overwrite?'):
            return

    # Prepare new data with updated PI
    new_data = source_data.copy()
    new_data['PI'] = target_pi  # Update the PI to the target PI

    # Set all "Days Off" columns to zero
    days_off_columns = [col for col in new_data.columns if "Days Off" in col]
    new_data[days_off_columns] = 0

    # Update SP Focus Factor according to the team data for the target PI
    if not team_data.empty:
        new_sp_focus_factor = float(team_data.iloc[0].get('SP Focus Factor', 0.0))
        new_data['SP Focus Factor (%)'] = new_sp_focus_factor

    # Remove existing data for target PI
    df = df[df['PI'] != target_pi]

    # Append new data
    df = pd.concat([df, new_data], ignore_index=True)

    # Save the updated data
    save_data(file_path, sheet_name, df)
    st.success(f"Data from PI {source_pi} successfully copied to PI {target_pi} with updated Days Off and SP Focus Factor: {new_sp_focus_factor:.2%}.")

def update_team_member(file_path, sheet_name, df, index, member_data):
    for key, value in member_data.items():
        df.at[index, key] = value

    # Save the updated DataFrame to Excel using the save_data function
    save_data(file_path, sheet_name, df)
    
    # Refresh the UI to reflect the changes
    st.rerun()

def delete_team_member(file_path, sheet_name, df, index):
    # Drop the row and reset the index
    df = df.drop(index).reset_index(drop=True)

    # Save the updated DataFrame back to the Excel file using the save_data function
    save_data(file_path, sheet_name, df)

    # Refresh the UI to reflect the changes
    st.rerun()

def confirm_action(key, message, on_confirm, on_cancel=None):
    # Create temporary session state variables if they don't exist
    if key not in st.session_state:
        st.session_state[key] = {'confirm': False, 'run': False}

    if not st.session_state[key]['confirm']:
        # Show confirmation buttons
        col1, col2 = st.columns(2)
        if col1.button('Confirm', key=f'{key}_confirm'):
            st.session_state[key]['confirm'] = True
            st.session_state[key]['run'] = True  # Proceed to action
        if col2.button('Cancel', key=f'{key}_cancel'):
            st.session_state[key]['confirm'] = True
            if on_cancel:
                on_cancel()  # Optional: Run a function when cancelled
    else:
        if st.session_state[key]['run']:
            on_confirm()  # Run the confirmation action
        else:
            st.write('Action cancelled.')
