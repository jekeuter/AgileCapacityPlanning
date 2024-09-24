import yaml
from streamlit_authenticator import Authenticate

def load_auth_config(config_file):
    with open(config_file) as file:
        return yaml.safe_load(file)

def create_authenticator(config):
    return Authenticate(
        credentials=config['credentials'],
        cookie_name=config['cookie']['name'],
        cookie_key=config['cookie']['key'],
        cookie_expiry_days=config['cookie']['expiry_days'],
        pre_authorized=config['pre-authorized']
    )

def save_auth_config(config, config_file):
    with open(config_file, 'w') as file:
        yaml.safe_dump(config, file, default_flow_style=False)
