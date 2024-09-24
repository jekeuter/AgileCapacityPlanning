import pandas as pd
import streamlit as st

def load_team_data(file_path, sheet_name):
    try:
        # Load the data from the specified sheet
        data = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Check for required columns
        required_columns = ["Team Name", "PI", "Approach"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing columns in data: {missing_columns}")
        
        return data
    except Exception as e:
        print(f"Failed to load team data: {e}")
        return None

def load_team_member_data(file_path, sheet_name):
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def load_capability_data(file_path, sheet_name):
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def save_data(file_path, sheet_name, data):
    try:
        # Ensure data is a DataFrame
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Data must be a pandas DataFrame")
        
        # Load the existing Excel file
        with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            # Write the DataFrame to the specified sheet
            data.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Data saved to {file_path} in sheet {sheet_name}")
    except Exception as e:
        print(f"Error saving data: {e}")
        raise e

def get_latest_team_data(file_path, team_name, sheet_name):
    data = load_team_data(file_path, sheet_name)
    if data is None:
        return None
    team_data = data[data["Team Name"] == team_name]
    if not team_data.empty:
        latest_pi = team_data["PI"].max()
        latest_data = team_data[team_data["PI"] == latest_pi].iloc[0]
        return latest_data
    else:
        return None

import pandas as pd

def update_team_data(file_path, new_data, sheet_name):
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            existing_data = pd.read_excel(writer, sheet_name=sheet_name)

            # Ensure the DataFrame columns are of the correct type
            column_types = {
                "Average Velocity": float,
                "Average Duration": float,
                "Average Team Members": int,
                "SP Focus Factor": float,
                "Approach": str
            }
            for column, dtype in column_types.items():
                if column in existing_data.columns:
                    existing_data[column] = existing_data[column].astype(dtype)
            
            # Check if the entry already exists
            mask = (existing_data['PI'] == new_data['PI']) & (existing_data['Team Name'] == new_data['Team Name'])
            if not existing_data.loc[mask].empty:
                # Explicitly cast the new data to match expected types
                for key, value in new_data.items():
                    new_data[key] = dtype(value) if (key in column_types and (dtype := column_types[key])) else value
                
                existing_data.loc[mask, list(new_data.keys())] = list(new_data.values())
            else:
                # Convert new_data to DataFrame ensuring the types
                new_df = pd.DataFrame([new_data])
                for column, dtype in column_types.items():
                    new_df[column] = new_df[column].astype(dtype)

                existing_data = pd.concat([existing_data, new_df], ignore_index=True)

            # Save the updated DataFrame back to the same sheet in Excel
            existing_data.to_excel(writer, sheet_name=sheet_name, index=False)

    except Exception as e:
        print(f"Error updating data: {e}")



def load_team_names(file_path, sheet_name):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        team_names = df.iloc[:, 0].tolist()
        return team_names
    except Exception as e:
        raise e

def load_pi_options(file_path, sheet_name):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        pi_options = df.iloc[:, 0].tolist()
        return pi_options
    except Exception as e:
        raise e

def load_portfolio_options(file_path, sheet_name):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        portfolio_options = df.iloc[:, 0].tolist()
        return portfolio_options
    except Exception as e:
        raise e

def get_team_members(file_path, sheet_name, team_name, pi):
    data = load_team_member_data(file_path, sheet_name)
    if data is None:
        st.error("Failed to load team members data.")
        return []
    
    team_data = data[(data["Team Name"] == team_name) & (data["PI"] == pi)]
    if team_data.empty:
        return []
    
    team_members = []
    for _, row in team_data.iterrows():
        team_members.append({
            "name": row["Name"],
            "role": row["Role"],
            "hours": row["Hours"],
            "fte": row["FTE"],
            "days_off": [
                row["Days Off Sprint 1"],
                row["Days Off Sprint 2"],
                row["Days Off Sprint 3"],
                row["Days Off Sprint 4"],
                row["Days Off Sprint 5"]
            ],
            "sp_focus_factor": row.get("SP Focus Factor (%)", 0.0),  # Default to 0.0 if not present
            "multiplier": row.get("Multiplier", 1.0)  # Default to 1.0 if not present
        })
    return team_members

def load_team_velocity_data(file_path, velocity_sheet_name):
    try:
        data = pd.read_excel(file_path, sheet_name=velocity_sheet_name)
        return data
    except Exception as e:
        st.error(f"Error loading team velocity data: {e}")
        return None
    

def calculate_average_team_members(file_path, team_name, pi, sheet_name):
    try:
        data = pd.read_excel(file_path, sheet_name=sheet_name)
        filtered_data = data[(data["Team Name"] == team_name) & (data["PI"] == f"PI {pi}")]
        if not filtered_data.empty:
            return filtered_data['Team Members'].mean()
        return 0  # Return 0 if no data available
    except Exception as e:
        st.error(f"Failed to calculate average team members: {e}")
        return 0

def load_role_relevance(file_path, sheet_name, team_name, pi):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    relevance_data = df[(df["Team Name"] == team_name) & (df["PI"] == pi)]
    return relevance_data.set_index("Role")["Relevant"].to_dict()

def save_role_relevance(file_path, sheet_name, team_name, pi, role_relevance_dict):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    relevance_data = pd.DataFrame([
        {"Team Name": team_name, "PI": pi, "Role": role, "Relevant": relevant}
        for role, relevant in role_relevance_dict.items()
    ])
    df = df[~((df["Team Name"] == team_name) & (df["PI"] == pi))]
    df = pd.concat([df, relevance_data], ignore_index=True)
    save_data(file_path, sheet_name, df)