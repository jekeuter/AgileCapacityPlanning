def calculate_capacity(data):
    # Example calculation
    data['Capacity'] = data['Availability'] * data['Average Velocity'] / 100
    return data
