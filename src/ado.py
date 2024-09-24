import requests
from requests.auth import HTTPBasicAuth
import pandas as pd

# Azure DevOps details
organization = 'agco-dcx'
project = 'f0df1a08-84ea-4d6e-8210-43b7a1097f20'
pat = 'who7qjyoqcr5sqtw3fzxi4g7gsue7pdchf3526yidqah76dcm4dq'
api_version = '7.0'
top = 200000
id = '9198b680-797f-4e73-8809-9a89e8b338b0'

def fetch_iterations():
    iterations = []

    url = f'https://dev.azure.com/{organization}/{project}/{team}/_apis/wit/wiql/{id}?api-version=7.1-preview.2'
    response = requests.get(
        url,
        auth=HTTPBasicAuth('', pat),
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code == 200:
        iterations_data = response.json()["value"]
        iterations.extend(iterations_data)
    else:
        raise Exception(f"Failed to fetch iterations: {response.content}")

    df_iterations = pd.DataFrame(iterations)
    return df_iterations

# If you want to use this script directly
if __name__ == "__main__":
    iterations_df = fetch_iterations()
    print(iterations_df)