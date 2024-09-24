import streamlit as st
import pandas as pd
import numpy as np
import re
from data_management import load_capability_data, save_data

def capability_data_ui(file_path, capability_sheet_name, area, pi_options, selected_pi):
    st.header("Capability Data")
    
    # Load the data
    capability_data = load_capability_data(file_path, capability_sheet_name)
    if capability_data is None:
        st.error("Failed to load capability data.")
        return
    
    # Rename specific columns
    column_mapping = {
        "OD Business Priority": "Bus. Priority",
        "OD Actual Story Points": "Act. SP",
        "OD Planned Story Points": "Planned SP",
        "OD Budget Story Points": "Budget SP",
        "t_shirt_size": "T-Shirt",
        "Time Criticality WSJF": "WSJF Time",
        "Risk Reduction Opp. Enablement WSJF": "WSJF Risk",
        "Business Value WSJF": "WSJF Value",
        "Effort WSJF": "WSJF Effort"
    }
    capability_data.rename(columns=column_mapping, inplace=True)

    # Format columns
    capability_data["Start Date"] = pd.to_datetime(capability_data["Start Date"], errors="coerce").dt.date
    capability_data["Target Date"] = pd.to_datetime(capability_data["Target Date"], errors="coerce").dt.date
    capability_data["ID"] = capability_data["ID"].astype(str).str.split('.').str[0]
    capability_data["Link"] = capability_data["ID"].apply(lambda x: f"https://agco-dcx.visualstudio.com/ONE%20Digital/_workitems/edit/{x}")
    capability_data["Tags"] = capability_data["Tags"].str.replace(";", ",")
    capability_data["To be aligned"] = capability_data["To be aligned"].fillna(False).astype(bool)
    pi_columns = capability_data.columns[capability_data.columns.str.match(r"^PI \d{2}-0\d$")]
    capability_data[pi_columns] = capability_data[pi_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # Filter data based on the selected pi & area
    capability_data_filtered = capability_data[(capability_data["Tags"].str.contains(selected_pi)) & (capability_data["Area Path"].str.contains(area))].copy()
    capability_data_filtered["State"] = capability_data_filtered["State"].apply(state_to_emoji)

    # Convert PI columns to numeric, replacing non-numeric with NaN
    pi_columns = capability_data_filtered.columns[capability_data_filtered.columns.str.startswith('PI ')]
    capability_data_filtered[pi_columns] = capability_data_filtered[pi_columns].apply(pd.to_numeric, errors='coerce')

    # Display the data
    selected_capabilities = st.dataframe(
        capability_data_filtered,
        hide_index=True,
        column_order=["Link", "Title", "State", "WSJF", "Priority", "Bus. Priority", "Iteration Path", "Start Date", "Target Date", "Assigned To", "Tags", "To be aligned"],
        column_config={
            "Link": st.column_config.LinkColumn(
                "ID",
                validate="^https://[a-z]+\.visualstudio.com/ONE%20Digital/_workitems/edit/\d+$",
                display_text="https://agco-dcx.visualstudio\.com/ONE%20Digital/_workitems/edit/(\d+)$",
            ),
            "Title": st.column_config.TextColumn(
                "Title",
                width="large",
            ),         
            'WSJF': st.column_config.ProgressColumn(
                "WSJF",
                help="The Overall WSJF Score",
                format="%.1f",
                min_value=0,
                max_value=20,
            ),
            "Tags": st.column_config.ListColumn(
                "Tags",
                width="medium",
            ),
            "To be aligned": st.column_config.CheckboxColumn(
                "To be aligned",
                help="Check this box if the capability needs to be aligned with others.",
            ),
        },
        on_select="rerun",
        selection_mode="multi-row",
        use_container_width=True,
    )

    # Get the selected rows' indices in the filtered DataFrame
    selected_indices_filtered = selected_capabilities.selection.rows
    # Map these indices to the original DataFrame
    selected_indices_original = capability_data_filtered.index[selected_indices_filtered]

    # Show the selected rows in a separate table for WSJF details
    st.subheader("⚖️ WSJF Details")
    wsjf_df = capability_data.loc[selected_indices_original]
    wsjf_columns = [col for col in wsjf_df.columns if 'WSJF' in col]
    st.dataframe(
        wsjf_df[['ID'] + wsjf_columns],
        column_config={
            'WSJF': st.column_config.ProgressColumn(
                "WSJF",
                help="The Overall WSJF Score",
                format="%.1f",
                min_value=0,
                max_value=20,
            ),
            'WSJF Time': st.column_config.ProgressColumn(
                "WSJF Time",
                help="The WSJF Time",
                format="%.1f",
                min_value=0,
                max_value=20,
            ),
            'WSJF Risk': st.column_config.ProgressColumn(
                "WSJF Risk",
                help="The WSJF Risk",
                format="%.1f",
                min_value=0,
                max_value=20,
            ),
            'WSJF Value': st.column_config.ProgressColumn(
                "WSJF Value",
                help="The WSJF Value",
                format="%.1f",
                min_value=0,
                max_value=20,
            ),
            'WSJF Effort': st.column_config.ProgressColumn(
                "WSJF Effort",
                help="The WSJF Effort",
                format="%.1f",
                min_value=0,
                max_value=20,
            ),
        },
        hide_index=True,
        use_container_width=True,
    )

    # Show the selected rows in a separate table for SP & T-Shirt details
    st.subheader("👕 Story Point & T-Shirt Details")
    sp_tshirt_df = capability_data.loc[selected_indices_original]
    sp_tshirt_columns = [col for col in sp_tshirt_df.columns if 'SP' in col or 'T-Shirt' in col]
    st.dataframe(
        sp_tshirt_df[['ID'] + sp_tshirt_columns],
        hide_index=True,
        use_container_width=True,
    )

    # Show the selected rows in a separate table for Timeline details
    st.subheader("📆 Timeline Details")
    timeline_df = capability_data.loc[selected_indices_original]
    pi_column_config = create_pi_column_config(timeline_df, pi_options)
    timeline_columns = [col for col in timeline_df.columns if 'PI' in col or 'Status' in col]
    edited_timeline = st.data_editor(
        timeline_df[['ID'] + timeline_columns],
        column_config=pi_column_config,
        hide_index=True,
        use_container_width=True,
        disabled=["ID"]
    )

    # Ensure PI columns are numeric
    edited_timeline[pi_columns] = edited_timeline[pi_columns].apply(pd.to_numeric, errors='coerce')

    # If the sum of the edited PI columns is greater than the Budget SP for each ID, there should be a warning callout
    if edited_timeline is not None:
        edited_timeline["Total PI SP"] = edited_timeline.filter(regex=r"^PI \d{2}-0\d$").sum(axis=1)
        edited_timeline["Budget SP"] = capability_data["Budget SP"]
        edited_timeline["Status"] = np.where(edited_timeline["Total PI SP"] > edited_timeline["Budget SP"], "Over Budget", "Within Budget")
        over_budget_ids = edited_timeline[edited_timeline["Status"] == "Over Budget"]["ID"].tolist()
        if over_budget_ids:
            st.error(f"The sum of the PI columns exceeds the Budget SP for the following IDs: {', '.join(over_budget_ids)}")
        elif edited_timeline["Total PI SP"].sum() == 0:
            st.warning("You have not yet distributed any SP to the PI columns.")
        else:
            over_budget_ids = edited_timeline[edited_timeline["Status"] == "Over Budget"]["ID"].tolist()
            if over_budget_ids:
                st.error(f"The sum of the PI columns exceeds the Budget SP for the following IDs: {', '.join(over_budget_ids)}")
            else:
                st.success("The sum of the PI columns is within the Budget SP for all IDs.")

    # Show the selected rows in a separate table for Comments
    st.subheader("🗣️ Comments")
    comment_df = capability_data.loc[selected_indices_original]
    comment_columns = [col for col in comment_df.columns if 'Comment' in col or 'To be aligned' in col]
    edited_comments = st.data_editor(
        comment_df[['ID'] + comment_columns],
        column_config={
            "Comment": st.column_config.TextColumn(
                "Comment",
                width="medium",
            ),
            "To be aligned": st.column_config.CheckboxColumn(
                "To be aligned",
                help="Check this box if the capability needs to be aligned with others.",
                width="small",
            ),
        },
        hide_index=True,
        use_container_width=True,
        disabled=["ID"]
    )

    # Save Button
    if st.button("Save Changes"):
        # Merge the changes back into the original DataFrame
        for index, row in edited_timeline.iterrows():
            capability_data.loc[capability_data["ID"] == row["ID"], pi_columns] = row[pi_columns]
            capability_data.loc[capability_data["ID"] == row["ID"], "Total PI SP"] = row["Total PI SP"]
            capability_data.loc[capability_data["ID"] == row["ID"], "Status"] = row["Status"]
        
        for index, row in edited_comments.iterrows():
            capability_data.loc[capability_data["ID"] == row["ID"], comment_columns] = row[comment_columns]
        
        # Save the updated DataFrame to an Excel file while preserving other sheets
        save_data(file_path, capability_sheet_name, capability_data)
        st.success("Changes have been saved.")

# Function to create column configurations for PI columns on the timeline section
def create_pi_column_config(df, pi_options):
    column_config = {
        'Discovery PI': st.column_config.SelectboxColumn(
            "Discovery PI",
            help="The PI in which the capability has its discovery phase",
            options=pi_options
        ),
        'Fit-Scope PI': st.column_config.SelectboxColumn(
            "Fit-scope PI",
            help="The PI in which the capability has its fit-scope phase",
            options=pi_options
        )
    }
    
    # Regular expression to match "PI YY-0X" for varying PI column structure
    pi_regex = r"^PI \d{2}-0\d$"

    for column in df.columns:
        if re.match(pi_regex, column):  # Use regex to match the column names
            column_config[column] = st.column_config.NumberColumn(
                f"{column}",
                help=f"Select PI for {column}",
                min_value=0,
                max_value=1000,
                step=1,
                format="%d",
            )

    return column_config

# Function to extract the last segment of the URL
def extract_last_segment(url):
    match = re.search(r'[^/]+$', url)
    return match.group(0) if match else None

# Function to map state values to emojis
def state_to_emoji(state):
    emoji_map = {
        "1 - New": "🆕",
        "2 - Solution Backlog": "📜",
        "3 - Refinement": "🔍",
        "4 - Implementing": "⚙️",
        "5 - Validating": "📏",
        "6 - Done": "✅",
    }
    # Remove the "Number -" part
    state_text = re.sub(r"^\d+ - ", "", state)
    return f"{emoji_map.get(state, '')} {state_text}"